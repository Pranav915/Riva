"""
Persona Behavior Mapper — Converts persona traits + episodic context into
hard behavioral rules that are injected directly into the LLM prompt.

Design: Pure-Python deterministic logic (no LLM call). Fast, free, predictable.
"""
from typing import Dict, List, Any, Optional
from models.user.persona_models import UserPersona, EpisodicContext


def map_persona_to_behavior_rules(
    persona: UserPersona,
    episodic_contexts: Optional[List[EpisodicContext]] = None,
) -> Dict[str, Any]:
    """
    Convert a UserPersona + active episodic contexts into a structured
    behavior rules dict that the prompt builder can inject verbatim.
    """
    rules: Dict[str, Any] = {
        "communication_rules": _map_communication(persona),
        "scheduling_rules": _map_scheduling(persona),
        "finance_rules": _map_finance(persona),
        "behavioral_rules": _map_behavioral(persona),
        "goal_rules": _map_goals(persona),
        "health_rules": _map_health(persona),
    }

    if episodic_contexts:
        rules["episodic_context_rules"] = _map_episodic(episodic_contexts)

    return rules


# ---------------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------------
def _map_communication(p: UserPersona) -> Dict[str, Any]:
    cs = p.communication_style
    rules: Dict[str, Any] = {}

    # Verbosity → sentence limits
    if cs.verbosity == "concise":
        rules["max_response_sentences"] = 2
        rules["avoid_long_explanations"] = True
    elif cs.verbosity == "detailed":
        rules["max_response_sentences"] = 6
        rules["avoid_long_explanations"] = False
    else:
        rules["max_response_sentences"] = 3
        rules["avoid_long_explanations"] = False

    # Tone
    rules["tone"] = cs.tone

    # Humor
    if cs.humor_preference == "none":
        rules["use_humor"] = False
    elif cs.humor_preference == "playful":
        rules["use_humor"] = True
        rules["humor_level"] = "high"
    else:
        rules["use_humor"] = True
        rules["humor_level"] = "subtle"

    # Confirmation preference
    if cs.confirmation_preference == "minimal":
        rules["confirmation_level"] = "skip_unless_critical"
    elif cs.confirmation_preference == "explicit":
        rules["confirmation_level"] = "always_confirm"
    else:
        rules["confirmation_level"] = "confirm_important_only"

    # Reminder style
    rules["reminder_style"] = cs.reminder_style

    # Motivation
    rules["motivation_approach"] = cs.motivation_style

    # Pacing
    if cs.conversation_pacing == "fast":
        rules["response_speed_note"] = "User prefers fast, snappy exchanges"
    elif cs.conversation_pacing == "slow":
        rules["response_speed_note"] = "User prefers thoughtful, unhurried responses"

    # Guidance style
    if cs.prefers_examples:
        rules["include_examples"] = True
    if cs.prefers_step_by_step_guidance:
        rules["use_step_by_step"] = True

    return rules


