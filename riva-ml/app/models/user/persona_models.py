from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

# ---------------------------------------------------------
# Enums
# ---------------------------------------------------------

class MemoryType(str, Enum):
    PREFERENCE = "preference"
    HABIT = "habit"
    FACT = "fact"
    CONSTRAINT = "constraint"
    GOAL = "goal"
    SYSTEM = "system"

class MemorySource(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    SYSTEM = "system"

# ---------------------------------------------------------
# Low-Level Memories & Observations
# ---------------------------------------------------------

class StructuredMemory(BaseModel):
    """Raw structured memory extracted from conversations or events."""
    id: Optional[str] = None  # MongoDB _id
    user_id: str
    memory_type: MemoryType
    key: str
    value: Any
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: MemorySource = MemorySource.EXPLICIT
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PersonaObservation(BaseModel):
    """Low-level behavioral signals inferred from repeated actions."""
    id: Optional[str] = None
    user_id: str
    trait: str
    evidence: str
    confidence_delta: float
    source: str = "behavior_analysis"
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ---------------------------------------------------------
# Episodic Context (Temporary Situational Awareness)
# ---------------------------------------------------------

class EpisodicContext(BaseModel):
    """Temporary life situation that influences RIVA's behavior."""
    id: Optional[str] = None
    user_id: str
    context_type: str = "general"     # career, health, travel, stress, deadline, family, etc.
    summary: str                       # "Preparing for job interviews"
    importance: float = Field(default=0.7, ge=0.0, le=1.0)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # None = no expiry (manual deactivation)

# ---------------------------------------------------------
# High-Level Synthesized Persona — V2 Attribute Model
# ---------------------------------------------------------

class CommunicationStyle(BaseModel):
    """Controls HOW RIVA speaks."""
    verbosity: str = "balanced"                   # concise | balanced | detailed
    tone: str = "friendly"                        # friendly | professional | casual | motivational
    decision_style: str = "analytical"            # analytical | emotional | mixed
    humor_preference: str = "light"               # none | light | playful
    confirmation_preference: str = "balanced"     # minimal | balanced | explicit
    reminder_style: str = "gentle"                # gentle | direct | aggressive
    motivation_style: str = "encouraging"         # encouraging | logical | accountability
    conversation_pacing: str = "moderate"         # fast | moderate | slow
    prefers_examples: bool = False
    prefers_step_by_step_guidance: bool = False

class ProductivityProfile(BaseModel):
    """Controls scheduling and productivity reasoning."""
    chronotype: str = "unknown"                   # morning_person | night_owl | flexible
    peak_focus_hours: List[str] = []              # e.g. ["9PM-1AM"]
    deep_work_preference: bool = False
    meeting_tolerance: str = "medium"             # low | medium | high
    context_switch_tolerance: str = "medium"      # low | medium | high
    task_completion_style: str = "steady"          # burst | steady | deadline_driven
    planning_style: str = "adaptive"              # structured | adaptive | chaotic
    procrastination_tendency: float = Field(default=0.5, ge=0.0, le=1.0)
    preferred_break_frequency: str = "medium"     # low | medium | high
    burnout_risk: str = "low"                     # low | medium | high
    prefers_batching_tasks: bool = False
    calendar_density_tolerance: str = "medium"    # low | medium | high

class FinancialPersona(BaseModel):
    """Controls finance coaching and alerts."""
    spending_style: str = "balanced"              # disciplined | impulsive | emotional | inconsistent
    budget_adherence: float = Field(default=0.5, ge=0.0, le=1.0)
    savings_consistency: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_tolerance: str = "medium"                # low | medium | high
    spending_trigger_patterns: List[str] = []     # e.g. ["weekend", "stress"]
    expense_awareness: str = "medium"             # low | medium | high
    price_sensitivity: str = "medium"             # low | medium | high
    financial_organization_level: str = "medium"  # low | medium | high
    overspending_categories: List[str] = []       # e.g. ["food", "shopping"]
    responds_well_to_budget_alerts: bool = True
    salary_stability: str = "stable"              # stable | variable

class BehavioralTraits(BaseModel):
    """Controls adaptive behavioral responses."""
    stress_response: str = "unknown"              # withdraws | overworks | seeks_structure
    motivation_pattern: str = "unknown"           # positive_reinforcement | pressure | rewards
    decision_fatigue_sensitivity: str = "medium"  # low | medium | high
    consistency_level: float = Field(default=0.5, ge=0.0, le=1.0)
    adaptability: str = "medium"                  # low | medium | high
    routine_dependence: str = "medium"            # low | medium | high
    impulsiveness: float = Field(default=0.5, ge=0.0, le=1.0)
    self_discipline: float = Field(default=0.5, ge=0.0, le=1.0)
    follow_through_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    energy_variability: str = "stable"            # stable | fluctuating

class GoalItem(BaseModel):
    """A structured goal with priority and optional deadline."""
    goal: str
    priority: str = "medium"                      # low | medium | high
    target_date: Optional[str] = None             # ISO date string or None

class SchedulingPreferences(BaseModel):
    """Controls calendar behavior."""
    preferred_meeting_times: List[str] = []       # e.g. ["afternoon", "evening"]
    avoids_back_to_back_meetings: bool = True
    travel_buffer_preference_minutes: int = 30
    preferred_work_hours: str = "9AM-6PM"
    weekend_work_tolerance: str = "low"           # low | medium | high
    meeting_length_preference: str = "short"      # short | balanced | long

class HealthEnergyProfile(BaseModel):
    """Adaptive scheduling and burnout prevention."""
    sleep_pattern_consistency: str = "medium"     # low | medium | high
    energy_peak_time: str = "unknown"             # morning | afternoon | night | unknown
    fatigue_frequency: str = "low"                # low | medium | high
    exercise_consistency: float = Field(default=0.5, ge=0.0, le=1.0)
    burnout_signals_detected: bool = False


class UserPersona(BaseModel):
    """The synthesized high-level profile injected into the LLM prompt. V2."""
    id: Optional[str] = None
    user_id: str
    communication_style: CommunicationStyle = Field(default_factory=CommunicationStyle)
    productivity_profile: ProductivityProfile = Field(default_factory=ProductivityProfile)
    financial_persona: FinancialPersona = Field(default_factory=FinancialPersona)
    behavioral_traits: BehavioralTraits = Field(default_factory=BehavioralTraits)
    scheduling_preferences: SchedulingPreferences = Field(default_factory=SchedulingPreferences)
    health_energy: HealthEnergyProfile = Field(default_factory=HealthEnergyProfile)
    active_goals: List[GoalItem] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)
