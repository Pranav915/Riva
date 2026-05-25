"""Email Processor - analyzes email content with LLM and updates todos/orders.

This module provides a lightweight pipeline that:
 - fetches messages via GmailService
 - parses headers/snippets
 - calls an LLM to classify and extract tasks or order info
 - writes ParsedEmail documents and upserts orders and todos
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from services.gmail_service import GmailService
from services.db import parsed_emails_collection, email_state_collection, orders_collection, todos_collection
from services.todo_service import TodoService
from services.schedule_context import ScheduleContext
from services.calendar_service import CalendarService
from providers.llm_provider import create_llm_provider, LLMProviderType
from pydantic import BaseModel
from bson import ObjectId
import os
import json
import traceback

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class EmailAnalysisResult(BaseModel):
    is_action_required: bool = False
    action_summary: Optional[str] = None
    task_title: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    order_details: Optional[dict] = None


PROMPT_TEMPLATE = (
    "You are an assistant that analyzes a single email and returns a JSON object.\n"
    "Only mark truly important work-related or action-required emails. Keep only:\n"
    "  1. submissions and meeting invitations/confirmations,\n"
    "  2. travel and booking-related emails (flights, hotels, rentals, appointments),\n"
    "  3. git/productivity tool notifications that require developer action,\n"
    "  4. other important action emails requiring a user response or task.\n"
    "Also keep recent delivered order notifications if they are clearly about an order delivered to the user.\n"
    "Ignore noise: sale mails, promotion mails, offers, marketing, newsletters, ads, coupons, and registration/confirmation emails that are not action items.\n"
    "Output ONLY valid JSON matching the schema: {{\n"
    "  \"is_action_required\": boolean,\n"
    "  \"action_summary\": string|null,\n"
    "  \"task_title\": string|null,\n"
    "  \"due_date\": ISO8601 string|null,\n"
    "  \"priority\": one of [urgent, high, medium, low] or null,\n"
    "  \"category\": one of [registration, application, renewal, payment, order, shipment, return, booking, appointment, productivity, other] or null,\n"
    "  \"order_details\": {{\"order_id\":string, \"merchant\":string, \"status\":string, \"items\": [ {{\"name\":string, \"qty\":int }} ], \"tracking_number\":string|null, \"expected_delivery\":ISO|null }} | null\n"
    "}}\n"
    "Do not include any extra keys. If uncertain, set fields to null or false.\n"
    "Email headers and snippet below:\nSubject: {subject}\nFrom: {from_addr}\nDate: {date}\nSnippet: {snippet}\nFullHeaders: {headers}\n"
)


class EmailProcessor:
    def __init__(self, gmail_service: GmailService, calendar_service: CalendarService = None, schedule_context: ScheduleContext = None, llm_api_key: str = None):
        self.gmail = gmail_service
        self.todo_service = TodoService(todos_collection)
        self.calendar_service = calendar_service
        self.schedule_context = schedule_context
        # Prefer Google generative models if GOOGLE_API_KEY is provided, otherwise use OpenAI
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            self.llm = create_llm_provider(LLMProviderType.GOOGLE, api_key=google_key, model=os.getenv("GOOGLE_MODEL"))
        else:
            self.llm = create_llm_provider(LLMProviderType.OPENAI, api_key=llm_api_key or OPENAI_API_KEY, model=os.getenv("OPENAI_MODEL"))

    async def _call_llm(self, subject: str, from_addr: str, date: str, snippet: str, headers: dict) -> EmailAnalysisResult:
        prompt = PROMPT_TEMPLATE.format(subject=subject or "", from_addr=from_addr or "", date=date or "", snippet=snippet or "", headers=json.dumps(headers or {}))
        messages = [{"role": "system", "content": "You extract structured JSON from emails."}, {"role": "user", "content": prompt}]
        try:
            text = await self.llm.generate_response(messages, temperature=0.0, max_tokens=400)
            # Try to parse JSON from text. Be defensive: LLM may include extra text.
            try:
                data = json.loads(text)
            except Exception:
                # attempt to extract a balanced JSON object substring
                raw = text or ""
                # find first '{'
                start = raw.find('{')
                data = None
                if start != -1:
                    depth = 0
                    end = -1
                    for i in range(start, len(raw)):
                        if raw[i] == '{':
                            depth += 1
                        elif raw[i] == '}':
                            depth -= 1
                            if depth == 0:
                                end = i + 1
                                break
                    if end != -1:
                        candidate = raw[start:end]
                        try:
                            data = json.loads(candidate)
                        except Exception:
                            data = None

                if data is None:
                    print(f"[EMAIL_PROCESSOR][LLM] Failed to parse JSON from LLM output:\n{raw}")
                    # Fallback: try to extract key fields with regex to be resilient to non-JSON outputs
                    def _extract_bool(txt, key):
                        import re
                        m = re.search(rf'"?{key}"?\s*[:=]\s*(true|false|True|False|1|0)', txt)
                        if m:
                            v = m.group(1)
                            return str(v).lower() in ("true", "1")
                        return False

                    def _extract_string(txt, key):
                        import re
                        # look for "key": "value" or key: "value"
                        m = re.search(rf'"?{key}"?\s*[:=]\s*"([^"]{{1,400}})"', txt)
                        if m:
                            return m.group(1).strip()
                        # fallback: look for single-quoted
                        m2 = re.search(rf"'{key}'\s*[:=]\s*'([^']{{1,400}})'", txt)
                        if m2:
                            return m2.group(1).strip()
                        return None

                    data = {
                        "is_action_required": _extract_bool(raw, "is_action_required"),
                        "action_summary": _extract_string(raw, "action_summary"),
                        "task_title": _extract_string(raw, "task_title"),
                        "due_date": _extract_string(raw, "due_date"),
                        "priority": _extract_string(raw, "priority"),
                        "category": _extract_string(raw, "category"),
                        "order_details": None,
                    }

            try:
                return EmailAnalysisResult(**data)
            except Exception as ve:
                print(f"[EMAIL_PROCESSOR][LLM] Validation error when building EmailAnalysisResult: {ve}\nRaw LLM output:\n{text}")
                return EmailAnalysisResult(is_action_required=False)
        except Exception as e:
            print(f"[EMAIL_PROCESSOR][LLM] Error: {e}")
            return EmailAnalysisResult(is_action_required=False)

    def _is_delivered_order(self, analysis: EmailAnalysisResult) -> bool:
        if not analysis.order_details:
            return False
        status = str(analysis.order_details.get("status", "")).lower()
        return any(keyword in status for keyword in ["deliver", "received", "completed", "arrived"])

    def _should_keep_email(self, analysis: EmailAnalysisResult) -> bool:
        if self._is_delivered_order(analysis):
            return True

        if not analysis.is_action_required:
            return False

        category = str(analysis.category or "").lower()
        blacklist = {"registration", "promotion", "sale", "offer", "marketing", "newsletter", "ads", "spam"}
        if category in blacklist:
            return False

        allowed = {"submission", "application", "booking", "flight", "appointment", "productivity", "git", "order", "shipment", "return", "payment", "meeting", "other"}
        if category in allowed:
            return True

        # Keep any remaining explicitly important action-required emails.
        return bool(analysis.task_title or analysis.action_summary)

    async def _schedule_time_block(self, user_id: str, title: str, duration_minutes: int = 30) -> Optional[dict]:
        if not self.calendar_service or not await self.calendar_service.is_connected(user_id):
            return None

        # Build a naive free-slot finder using ScheduleContext busy_slots
        start_dt = datetime.utcnow()
        # round up to next 30-minute slot
        minutes = (start_dt.minute // 30 + 1) * 30
        start_candidate = start_dt.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)

        # Check busy slots from schedule context
        busy = []
        if self.schedule_context:
            ctx = await self.schedule_context.get_full_context(user_id, days=1)
            for b in ctx.get("busy_slots", []):
                try:
                    busy_start = datetime.fromisoformat(b.get("start"))
                    busy_end = datetime.fromisoformat(b.get("end"))
                    busy.append((busy_start, busy_end))
                except Exception:
                    continue

        # Try next 12 slots (~6 hours)
        for i in range(12):
            s = start_candidate + timedelta(minutes=duration_minutes * i)
            e = s + timedelta(minutes=duration_minutes)
            conflict = False
            for bs, be in busy:
                if not (e <= bs or s >= be):
                    conflict = True
                    break
            if not conflict:
                # create event in user's calendar
                try:
                    ev = await self.calendar_service.create_event(user_id, title, s.isoformat(), e.isoformat())
                    return ev
                except Exception as ex:
                    print(f"[EMAIL_PROCESSOR] Failed to schedule event: {ex}")
                    return None

        return None

    async def fetch_and_process(self, user_id: str, max_messages: int = 25) -> Dict[str, Any]:
        print(f"[EMAIL_PROCESSOR] fetch_and_process starting for user {user_id}")

        # Read last synced state for this user and pass to GmailService to limit fetch
        last_synced_iso = None
        try:
            state = await email_state_collection.find_one({"user_id": user_id})
            if state:
                last_synced_iso = state.get("last_synced")
        except Exception:
            last_synced_iso = None

        messages = await self.gmail.list_messages_since(user_id, max_results=max_messages, since_iso=last_synced_iso)
        print(f"[EMAIL_PROCESSOR] Got {len(messages)} messages to process")
        processed = 0
        created_todos = 0
        upserted_orders = 0

        # Track the newest internalDate seen so we can update last_synced
        max_internal_ms = 0

        for m in messages:
            try:
                mid = m.get("id")
                if not mid:
                    continue
                print(f"[EMAIL_PROCESSOR] Processing message id={mid}")
                msg = await self.gmail.get_message(user_id, mid)
                if not msg:
                    continue

                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subject = headers.get("Subject")
                snippet = msg.get("snippet")
                from_addr = headers.get("From")
                date_str = headers.get("Date")
                thread_id = msg.get("threadId")
                # record internalDate (milliseconds since epoch) to advance last_synced later
                try:
                    internal_ms = int(msg.get("internalDate") or 0)
                    if internal_ms and internal_ms > max_internal_ms:
                        max_internal_ms = internal_ms
                except Exception:
                    pass

                print(f"[EMAIL_PROCESSOR] Calling LLM for message {mid} subject={subject}")
                analysis = await self._call_llm(subject, from_addr, date_str, snippet, headers)
                try:
                    print(f"[EMAIL_PROCESSOR] LLM analysis for {mid}: is_action_required={analysis.is_action_required}, task_title={analysis.task_title}, category={analysis.category}, order_details={analysis.order_details}")
                except Exception:
                    print(f"[EMAIL_PROCESSOR] LLM returned non-standard analysis for {mid}: {analysis}")
            except Exception as e:
                print(f"[EMAIL_PROCESSOR] Error processing message {m.get('id')}: {e}")
                traceback.print_exc()
                # skip this message but continue processing others
                continue

            if not self._should_keep_email(analysis):
                print(f"[EMAIL_PROCESSOR] Skipping message {mid} because it is not important")
                continue

            parsed_doc = {
                "user_id": user_id,
                "message_id": mid,
                "thread_id": thread_id,
                "subject": subject,
                "snippet": snippet,
                "from_address": from_addr,
                "action_required": analysis.is_action_required,
                "action_type": analysis.category,
                "action_summary": analysis.action_summary,
                "parsed_task": analysis.task_title,
                "parsed_due_date": analysis.due_date,
                "priority": analysis.priority,
                "metadata": {},
                "raw_headers": headers,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            await parsed_emails_collection.update_one({"user_id": user_id, "message_id": mid}, {"$set": parsed_doc}, upsert=True)

            # Action required -> create todo and maybe schedule
            if analysis.is_action_required and analysis.task_title:
                todo = await self.todo_service.add_todo(user_id, analysis.task_title, due_date=analysis.due_date or None, description=f"Source: gmail. {analysis.action_summary or ''}")
                # annotate todo with source
                try:
                    await todos_collection.update_one({"_id": ObjectId(todo.get("_id"))}, {"$set": {"source": "gmail"}})
                except Exception:
                    pass
                created_todos += 1

                # If urgent — try to auto-schedule a 30-minute block today
                if (analysis.priority or "").lower() in ("urgent", "high"):
                    try:
                        ev = await self._schedule_time_block(user_id, f"Work: {analysis.task_title}", duration_minutes=30)
                        if ev:
                            # annotate todo with scheduled event id
                            try:
                                await todos_collection.update_one({"_id": ObjectId(todo.get("_id"))}, {"$set": {"scheduled_event": ev.get("id")}})
                            except Exception:
                                pass
                    except Exception:
                        pass

            # Order handling
            if analysis.order_details:
                od = analysis.order_details
                order_id = od.get("order_id") or od.get("id")
                if order_id:
                    doc = {
                        "user_id": user_id,
                        "order_id": order_id,
                        "order_status": od.get("status", "pending"),
                        "merchant": od.get("merchant"),
                        "items": od.get("items"),
                        "tracking_number": od.get("tracking_number"),
                        "expected_delivery": od.get("expected_delivery"),
                        "last_update": datetime.utcnow(),
                    }
                    await orders_collection.update_one({"user_id": user_id, "order_id": order_id}, {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)
                    upserted_orders += 1

            processed += 1

        # Update last_synced state for this user based on newest internalDate seen
        try:
            if max_internal_ms and self.gmail and getattr(self.gmail, 'email_state_collection', None) is not None:
                from datetime import datetime as _dt
                iso_ts = _dt.utcfromtimestamp(max_internal_ms / 1000.0).isoformat()
                await email_state_collection.update_one({"user_id": user_id}, {"$set": {"last_synced": iso_ts, "last_internal_ms": max_internal_ms, "updated_at": datetime.utcnow()}}, upsert=True)
        except Exception as e:
            print(f"[EMAIL_PROCESSOR] Failed to update email_state for {user_id}: {e}")

        return {"processed": processed, "todos_created": created_todos, "orders_upserted": upserted_orders}
