"""
Nightly Persona Synthesis Job (V2)

Runs nightly to:
1. Decay confidence on stale persona traits (not reinforced in 30+ days)
2. Clean up expired episodic contexts
3. Synthesize updated persona for users with new data
"""
import asyncio
from datetime import datetime, timedelta
from services.db import (
    users_collection, user_persona_collection,
    persona_observations_collection, user_memory_collection,
    episodic_context_collection
)
from services.persona.memory_service import MemoryService
from services.persona.observation_service import ObservationService
from services.persona.persona_service import PersonaService
from services.persona.episodic_context_service import EpisodicContextService


# ---------------------------------------------------------------------------
# Confidence Decay — reduce stale float traits by a small amount
# ---------------------------------------------------------------------------
DECAY_AMOUNT = 0.05
STALE_DAYS = 30
DECAY_FLOOR = 0.3  # Traits below this are effectively ignored by the behavior mapper

FLOAT_TRAIT_PATHS = [
    ("financial_persona", "budget_adherence"),
    ("financial_persona", "savings_consistency"),
    ("behavioral_traits", "consistency_level"),
    ("behavioral_traits", "impulsiveness"),
    ("behavioral_traits", "self_discipline"),
    ("behavioral_traits", "follow_through_rate"),
    ("productivity_profile", "procrastination_tendency"),
    ("health_energy", "exercise_consistency"),
]


async def apply_confidence_decay(user_id: str):
    """
    For each float trait in the persona, if the persona hasn't been
    updated in STALE_DAYS, reduce the float by DECAY_AMOUNT (min DECAY_FLOOR).
    """
    doc = await user_persona_collection.find_one({"user_id": user_id})
    if not doc:
        return

    last_updated = doc.get("updated_at")
    if not last_updated:
        return

    if isinstance(last_updated, str):
        last_updated = datetime.fromisoformat(last_updated)

    days_since = (datetime.utcnow() - last_updated).days
    if days_since < STALE_DAYS:
        return  # Not stale yet

    updates = {}
    for section, field in FLOAT_TRAIT_PATHS:
        section_data = doc.get(section, {})
        current_val = section_data.get(field)
        if current_val is not None and isinstance(current_val, (int, float)):
            new_val = max(current_val - DECAY_AMOUNT, DECAY_FLOOR)
            if new_val != current_val:
                updates[f"{section}.{field}"] = round(new_val, 3)

    if updates:
        await user_persona_collection.update_one(
            {"_id": doc["_id"]},
            {"$set": updates}
        )
        print(f"  [DECAY] Applied confidence decay to {len(updates)} traits for user {user_id}")


# ---------------------------------------------------------------------------
# Main Job
# ---------------------------------------------------------------------------
async def run_nightly_synthesis():
    """
    Iterates over all users and:
    1. Cleans up expired episodic contexts
    2. Applies confidence decay to stale traits
    3. Synthesizes persona for users with new data
    """
    print("[INFO] Starting Nightly Persona Synthesis Job (V2)...")
    
    # ── Step 1: Clean expired episodic contexts ──────────────────────────
    episodic_svc = EpisodicContextService(episodic_context_collection)
    expired_count = await episodic_svc.deactivate_expired()
    if expired_count:
        print(f"[INFO] Deactivated {expired_count} expired episodic contexts.")

    # ── Step 2: Initialize services ──────────────────────────────────────
    mem_service = MemoryService(user_memory_collection)
    obs_service = ObservationService(persona_observations_collection)
    persona_service = PersonaService(user_persona_collection, mem_service, obs_service)
    
    # Fetch all active users who have memories or observations
    memory_users = await user_memory_collection.distinct("user_id")
    obs_users = await persona_observations_collection.distinct("user_id")
    all_user_ids = list(set(memory_users + obs_users))
    
    processed_count = 0
    for user_id in all_user_ids:
        
        # ── Step 3: Confidence decay ─────────────────────────────────────
        await apply_confidence_decay(user_id)
        
        # ── Step 4: Check for new data ───────────────────────────────────
        obs_count = await persona_observations_collection.count_documents({"user_id": user_id})
        
        user_persona_doc = await user_persona_collection.find_one({"user_id": user_id})
        last_updated = user_persona_doc.get("updated_at") if user_persona_doc else None
        
        new_memories_count = 0
        if last_updated:
            new_memories_count = await user_memory_collection.count_documents({
                "user_id": user_id, 
                "updated_at": {"$gt": last_updated}
            })
        else:
            new_memories_count = await user_memory_collection.count_documents({"user_id": user_id})
            
        # ── Step 5: Synthesize if new data exists ────────────────────────
        if obs_count > 0 or new_memories_count > 0:
            print(f"[INFO] Synthesizing persona for user: {user_id} ({obs_count} observations, {new_memories_count} new memories)")
            success = await persona_service.synthesize_persona(user_id)
            if success:
                processed_count += 1
                
    print(f"[INFO] Nightly Persona Synthesis Complete. Processed {processed_count} users.")

if __name__ == "__main__":
    asyncio.run(run_nightly_synthesis())
