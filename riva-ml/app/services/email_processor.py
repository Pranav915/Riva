"""Email Processor - analyzes email content with LLM and updates todos/orders.

This module provides a lightweight pipeline that:
 - fetches messages via GmailService
 - parses headers/snippets
 - calls an LLM to classify and extract tasks or order info
 - writes ParsedEmail documents and upserts orders and todos
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.gmail_service import GmailService
from services.db import parsed_emails_collection, email_state_collection, orders_collection, todos_collection
from services.todo_service import TodoService
from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class EmailProcessor:
    def __init__(self, gmail_service: GmailService):
        self.gmail = gmail_service
        self.todo_service = TodoService(todos_collection)
        self.openai = OpenAI(api_key=OPENAI_API_KEY)

    async def fetch_and_process(self, user_id: str, max_messages: int = 25) -> Dict[str, Any]:
        """Fetch new messages for user and process them."""
        # Get message ids
        messages = await self.gmail.list_messages_since(user_id, max_results=max_messages)
        processed = 0
        for m in messages:
            mid = m.get("id")
            if not mid:
                continue
            msg = await self.gmail.get_message(user_id, mid)
            if not msg:
                continue

            # Basic metadata
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject")
            snippet = msg.get("snippet")
            from_addr = headers.get("From")
            thread_id = msg.get("threadId")

            # Ask LLM to classify
            prompt = (
                f"Classify this email and extract any actionable task or order data.\nSubject: {subject}\nFrom: {from_addr}\nSnippet: {snippet}\n\nRespond JSON with keys: action_required (bool), action_type (string|null), task (string|null), due_date (ISO|null), order (object|null)."
            )

            try:
                resp = self.openai.complete(prompt)
                # openai.complete is a lightweight wrapper in this repo — adapt to returned value
                text = getattr(resp, "text", None) or resp.get("text") if isinstance(resp, dict) else str(resp)
                # Try parse JSON from text
                import json
                parsed = {}
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = {"action_required": False}

                # Build parsed doc
                parsed_doc = {
                    "user_id": user_id,
                    "message_id": mid,
                    "thread_id": thread_id,
                    "subject": subject,
                    "snippet": snippet,
                    "from_address": from_addr,
                    "action_required": parsed.get("action_required", False),
                    "action_type": parsed.get("action_type"),
                    "parsed_task": parsed.get("task"),
                    "parsed_due_date": parsed.get("due_date"),
                    "metadata": {},
                    "raw_headers": headers,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

                await parsed_emails_collection.update_one(
                    {"user_id": user_id, "message_id": mid},
                    {"$set": parsed_doc},
                    upsert=True,
                )

                # If action_required and there's a task -> create todo
                if parsed_doc["action_required"] and parsed_doc.get("parsed_task"):
                    due = parsed_doc.get("parsed_due_date")
                    await self.todo_service.add_todo(user_id, parsed_doc["parsed_task"], due_date=due)

                # If order info present -> upsert into orders
                order = parsed.get("order") if isinstance(parsed, dict) else None
                if order:
                    order_id = order.get("order_id") or order.get("id")
                    doc = {
                        "user_id": user_id,
                        "order_id": order_id,
                        "order_status": order.get("status", "pending"),
                        "merchant": order.get("merchant"),
                        "estimated_delivery": order.get("estimated_delivery"),
                        "item_summary": order.get("items"),
                        "tracking_number": order.get("tracking_number"),
                        "updated_at": datetime.utcnow(),
                    }
                    await orders_collection.update_one({"user_id": user_id, "order_id": order_id}, {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)

                processed += 1

            except Exception as e:
                print(f"[EMAIL_PROCESSOR] Error processing message {mid}: {e}")
                continue

        return {"processed": processed}
