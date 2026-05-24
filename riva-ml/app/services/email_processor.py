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
    "Only mark emails that require explicit user action (i.e., the user must do something).\n"
    "Detect tasks such as: register, apply, renew, submit, order, pay, track_shipment, return, book, attend, confirm.\n"
    "Output ONLY valid JSON matching the schema: {\n"
    "  \"is_action_required\": boolean,\n"
    "  \"action_summary\": string|null,\n"
    "  \"task_title\": string|null,\n"
    "  \"due_date\": ISO8601 string|null,\n"
    "  \"priority\": one of [urgent, high, medium, low] or null,\n"
    "  \"category\": one of [registration, application, renewal, payment, order, shipment, return, booking, appointment, other] or null,\n"
    "  \"order_details\": {\"order_id\":string, \"merchant\":string, \"status\":string, \"items\": [ {\"name\":string, \"qty\":int } ], \"tracking_number\":string|null, \"expected_delivery\":ISO|null } | null\n"
    "}\n"
    "Do not include any extra keys. If uncertain, set fields to null or false.\n"
    "Email headers and snippet below:\nSubject: {subject}\nFrom: {from_addr}\nDate: {date}\nSnippet: {snippet}\nFullHeaders: {headers}\n"
)


class EmailProcessor:
    def __init__(self, gmail_service: GmailService, calendar_service: CalendarService = None, schedule_context: ScheduleContext = None, llm_api_key: str = None):
        self.gmail = gmail_service
        self.todo_service = TodoService(todos_collection)
        self.calendar_service = calendar_service
        self.schedule_context = schedule_context
        self.llm = create_llm_provider(LLMProviderType.OPENAI, api_key=llm_api_key or OPENAI_API_KEY)

    async def _call_llm(self, subject: str, from_addr: str, date: str, snippet: str, headers: dict) -> EmailAnalysisResult:
        prompt = PROMPT_TEMPLATE.format(subject=subject or "", from_addr=from_addr or "", date=date or "", snippet=snippet or "", headers=json.dumps(headers or {}))
        messages = [{"role": "system", "content": "You extract structured JSON from emails."}, {"role": "user", "content": prompt}]
        try:
            text = await self.llm.generate_response(messages, temperature=0.0, max_tokens=400)
            # Try to parse JSON from text
            try:
                data = json.loads(text)
            except Exception:
                # attempt to extract JSON substring
                import re
                m = re.search(r"\{.*\}", text, flags=re.S)
                if m:
                    data = json.loads(m.group(0))
                else:
                    data = {"is_action_required": False}

            return EmailAnalysisResult(**data)
        except Exception as e:
            print(f"[EMAIL_PROCESSOR][LLM] Error: {e}")
            return EmailAnalysisResult(is_action_required=False)

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
        messages = await self.gmail.list_messages_since(user_id, max_results=max_messages)
        processed = 0
        created_todos = 0
        upserted_orders = 0

        for m in messages:
            mid = m.get("id")
            if not mid:
                continue
            msg = await self.gmail.get_message(user_id, mid)
            if not msg:
                continue

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject")
            snippet = msg.get("snippet")
            from_addr = headers.get("From")
            date_str = headers.get("Date")
            thread_id = msg.get("threadId")

            analysis = await self._call_llm(subject, from_addr, date_str, snippet, headers)

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

        return {"processed": processed, "todos_created": created_todos, "orders_upserted": upserted_orders}