# ---------------------------------------------------------------------------
# Scheduling & Productivity
# ---------------------------------------------------------------------------
def _map_scheduling(p: UserPersona) -> Dict[str, Any]:
    pp = p.productivity_profile
    sp = p.scheduling_preferences
    rules: Dict[str, Any] = {}

    # Chronotype-based morning avoidance
    if pp.chronotype == "night_owl":
        rules["avoid_morning_scheduling"] = True
        rules["suggest_late_focus_blocks"] = True
    elif pp.chronotype == "morning_person":
        rules["protect_morning_focus_time"] = True

    # Peak hours
    if pp.peak_focus_hours:
        rules["peak_hours"] = pp.peak_focus_hours
        rules["protect_peak_hours"] = True

    # Meeting tolerance
    if pp.meeting_tolerance == "low":
        rules["max_meetings_per_day"] = 2
        rules["warn_on_meeting_heavy_day"] = True
    elif pp.meeting_tolerance == "high":
        rules["max_meetings_per_day"] = 6

    # Calendar density
    if pp.calendar_density_tolerance == "low":
        rules["max_daily_events"] = 4
        rules["flag_overloaded_days"] = True
    elif pp.calendar_density_tolerance == "high":
        rules["max_daily_events"] = 8

    # Back-to-back
    if sp.avoids_back_to_back_meetings:
        rules["buffer_between_meetings_min"] = sp.travel_buffer_preference_minutes

    # Context switching
    if pp.context_switch_tolerance == "low":
        rules["batch_similar_tasks"] = True
        rules["minimize_context_switches"] = True

    # Deep work
    if pp.deep_work_preference:
        rules["protect_deep_work_blocks"] = True

    # Meeting preferences
    if sp.preferred_meeting_times:
        rules["preferred_meeting_slots"] = sp.preferred_meeting_times

    # Work hours
    rules["preferred_work_hours"] = sp.preferred_work_hours

    # Weekend
    if sp.weekend_work_tolerance == "low":
        rules["avoid_weekend_scheduling"] = True

    # Burnout risk
    if pp.burnout_risk == "high":
        rules["enforce_break_reminders"] = True
        rules["limit_overtime_suggestions"] = True

    # Procrastination
    if pp.procrastination_tendency > 0.7:
        rules["use_deadline_nudges"] = True
        rules["break_tasks_into_smaller_steps"] = True

    return rules


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------
def _map_finance(p: UserPersona) -> Dict[str, Any]:
    fp = p.financial_persona
    rules: Dict[str, Any] = {}

    # Budget alert style based on responsiveness
    if fp.responds_well_to_budget_alerts:
        rules["budget_alert_frequency"] = "proactive"
    else:
        rules["budget_alert_frequency"] = "minimal"

    # Budget adherence → alert urgency
    if fp.budget_adherence < 0.4:
        rules["budget_alert_style"] = "gentle"
        rules["budget_coaching_level"] = "supportive"
    elif fp.budget_adherence > 0.8:
        rules["budget_alert_style"] = "brief"
        rules["budget_coaching_level"] = "minimal"
    else:
        rules["budget_alert_style"] = "balanced"
        rules["budget_coaching_level"] = "moderate"

    # Spending triggers
    if fp.spending_trigger_patterns:
        rules["watch_for_spending_triggers"] = fp.spending_trigger_patterns

    # Overspending categories
    if fp.overspending_categories:
        rules["flag_categories"] = fp.overspending_categories

    # Savings emphasis
    if fp.savings_consistency < 0.4:
        rules["emphasize_savings_goals"] = True

    # Impulsive spending
    if fp.spending_style in ("impulsive", "emotional"):
        rules["add_cooling_period_nudge"] = True

    return rules


# ---------------------------------------------------------------------------
# Behavioral / Emotional
# ---------------------------------------------------------------------------
def _map_behavioral(p: UserPersona) -> Dict[str, Any]:
    bt = p.behavioral_traits
    rules: Dict[str, Any] = {}

    # Stress response
    if bt.stress_response == "withdraws":
        rules["avoid_aggressive_reminders"] = True
        rules["use_supportive_language"] = True
        rules["reduce_proactive_suggestions_when_stressed"] = True
    elif bt.stress_response == "overworks":
        rules["enforce_break_reminders"] = True
        rules["flag_overwork_patterns"] = True
    elif bt.stress_response == "seeks_structure":
        rules["offer_structured_plans"] = True

    # Motivation pattern
    if bt.motivation_pattern == "positive_reinforcement":
        rules["celebrate_completions"] = True
        rules["avoid_negative_framing"] = True
    elif bt.motivation_pattern == "pressure":
        rules["use_urgency_language"] = True
    elif bt.motivation_pattern == "rewards":
        rules["suggest_rewards_after_milestones"] = True

    # Decision fatigue
    if bt.decision_fatigue_sensitivity == "high":
        rules["limit_choices_presented"] = 2
        rules["provide_default_recommendation"] = True

    # Follow-through
    if bt.follow_through_rate < 0.4:
        rules["add_follow_up_reminders"] = True
        rules["check_in_on_pending_tasks"] = True

    # Self-discipline
    if bt.self_discipline < 0.4:
        rules["use_accountability_nudges"] = True

    # Routine dependence
    if bt.routine_dependence == "high":
        rules["preserve_established_routines"] = True
        rules["warn_before_disrupting_routine"] = True

    return rules


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------
def _map_goals(p: UserPersona) -> Dict[str, Any]:
    rules: Dict[str, Any] = {}

    if p.active_goals:
        high_priority = [g for g in p.active_goals if g.priority == "high"]
        if high_priority:
            rules["high_priority_goals"] = [g.goal for g in high_priority]
            rules["reference_goals_in_relevant_decisions"] = True

        all_goals = [
            {"goal": g.goal, "priority": g.priority, "deadline": g.target_date}
            for g in p.active_goals
        ]
        rules["active_goals_summary"] = all_goals

    return rules


