from datetime import datetime
from typing import List, Optional
from models.user.persona_models import PersonaObservation

class ObservationService:
    """
    Service for managing low-level behavioral observations.
    """
    def __init__(self, collection):
        self.collection = collection

    async def log_observation(self, user_id: str, trait: str, evidence: str, confidence_delta: float) -> str:
        """
        Logs a new behavioral observation for a user.
        """
        obs = PersonaObservation(
            user_id=user_id,
            trait=trait,
            evidence=evidence,
            confidence_delta=confidence_delta
        )
        
        result = await self.collection.insert_one(obs.model_dump(exclude={"id"}))
        return str(result.inserted_id)

    async def get_recent_observations(self, user_id: str, limit: int = 50) -> List[PersonaObservation]:
        """
        Fetches the most recent observations.
        """
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        observations = []
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
            observations.append(PersonaObservation(**doc))
            
        return observations

    async def clear_observations(self, user_id: str):
        """
        Clears observations (e.g. after they have been synthesized).
        """
        await self.collection.delete_many({"user_id": user_id})
