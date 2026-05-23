import os
from datetime import datetime
from typing import Optional, List
from models.user.persona_models import UserPersona, PersonaObservation, StructuredMemory
from services.persona.memory_service import MemoryService
from services.persona.observation_service import ObservationService
from providers.llm_provider import create_llm_provider, LLMProviderType

class PersonaService:
    """
    Manages the high-level User Persona profile and synthesizes observations into traits.
    """
    def __init__(self, persona_collection, memory_service: MemoryService, observation_service: ObservationService, llm_provider=None):
        self.collection = persona_collection
        self.memory_service = memory_service
        self.observation_service = observation_service
        self.llm = llm_provider or create_llm_provider(
            provider_type=LLMProviderType.OPENAI,
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini"
        )

    async def get_persona(self, user_id: str) -> UserPersona:
        """Fetch the user's current persona profile, or create a default one."""
        doc = await self.collection.find_one({"user_id": user_id})
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return UserPersona(**doc)
        
        # Return default if not exists
        return UserPersona(user_id=user_id)

    async def save_persona(self, persona: UserPersona):
        """Upsert the persona document."""
        data = persona.model_dump(exclude={"id"})
        data["updated_at"] = datetime.utcnow()
        
        await self.collection.update_one(
            {"user_id": persona.user_id},
            {"$set": data},
            upsert=True
        )

    async def synthesize_persona(self, user_id: str) -> bool:
        """
        The core engine function (V2).
        1. Load current Persona
        2. Load recent Observations
        3. Load raw active Memories
        4. LLM synthesizes updated Persona with contradiction handling
        5. Save Persona & clear processed observations
        """
        current_persona = await self.get_persona(user_id)
        observations = await self.observation_service.get_recent_observations(user_id)
        memories = await self.memory_service.get_memories(user_id)
        
        if not observations and not memories:
            return False # Nothing to synthesize
            
        system_prompt = {
            "role": "system",
            "content": (
                "You are RIVA's Persona Synthesis Engine (V2). Your job is to update a user's "
                "high-level persona profile based on their raw memories and recent behavioral observations.\n\n"
                "RULES:\n"
                "1. MERGE new insights gracefully without losing established patterns.\n"
                "2. CONTRADICTION HANDLING: If new evidence contradicts an existing trait, do NOT "
                "   overwrite immediately. Instead, move the trait toward the new value gradually. "
                "   For example, if the user was a 'night_owl' but new evidence suggests mornings, "
                "   set chronotype to 'flexible' as a transition.\n"
                "3. CONFIDENCE: For float fields (0.0-1.0), adjust based on evidence strength:\n"
                "   - Explicit user statements → high values (0.8-1.0)\n"
                "   - Repeated behavioral patterns → medium-high (0.6-0.8)\n"
                "   - Single observations → moderate (0.4-0.6)\n"
                "4. GOALS: Convert any goal mentions into GoalItem format with goal, priority, target_date.\n"
                "5. Keep ALL fields populated — use sensible defaults if no evidence exists.\n"
                "6. The output must exactly match the UserPersona Pydantic schema including all "
                "   sub-models: CommunicationStyle, ProductivityProfile, FinancialPersona, "
                "   BehavioralTraits, SchedulingPreferences, HealthEnergyProfile, and active_goals as List[GoalItem]."
            )
        }
        
        user_prompt = {
            "role": "user",
            "content": (
                f"CURRENT PERSONA:\n{current_persona.model_dump_json(indent=2)}\n\n"
                f"RECENT BEHAVIORAL OBSERVATIONS:\n{[obs.model_dump() for obs in observations]}\n\n"
                f"RAW MEMORIES:\n{[mem for mem in memories]}\n\n"
                "Please output the completely updated UserPersona structure."
            )
        }
        
        try:
            # Force output to match the UserPersona Pydantic schema
            updated_persona = await self.llm.generate_structured(
                messages=[system_prompt, user_prompt],
                response_format=UserPersona
            )
            
            # Ensure user_id remains intact
            updated_persona.user_id = user_id
            
            # Save the new persona
            await self.save_persona(updated_persona)
            
            # Clear processed observations
            await self.observation_service.clear_observations(user_id)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Persona synthesis failed: {e}")
            return False