# ---------------------------------------------------------------------------
# Health & Energy
# ---------------------------------------------------------------------------
def _map_health(p: UserPersona) -> Dict[str, Any]:
    he = p.health_energy
    rules: Dict[str, Any] = {}

    if he.burnout_signals_detected:
        rules["burnout_warning"] = True
        rules["reduce_workload_suggestions"] = True
        rules["enforce_rest_periods"] = True

    if he.fatigue_frequency == "high":
        rules["suggest_energy_management"] = True
        rules["limit_back_to_back_intense_tasks"] = True

    if he.energy_peak_time != "unknown":
        rules["energy_peak"] = he.energy_peak_time
        rules["schedule_demanding_tasks_at_peak"] = True

    if he.exercise_consistency < 0.3:
        rules["nudge_physical_activity"] = True

    if he.sleep_pattern_consistency == "low":
        rules["suggest_sleep_hygiene"] = True

    return rules


# ---------------------------------------------------------------------------
# Episodic Context
# ---------------------------------------------------------------------------
def _map_episodic(contexts: List[EpisodicContext]) -> Dict[str, Any]:
    rules: Dict[str, Any] = {}

    summaries = []
    priority_adjustments = []

    for ctx in contexts:
        if not ctx.is_active:
            continue
        summaries.append(f"{ctx.context_type}: {ctx.summary}")
        if ctx.importance >= 0.8:
            priority_adjustments.append(ctx.summary)

    if summaries:
        rules["current_situations"] = summaries

    if priority_adjustments:
        rules["adjust_priorities_for"] = priority_adjustments

    return rules


