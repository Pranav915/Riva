"""
Gemini Multimodal Live Router

Architecture:
  Browser (mic PCM) → this router → Gemini Live API (bidi WebSocket)
  Gemini may call tools → we execute them and send results back.

Improvements:
  - update_event / delete_event tools added
  - Parallel tool execution: all tool_calls in one Gemini turn run concurrently
  - Fire-and-forget for write tools (add_expense, schedule_event, update_event,
    delete_event): Gemini gets an immediate ACK so it can start speaking, and
    the actual DB/API work happens in the background.
  - Query tools (query_spending, list_events) are still awaited because the
    result is part of the answer.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import os
import json
import asyncio
import base64
from google import genai
from google.genai import types
from typing import Dict, Any

from tools import TOOLS_SCHEMA, get_tool_handler
from services.riva_brain import build_riva_system_prompt, get_time_context
from services.db import (
    user_memory_collection,
    transactions_collection,
    calendar_tokens_collection,
    todos_collection,
    budgets_collection
)

router = APIRouter(tags=["Gemini Live"])

# Closing phrases that trigger conversation end
END_PHRASES = {"bye", "goodbye", "see you", "that's all", "thanks bye", "exit", "quit", "close"}

async def get_tools_and_handlers(user_id: str):
    """Build Gemini tool declarations and an async handler for a user session."""
    collections = {
        "transactions": transactions_collection,
        "user_memory": user_memory_collection,
        "calendar_tokens": calendar_tokens_collection,
        "todos": todos_collection,
        "budgets": budgets_collection
    }
    handle_tool_call = get_tool_handler(user_id, collections)
    return TOOLS_SCHEMA, handle_tool_call


# ---------------------------------------------------------------------------
# System prompt builder for Gemini Live
# Sent ONCE per session (connection time) — zero per-turn token cost.
# ---------------------------------------------------------------------------
def _build_gemini_system_prompt(schedule_ctx_text: str = "") -> str:
    """
    Build the Gemini Live system_instruction by composing:
      1. RIVA Brain persona + current time context + productivity skills
      2. Gemini-specific tool rules (timezone, TO-DO vs Calendar, response style)
      3. Optional live schedule context

    The result is sent once at session start — not on every turn.
    Prompt length: ~1,200 tokens (was ~350). Cost impact: negligible because
    Gemini Live caches the system_instruction across the session.
    """
    time_ctx = get_time_context()

    # Core RIVA persona + productivity skills (planning mode = rich skills)
    base = build_riva_system_prompt(
        mode="planning",
        time_ctx=time_ctx,
        extra_skills=["finance", "wellness", "habits"],
    )

    # Gemini Live-specific rules (tool usage, timezone, voice style)
    gemini_rules = """
VOICE & TOOL RULES (Gemini Live):
- You are voice-first. Every response will be spoken aloud — be concise and natural.
- TIMEZONE: User is in India (IST, UTC+5:30). All datetimes must use +05:30 offset.
  Example: '2026-04-28T15:00:00+05:30'. Never assume UTC.

TO-DO vs CALENDAR (critical distinction):
- Tasks/to-dos → trackable items with no fixed time slot → add_todo, list_todos, complete_todo, delete_todo
- Events/meetings → time-bound calendar entries → schedule_event, list_events, update_event, delete_event
- When adding a task, check schedule context to suggest a good time if relevant.
- When listing tasks, mention overlapping calendar events.

TRANSACTION MANAGEMENT (add_transaction tool):
- Use add_transaction for ALL money movements — expense, income, lended, borrowed.
- ALWAYS pass the correct transaction_type:
    expense  → user spent money (food, shopping, bills, etc.)
    income   → user received money (salary, freelance, gift, refund)
    lended   → user gave money to someone ("I gave Rahul ₹500")
    borrowed → user received money as a loan ("I borrowed ₹1000 from mom")
- For lended/borrowed, also pass person="<name>" when mentioned.
- To update or delete a transaction: call list_expenses first to find the ID, then update_expense or delete_expense.
- Example: "I paid ₹200 for lunch" → add_transaction(transaction_type="expense", amount=200, category="food", description="lunch")
- Example: "I got my salary ₹50000" → add_transaction(transaction_type="income", amount=50000, category="salary", description="salary")
- Example: "I lent Rahul ₹500" → add_transaction(transaction_type="lended", amount=500, category="other", description="lent to Rahul", person="Rahul")

BUDGET TOOLS:
- get_budget_status → shows this month's spending vs limits. Call proactively after any large expense.
- set_budget → sets a monthly limit for a category. E.g. user says "set food budget to 8000".
- After recording an expense: if that category is at warning/over, mention it in one sentence.

