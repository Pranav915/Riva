"""
Finance Query Service - Handles NLP queries for spending and income.
Replaces the legacy FinanceAgent _handle_query logic.
"""
from datetime import datetime
from typing import Dict, Any
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

from .query_builder import QueryBuilder

load_dotenv()

class FinanceQueryService:
    def __init__(self, transactions_collection, openai_client: OpenAI = None):
        self.transactions = transactions_collection
        self.client = openai_client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def handle_query(self, user_id: str, user_input: str, memory: Dict[str, Any] = None) -> str:
        """
        Process a natural language finance query.
        Returns a natural language response.
        """
        if self.transactions is None:
            return "Finance tracking isn't set up yet."

        if memory is None:
            memory = {}

        # 1. Use GPT to understand what the user wants to query
        query_spec = await self._build_query_spec(user_input)

        # 2. Build and run the MongoDB query
        builder = QueryBuilder(user_id)
        
        try:
            query = builder.build_query(query_spec)
            cursor = self.transactions.find(query)
            transactions = await cursor.to_list(length=100)

            if not transactions:
                return "No transactions found for that period."

            # 3. Aggregate results
            total = sum(t.get("amount", 0) for t in transactions)
            by_category = {}
            for t in transactions:
                cat = t.get("category", "other")
                by_category[cat] = by_category.get(cat, 0) + t.get("amount", 0)

            query_results = {
                "total": total,
                "count": len(transactions),
                "by_category": by_category,
                "date_range": query_spec.get("date_range", "this_month"),
            }

            # 4. Generate natural-language response via GPT
            response_text = await self._generate_query_response(
                user_input=user_input, 
                query_results=query_results, 
                memory=memory
            )

            return response_text

        except Exception as e:
            print(f"[FINANCE_QUERY] Query error: {e}")
            return "I had trouble fetching your data. Please try again."

    async def _build_query_spec(self, user_input: str) -> Dict:
        """Use GPT to build a query spec from natural language."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._query_prompt()},
                    {"role": "user", "content": user_input},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=300,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"[FINANCE_QUERY] Query spec error: {e}")
            return {"type": "expense", "date_range": "this_month"}

    async def _generate_query_response(
        self,
        user_input: str,
        query_results: Dict,
        memory: Dict,
    ) -> str:
        """Generate a natural-language response for query results."""
        context_data = {
            "user_input": user_input,
            "query_results": query_results,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
        }
        if memory.get("constraints"):
            context_data["user_budgets"] = memory["constraints"]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._response_prompt()},
                    {"role": "user", "content": json.dumps(context_data, default=str)},
                ],
                temperature=0.5,
                max_tokens=300,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[FINANCE_QUERY] Response gen error: {e}")
            total = query_results.get("total", 0)
            return f"You've spent ₹{total:,.0f} so far."

    def _query_prompt(self) -> str:
        return """You are a query spec builder. Convert natural language into a MongoDB query spec.

RETURN THIS JSON:
{
  "type": "expense" | "income" | "all",
  "category": category or null,
  "date_range": "today|yesterday|this_week|last_week|this_month|last_month|last_30_days|all_time",
  "min_amount": number or null,
  "max_amount": number or null,
  "group_by": "category" | "day" | null,
  "sort_by": "amount" | "date" | null,
  "sort_order": "asc" | "desc",
  "limit": number or null
}"""

    def _response_prompt(self) -> str:
        return """You are RIVA. Given financial query results, generate a concise, friendly response.

RULES:
- Use ₹ for currency
- Be concise (1-2 sentences)
- If budget exists, mention how close user is to limit
- Be supportive, never judgmental
- Mention top categories if available"""