# ---------------------------------------------------------------------------
# Prompt Formatter — Converts rules dict into injectable prompt text
# ---------------------------------------------------------------------------
def format_behavior_rules_for_prompt(rules: Dict[str, Any]) -> str:
    """
    Convert the behavior rules dict into clean, readable prompt text.
    Only includes sections that have meaningful rules.
    """
    sections = []

    # Communication
    comm = rules.get("communication_rules", {})
    if comm:
        lines = ["COMMUNICATION RULES:"]
        if comm.get("max_response_sentences"):
            lines.append(f"- Keep responses to {comm['max_response_sentences']} sentences max.")
        if comm.get("avoid_long_explanations"):
            lines.append("- Avoid long explanations. Be direct.")
        if comm.get("tone"):
            lines.append(f"- Tone: {comm['tone']}.")
        if comm.get("use_humor") and comm.get("humor_level") == "high":
            lines.append("- User enjoys humor — feel free to be playful.")
        elif comm.get("use_humor"):
            lines.append("- Light humor is welcome.")
        if comm.get("reminder_style"):
            lines.append(f"- Reminder style: {comm['reminder_style']}.")
        if comm.get("motivation_approach"):
            lines.append(f"- Motivation: use {comm['motivation_approach']} approach.")
        if comm.get("include_examples"):
            lines.append("- Include practical examples when explaining.")
        if comm.get("use_step_by_step"):
            lines.append("- Break guidance into clear steps.")
        if comm.get("response_speed_note"):
            lines.append(f"- {comm['response_speed_note']}.")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Scheduling
    sched = rules.get("scheduling_rules", {})
    if sched:
        lines = ["SCHEDULING RULES:"]
        if sched.get("avoid_morning_scheduling"):
            lines.append("- Avoid scheduling before 11AM (user is a night owl).")
        if sched.get("protect_morning_focus_time"):
            lines.append("- Protect morning hours for focus work.")
        if sched.get("peak_hours"):
            lines.append(f"- Peak focus hours: {', '.join(sched['peak_hours'])}. Protect these.")
        if sched.get("max_meetings_per_day"):
            lines.append(f"- Max {sched['max_meetings_per_day']} meetings/day. Warn if exceeded.")
        if sched.get("buffer_between_meetings_min"):
            lines.append(f"- Keep {sched['buffer_between_meetings_min']}min buffer between meetings.")
        if sched.get("avoid_weekend_scheduling"):
            lines.append("- Avoid weekend scheduling unless user insists.")
        if sched.get("flag_overloaded_days"):
            lines.append("- Flag days with too many events.")
        if sched.get("batch_similar_tasks"):
            lines.append("- Suggest batching similar tasks together.")
        if sched.get("protect_deep_work_blocks"):
            lines.append("- Protect deep work blocks from interruptions.")
        if sched.get("preferred_meeting_slots"):
            lines.append(f"- Preferred meeting slots: {', '.join(sched['preferred_meeting_slots'])}.")
        if sched.get("use_deadline_nudges"):
            lines.append("- Use gentle deadline nudges (user tends to procrastinate).")
        if sched.get("enforce_break_reminders"):
            lines.append("- Remind user to take breaks.")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Finance
    fin = rules.get("finance_rules", {})
    if fin:
        lines = ["FINANCE RULES:"]
        if fin.get("budget_alert_style"):
            lines.append(f"- Budget alerts: {fin['budget_alert_style']} style.")
        if fin.get("budget_alert_frequency"):
            lines.append(f"- Alert frequency: {fin['budget_alert_frequency']}.")
        if fin.get("emphasize_savings_goals"):
            lines.append("- Emphasize long-term savings goals in finance conversations.")
        if fin.get("flag_categories"):
            lines.append(f"- Watch spending in: {', '.join(fin['flag_categories'])}.")
        if fin.get("watch_for_spending_triggers"):
            lines.append(f"- Spending triggers to watch: {', '.join(fin['watch_for_spending_triggers'])}.")
        if fin.get("add_cooling_period_nudge"):
            lines.append("- For impulse purchases, suggest a cooling-off period.")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Behavioral
    behav = rules.get("behavioral_rules", {})
    if behav:
        lines = ["BEHAVIORAL RULES:"]
        if behav.get("avoid_aggressive_reminders"):
            lines.append("- Never use aggressive reminders. Be supportive.")
        if behav.get("use_supportive_language"):
            lines.append("- Use encouraging, supportive language.")
        if behav.get("celebrate_completions"):
            lines.append("- Celebrate task completions enthusiastically.")
        if behav.get("avoid_negative_framing"):
            lines.append("- Avoid negative framing. Focus on progress.")
        if behav.get("provide_default_recommendation"):
            lines.append("- When presenting options, always suggest a default.")
        if behav.get("limit_choices_presented"):
            lines.append(f"- Limit choices to {behav['limit_choices_presented']} options max.")
        if behav.get("add_follow_up_reminders"):
            lines.append("- Follow up on pending tasks proactively.")
        if behav.get("use_accountability_nudges"):
            lines.append("- Use gentle accountability nudges.")
        if behav.get("preserve_established_routines"):
            lines.append("- Respect and preserve user's established routines.")
        if behav.get("offer_structured_plans"):
            lines.append("- When user is stressed, offer structured action plans.")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Goals
    goals = rules.get("goal_rules", {})
    if goals:
        lines = ["ACTIVE GOALS:"]
        if goals.get("high_priority_goals"):
            for g in goals["high_priority_goals"]:
                lines.append(f"- [HIGH] {g}")
        if goals.get("active_goals_summary"):
            for g in goals["active_goals_summary"]:
                if g["priority"] != "high":
                    deadline = f" (by {g['deadline']})" if g.get("deadline") else ""
                    lines.append(f"- [{g['priority'].upper()}] {g['goal']}{deadline}")
        if goals.get("reference_goals_in_relevant_decisions"):
            lines.append("- Reference these goals when making relevant suggestions.")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Health
    health = rules.get("health_rules", {})
    if health:
        lines = ["HEALTH & ENERGY RULES:"]
        if health.get("burnout_warning"):
            lines.append("- ⚠️ Burnout signals detected. Prioritize rest and reduce load.")
        if health.get("suggest_energy_management"):
            lines.append("- Suggest energy management strategies.")
        if health.get("energy_peak"):
            lines.append(f"- User's energy peaks in the {health['energy_peak']}.")
        if health.get("nudge_physical_activity"):
            lines.append("- Gently nudge towards physical activity.")
        if health.get("suggest_sleep_hygiene"):
            lines.append("- Suggest better sleep habits when relevant.")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Episodic
    episodic = rules.get("episodic_context_rules", {})
    if episodic:
        lines = ["CURRENT LIFE CONTEXT:"]
        if episodic.get("current_situations"):
            for s in episodic["current_situations"]:
                lines.append(f"- {s}")
        if episodic.get("adjust_priorities_for"):
            lines.append("- Adjust priorities and tone for these situations.")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    return "\n\n".join(sections) if sections else ""