TOOL BEHAVIOUR:
- For write operations: confirm in ONE short sentence. Never repeat back all the details.
- For query results (spending, events, tasks): give the key numbers/names directly, no filler.
- status=error: briefly tell the user what went wrong.
- status=conflict: name the conflicting event and ask what to do.
- For update/delete: call list_* first to get the ID, then act.
- You may call multiple tools in one turn when needed.
- If the user says bye/goodbye: say a brief farewell and call end_conversation.

PROACTIVE BEHAVIOUR:
- After any expense, call get_budget_status if the category might be near its limit.
- After adding a todo, if there's a free slot on the calendar, suggest using it.
- Keep proactive additions to ≤1 sentence — don't overwhelm.
"""

    parts = [base.strip(), gemini_rules.strip()]

    if schedule_ctx_text:
        parts.append(f"CURRENT SCHEDULE CONTEXT:\n{schedule_ctx_text}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@router.websocket("/gemini-live")
async def gemini_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[GEMINI_LIVE] WebSocket connected")

    # ── Auth ──────────────────────────────────────────────────────────
    user_id = "anonymous"
    try:
        token = websocket.query_params.get("token")
        if token and token != "mock_token":
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("user_id") or decoded.get("sub") or "anonymous"
    except Exception as e:
        print(f"[GEMINI_LIVE] Auth warning: {e}")

    # ── API key ───────────────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        await websocket.send_json({"error": "GEMINI_API_KEY not configured on backend."})
        await websocket.close()
        return

    print(f"[GEMINI_LIVE] API key loaded ({api_key[:8]}…), user={user_id}")

    # ── Build session ─────────────────────────────────────────────────
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    tools, handle_tool_call = await get_tools_and_handlers(user_id)

    # Build shared schedule context for the system prompt
    schedule_ctx_text = ""
    try:
        from services.todo_service import TodoService as _TS
        from services.schedule_context import ScheduleContext as _SC
        from services.calendar_service import CalendarService as _CS
        from services.db import calendar_tokens_collection as _ctc, todos_collection as _tc
        _sc = _SC(calendar_service=_CS(_ctc), todo_service=_TS(_tc))
        schedule_ctx_text = await _sc.get_context_for_prompt(user_id, days=2)
    except Exception as e:
        print(f"[GEMINI_LIVE] Schedule context build error: {e}")

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        tools=tools,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part(text=_build_gemini_system_prompt(
                schedule_ctx_text=schedule_ctx_text,
            ))],
        ),
    )

    # gemini-live-2.5-flash-preview is the canonical Live API model that supports:
    # - send_realtime_input (streaming PCM audio)
    # - speech_config with PrebuiltVoiceConfig
    # - response_modalities=["AUDIO"]
    # - function calling / tool responses
    # gemini-2.5-flash-native-audio-latest is a DIFFERENT model (native audio generation,
    # not the bidirectional Live API) and returns 1008 with these features.
    # Free tier: gemini-2.0-flash-live-001
    # Paid/preview tier: gemini-2.5-flash-preview-native-audio-dialog
    model_id = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
    MAX_RECONNECT_ATTEMPTS = 5

    # The browser WebSocket stays open across Gemini reconnects.
    # Only the Gemini session is re-established on transient errors.
    for attempt in range(MAX_RECONNECT_ATTEMPTS):
        try:
            if attempt > 0:
                wait = min(2 ** attempt, 16)  # 2, 4, 8, 16 seconds
                print(f"[GEMINI_LIVE] Reconnect attempt {attempt}/{MAX_RECONNECT_ATTEMPTS} in {wait}s…")
                await websocket.send_json({"type": "reconnecting", "attempt": attempt})
                await asyncio.sleep(wait)

            async with client.aio.live.connect(model=model_id, config=config) as session:
                print(f"[GEMINI_LIVE] Connected to Gemini Live API (attempt {attempt + 1})")
                if attempt > 0:
                    await websocket.send_json({"type": "reconnected"})

                # shared event so receive_from_frontend can stop sending when
                # the Gemini session is closing
                session_alive = asyncio.Event()
                session_alive.set()

                # ── Task 1: Gemini → Frontend ─────────────────────────────
                async def receive_from_gemini():
                    # session.receive() covers exactly ONE turn then exits.
                    # Loop to handle unlimited multi-turn conversations.
                    while True:
                        async for message in session.receive():
                            # ── Audio chunks ──────────────────────────────
                            if message.server_content:
                                if message.server_content.model_turn:
                                    for part in message.server_content.model_turn.parts:
                                        if part.inline_data:
                                            audio_b64 = base64.b64encode(
                                                part.inline_data.data
                                            ).decode("utf-8")
                                            await websocket.send_json(
                                                {"type": "audio", "data": audio_b64}
                                            )
                                if message.server_content.turn_complete:
                                    await websocket.send_json({"type": "turn_complete"})

                            # ── Tool calls (possibly multiple per turn) ───
                            if message.tool_call:
                                calls = message.tool_call.function_calls
                                should_close = False

                                # Execute all tool calls in this turn CONCURRENTLY
                                async def resolve_call(call):
                                    result = await handle_tool_call(call.name, call.args)
                                    return call, types.FunctionResponse(
                                        name=call.name,
                                        id=call.id,
                                        response=result,
                                    )

                                resolved = await asyncio.gather(
                                    *[resolve_call(c) for c in calls]
                                )

                                # Send all responses, check for end_conversation
                                for original_call, resp in resolved:
                                    if original_call.name == "end_conversation":
                                        should_close = True
                                    await session.send_tool_response(
                                        function_responses=resp
                                    )

                                if should_close:
                                    print("[GEMINI_LIVE] Conversation ended by user.")
                                    await websocket.send_json({"type": "session_end"})
                                    await websocket.close()
                                    return

                # ── Task 2: Frontend → Gemini ─────────────────────────────
                async def receive_from_frontend():
                    try:
                        while True:
                            data = await websocket.receive()
                            if "bytes" in data:
                                # Raw PCM from browser mic (16 kHz, 16-bit, mono)
                                await session.send_realtime_input(
                                    audio=types.Blob(
                                        data=data["bytes"],
                                        mime_type="audio/pcm;rate=16000",
                                    )
                                )
                            elif "text" in data:
                                msg = json.loads(data["text"])
                                msg_type = msg.get("type")

                                if msg_type == "barge_in":
                                    # User spoke while RIVA was talking.
                                    # Send activity_start so Gemini knows to stop
                                    # generating and pay attention to incoming audio.
                                    print("[GEMINI_LIVE] Barge-in detected — signalling Gemini")
                                    try:
                                        await session.send_realtime_input(
                                            activity_start=types.ActivityStart()
                                        )
                                    except Exception as e:
                                        print(f"[GEMINI_LIVE] activity_start error: {e}")

                                elif msg_type == "input_text":
                                    await session.send_client_content(
                                        turns=types.Content(
                                            role="user",
                                            parts=[types.Part(text=msg["text"])],
                                        ),
                                        turn_complete=True,
                                    )
                    except WebSocketDisconnect:
                        raise
                    except Exception as e:
                        print(f"[GEMINI_LIVE] Frontend receive error: {e}")

                await asyncio.gather(receive_from_gemini(), receive_from_frontend())
                break  # Clean exit — don't retry

        except WebSocketDisconnect:
            print("[GEMINI_LIVE] Browser WebSocket disconnected")
            break  # User closed the browser tab — stop completely

        except Exception as e:
            err_str = str(e)
            err_code = ""
            # Extract numeric WS close code from the error string
            import re as _re
            m = _re.search(r'(\d{4})', err_str)
            if m:
                err_code = m.group(1)

            # 1006 / 1011 / 1012 = network-level drops → transient, retry
            # 1008 (policy violation) / 1003 (unsupported data) = API rejects
            #   our request → fatal, do NOT retry (retrying won't help)
            TRANSIENT_CODES = {"1006", "1011", "1012"}
            FATAL_CODES     = {"1008", "1003", "1007", "1009", "1010"}

            is_transient = (
                err_code in TRANSIENT_CODES
                or "abnormal closure" in err_str
                or "ConnectionReset" in type(e).__name__
            )
            is_fatal_policy = err_code in FATAL_CODES

            if is_fatal_policy:
                # Policy/capability error — retrying will always fail
                print(f"[GEMINI_LIVE] Fatal API policy error ({err_code}): {e}")
                user_msg = (
                    "This Gemini model or feature is not enabled for your API key. "
                    "Check the model name and API key permissions."
                    if err_code == "1008" else
                    f"Gemini rejected the connection (error {err_code})."
                )
                try:
                    await websocket.send_json({"type": "error", "message": user_msg})
                except Exception:
                    pass
                break

            elif is_transient and attempt < MAX_RECONNECT_ATTEMPTS - 1:
                print(f"[GEMINI_LIVE] Transient disconnect ({err_code or e}) — will retry…")
                continue  # Go to next attempt

            else:
                print(f"[GEMINI_LIVE] Unhandled error: {e}")
                import traceback
                traceback.print_exc()
                try:
                    await websocket.send_json({"type": "error", "message": "Connection to Gemini lost. Please try again."})
                except Exception:
                    pass
                break
    else:
        # Exhausted all retries
        try:
            await websocket.send_json({"type": "error", "message": "Could not reconnect to Gemini after several attempts."})
        except Exception:
            pass

    print("[GEMINI_LIVE] Session ended")
