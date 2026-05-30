import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel
from services.persona.memory_service import MemoryService, MemoryType, MemorySource
from providers.llm_provider import create_llm_provider, LLMProviderType

class MemoryExtractionResponse(BaseModel):
    memories: List[dict]  # Will contain dictionaries matching StructuredMemory

class MemoryExtractor:
    """
    Extracts structured facts, preferences, and goals from raw user messages.
    """
    def __init__(self, memory_service: MemoryService, llm_provider=None):
        self.memory_service = memory_service
        self.llm = llm_provider or create_llm_provider(
            provider_type=LLMProviderType.OPENAI,
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini"
        )
        
    async def extract_from_conversation(self, user_id: str, messages: List[Dict[str, str]]) -> int:
        """
        Analyzes recent conversation and extracts structured memories.
        Saves them to the database.
        Returns the number of memories extracted.
        """
        if not messages:
            return 0
            
        system_prompt = {
            "role": "system",
            "content": (
                "You are an AI memory extraction module. "
                "Analyze the following conversation and extract any new facts, preferences, constraints, or goals about the user. "
                "Only extract information that is persistent and important for a long-term AI secretary to remember. "
                "Output a list of memories."
                "\n\nRules:"
                "\n- memory_type: must be 'preference', 'habit', 'fact', 'constraint', or 'goal'."
                "\n- key: A snake_case string identifying the memory (e.g., 'meeting_time_preference')."
                "\n- value: The actual value (e.g., 'avoid_morning' or {'avoid': 'morning'})."
                "\n- confidence: 0.0 to 1.0. High (0.9+) if explicitly stated by the user."
            )
        }
        
        prompt_messages = [system_prompt] + messages[-10:] # Analyze last 10 messages
        
        try:
            result = await self.llm.generate_structured(
                messages=prompt_messages,
                response_format=MemoryExtractionResponse
            )
            
            extracted_count = 0
            for mem_data in result.memories:
                # Add to DB
                await self.memory_service.add_memory(
                    user_id=user_id,
                    memory_type=mem_data.get("memory_type", MemoryType.FACT),
                    key=mem_data.get("key"),
                    value=mem_data.get("value"),
                    confidence=mem_data.get("confidence", 0.9),
                    source=MemorySource.EXPLICIT
                )
                extracted_count += 1
                
            return extracted_count
            
        except Exception as e:
            print(f"[ERROR] Memory extraction failed: {e}")
            return 0
