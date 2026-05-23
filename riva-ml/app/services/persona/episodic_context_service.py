"""
Episodic Context Service — Manages temporary situational contexts.

Examples: interview prep, stressful work week, traveling, illness recovery,
intense deadlines, exams, family events.

These contexts influence RIVA's behavior for a limited time and auto-expire.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from models.user.persona_models import EpisodicContext


class EpisodicContextService:
    """CRUD service for temporary situational contexts."""

    def __init__(self, collection):
        self.collection = collection

    async def add_context(
        self,
        user_id: str,
        context_type: str,
        summary: str,
        importance: float = 0.7,
        duration_days: Optional[int] = 7,
    ) -> str:
        """
        Create a new episodic context for a user.
        
        Args:
            duration_days: How many days until this context expires.
                          None = no auto-expiry (manual deactivation).
        """
        expires_at = None
        if duration_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=duration_days)

        ctx = EpisodicContext(
            user_id=user_id,
            context_type=context_type,
            summary=summary,
            importance=min(max(importance, 0.0), 1.0),
            is_active=True,
            expires_at=expires_at,
        )

        result = await self.collection.insert_one(ctx.model_dump(exclude={"id"}))
        return str(result.inserted_id)

    async def get_active_contexts(self, user_id: str) -> List[EpisodicContext]:
        """Fetch all active, non-expired contexts for a user."""
        now = datetime.utcnow()

        query = {
            "user_id": user_id,
            "is_active": True,
            "$or": [
                {"expires_at": None},           # No expiry set
                {"expires_at": {"$gt": now}},   # Not yet expired
            ],
        }

        cursor = self.collection.find(query).sort("importance", -1)
        docs = await cursor.to_list(length=20)

        contexts = []
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
            contexts.append(EpisodicContext(**doc))

        return contexts

    async def deactivate_context(self, user_id: str, context_id: str) -> bool:
        """Manually deactivate a specific context."""
        from bson import ObjectId
        result = await self.collection.update_one(
            {"_id": ObjectId(context_id), "user_id": user_id},
            {"$set": {"is_active": False}},
        )
        return result.modified_count > 0

    async def deactivate_expired(self) -> int:
        """
        Bulk-deactivate all contexts past their expiry.
        Called by the nightly job.
        """
        now = datetime.utcnow()
        result = await self.collection.update_many(
            {
                "is_active": True,
                "expires_at": {"$lte": now, "$ne": None},
            },
            {"$set": {"is_active": False}},
        )
        return result.modified_count
