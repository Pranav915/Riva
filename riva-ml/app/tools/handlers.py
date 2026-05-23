"""
Handlers for executing Gemini Live tools.
"""
import asyncio
from typing import Dict, Any, Callable, Tuple
from datetime import datetime as dt
from bson import ObjectId

from services.finance_query_service import FinanceQueryService
from services.memory_service import MemoryService
from services.calendar_service import CalendarService
from services.todo_service import TodoService
from services.schedule_context import ScheduleContext
from services.budget_service import BudgetService

BACKGROUND_TOOLS = {"add_transaction", "update_event", "delete_event", "add_todo", "complete_todo", "delete_todo",
                    "update_expense", "delete_expense"}

ACK_MESSAGES = {
    "add_transaction": "recorded.",
    "schedule_event":  "scheduled.",
    "update_event":    "updated.",
    "delete_event":    "deleted.",
    "add_todo":        "added to your list.",
    "complete_todo":   "marked as done.",
    "delete_todo":     "removed from your list.",
    "update_expense":  "updated.",
    "delete_expense":  "deleted.",
}

def get_tool_handler(user_id: str, db_collections: Dict[str, Any]) -> Callable[[str, Dict[str, Any]], Any]:
    """
    Returns an async handler function configured for the current session.
    """
    transactions_collection = db_collections["transactions"]
    user_memory_collection = db_collections["user_memory"]
    calendar_tokens_collection = db_collections["calendar_tokens"]
    todos_collection = db_collections["todos"]
    budgets_collection = db_collections["budgets"]

    finance_query_service = FinanceQueryService(transactions_collection)
    memory_service  = MemoryService(user_memory_collection)
    calendar_service = CalendarService(calendar_tokens_collection)
    todo_service = TodoService(todos_collection)
    schedule_context = ScheduleContext(calendar_service=calendar_service, todo_service=todo_service)
    budget_svc = BudgetService(budgets_collection, transactions_collection)

    async def _execute_tool(name: str, args: Dict[str, Any]) -> Dict:
        context = {"user_id": user_id}

        if name == "add_transaction":
            try:
                # ── Type resolution ─────────────────────────────────────────
                VALID_TYPES = {"expense", "income", "lended", "borrowed"}
                tx_type = str(args.get("transaction_type", "expense")).lower().strip()
                if tx_type not in VALID_TYPES:
                    tx_type = "expense"

                # ── Category resolution ────────────────────────────────────
                VALID_CATS = {
                    "food", "transport", "shopping", "bills",
                    "entertainment", "health", "personal",
                    "salary", "investment", "other",
                }
                DEFAULT_CAT = {
                    "income":   "salary",
                    "lended":   "other",
                    "borrowed": "other",
                    "expense":  "other",
                }
                category = str(args.get("category", "")).lower().strip()
                if not category or category not in VALID_CATS:
                    category = DEFAULT_CAT.get(tx_type, "other")

                amount   = float(args.get("amount", 0))
                desc     = str(args.get("description") or category)
                date_str = args.get("date") or dt.now().strftime("%Y-%m-%d")
                person   = args.get("person", "")

                doc = {
                    "user_id":     user_id,
                    "type":        tx_type,
                    "amount":      amount,
                    "currency":    "INR",
                    "category":    category,
                    "description": desc,
                    "date":        date_str,
                    "created_at":  dt.utcnow(),
                }
                if person:
                    doc["person"] = person

                await transactions_collection.insert_one(doc)
                print(f"[GEMINI_LIVE][BG] add_transaction: {tx_type} ₹{amount} / {category} / {desc}")
                return {"status": "success", "type": tx_type}
            except Exception as e:
                print(f"[GEMINI_LIVE][BG] add_transaction error: {e}")
                return {"status": "error", "message": str(e)}

        elif name == "query_spending":
            resp_text = await finance_query_service.handle_query(
                user_id=user_id,
                user_input=f"How much did I spend {args.get('time_range', 'this month')}?",
                memory={},
            )
            return {"status": "success", "response": resp_text}

        elif name == "schedule_event":
            from dateutil.parser import parse as dtparse
            from datetime import timedelta
            import pytz

            IST = pytz.timezone("Asia/Kolkata")

            def to_ist_iso(time_str: str) -> str:
                parsed = dtparse(time_str)
                if parsed.tzinfo is None:
                    parsed = IST.localize(parsed)
                else:
                    parsed = parsed.astimezone(IST)
                return parsed.isoformat()

            start_iso = to_ist_iso(args["start_time"])
            end_str   = args.get("end_time")
            if end_str:
                end_iso = to_ist_iso(end_str)
            else:
                naive_start = dtparse(args["start_time"]).replace(tzinfo=None)
                end_iso = to_ist_iso((naive_start + timedelta(hours=1)).isoformat())

            # Conflict check
            conflicts = await calendar_service.check_conflicts(
                user_id=user_id,
                start_time=start_iso,
                end_time=end_iso,
            )
            if conflicts:
                names = ", ".join(f"'{e['title']}' at {e['start_time']}" for e in conflicts[:3])
                return {
                    "status": "conflict",
                    "message": f"There's a scheduling conflict: {names}. Ask what to do.",
                    "conflicting_events": [{"title": e["title"], "start": e["start_time"], "id": e["id"]} for e in conflicts],
                }

            result = await calendar_service.create_event(
                user_id=user_id,
                title=args["title"],
                start_time=start_iso,
                end_time=end_iso,
                description=args.get("description", ""),
                timezone="Asia/Kolkata",
            )
            if result:
                return {"status": "success", "event_id": result.get("id")}
            return {"status": "error", "message": "Calendar not connected or event creation failed."}

        elif name == "update_event":
            from dateutil.parser import parse as dtparse
            import pytz
            IST = pytz.timezone("Asia/Kolkata")

            updates = {k: v for k, v in args.items() if k != "event_id"}
            for time_field in ("start_time", "end_time"):
                if time_field in updates:
                    parsed = dtparse(updates[time_field])
                    if parsed.tzinfo is None:
                        parsed = IST.localize(parsed)
                    else:
                        parsed = parsed.astimezone(IST)
                    updates[time_field] = parsed.isoformat()

            result = await calendar_service.update_event(
                user_id=user_id,
                event_id=args["event_id"],
                updates=updates,
            )
            if result:
                return {"status": "success"}
            return {"status": "error", "message": "Failed to update — check event_id."}

        elif name == "delete_event":
            deleted = await calendar_service.delete_event(
                user_id=user_id,
                event_id=args["event_id"],
            )
            if deleted:
                return {"status": "success"}
            return {"status": "error", "message": "Failed to delete — check event_id."}

        elif name == "list_events":
            from datetime import datetime, timedelta
            days = int(args.get("days", 1))
            events = await calendar_service.list_events(
                user_id,
                time_min=datetime.utcnow(),
                time_max=datetime.utcnow() + timedelta(days=days),
            )
            return {"status": "success", "events": events or []}

        elif name == "add_todo":
            try:
                result = await todo_service.add_todo(
                    user_id=user_id,
                    title=args.get("title", "Untitled task"),
                    due_date=args.get("due_date") or dt.now().strftime("%Y-%m-%d"),
                    due_time=args.get("due_time"),
                    priority=args.get("priority", "medium"),
                    category=args.get("category", "other"),
                )
                print(f"[GEMINI_LIVE][BG] add_todo written: {result.get('title')}")
                return {"status": "success", "todo_id": result.get("_id")}
            except Exception as e:
                print(f"[GEMINI_LIVE][BG] add_todo error: {e}")
                return {"status": "error", "message": str(e)}

        elif name == "list_todos":
            from datetime import datetime, timedelta
            days = int(args.get("days", 1))
            status = args.get("status", "pending")
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

            todos = await todo_service.get_todos(
                user_id,
                status=status,
                start_date=start_date,
                end_date=end_date,
                limit=20,
            )
            schedule_summary = ""
            try:
                schedule_summary = await schedule_context.get_context_for_prompt(user_id, days=days)
            except Exception:
                pass
            return {
                "status": "success",
                "todos": todos or [],
                "schedule_context": schedule_summary,
            }

        elif name == "complete_todo":
            try:
                result = await todo_service.complete_todo(user_id, args["todo_id"])
                if result:
                    return {"status": "success", "title": result.get("title")}
                return {"status": "error", "message": "Todo not found."}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif name == "delete_todo":
            try:
                deleted = await todo_service.delete_todo(user_id, args["todo_id"])
                if deleted:
                    return {"status": "success"}
                return {"status": "error", "message": "Todo not found."}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif name == "list_expenses":
            from datetime import timedelta
            days    = int(args.get("days", 7))
            limit   = int(args.get("limit", 10))
            cat     = args.get("category", "").lower().strip() or None
            start   = dt.utcnow() - timedelta(days=days)
            q = {
                "user_id": user_id,
                "$or": [
                    {"created_at": {"$gte": start}},
                    {"date": {"$gte": start.strftime("%Y-%m-%d")}},
                ],
            }
            if cat:
                q["category"] = cat
            cursor = transactions_collection.find(q).sort("created_at", -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            items = []
            for d in docs:
                date_raw = d.get("date") or d.get("created_at", "")
                date_str = date_raw.strftime("%Y-%m-%d") if hasattr(date_raw, "strftime") else str(date_raw)[:10]
                items.append({
                    "id":          str(d["_id"]),
                    "amount":      d.get("amount"),
                    "category":    d.get("category"),
                    "description": d.get("description", ""),
                    "date":        date_str,
                })
            return {"status": "success", "expenses": items, "count": len(items)}

        elif name == "update_expense":
            expense_id = args.get("expense_id", "")
            try:
                oid = ObjectId(expense_id)
            except Exception:
                return {"status": "error", "message": f"Invalid expense_id: {expense_id}"}

            updates: Dict[str, Any] = {}
            if "amount"      in args: updates["amount"]      = float(args["amount"])
            if "category"    in args: updates["category"]    = str(args["category"]).lower()
            if "description" in args: updates["description"] = str(args["description"])
            if "date"        in args: updates["date"]        = str(args["date"])
            if not updates:
                return {"status": "error", "message": "No fields to update."}

            updates["updated_at"] = dt.utcnow()
            result = await transactions_collection.update_one(
                {"_id": oid, "user_id": user_id},
                {"$set": updates},
            )
            if result.matched_count == 0:
                return {"status": "error", "message": "Expense not found — check the ID."}
            print(f"[GEMINI_LIVE][BG] update_expense {expense_id}: {updates}")
            return {"status": "success"}

        elif name == "delete_expense":
            expense_id = args.get("expense_id", "")
            try:
                oid = ObjectId(expense_id)
            except Exception:
                return {"status": "error", "message": f"Invalid expense_id: {expense_id}"}

            result = await transactions_collection.delete_one({"_id": oid, "user_id": user_id})
            if result.deleted_count == 0:
                return {"status": "error", "message": "Expense not found — check the ID."}
            print(f"[GEMINI_LIVE][BG] delete_expense {expense_id} done")
            return {"status": "success"}

        elif name == "get_budget_status":
            now = dt.utcnow()
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            pipeline = [
                {"$match": {
                    "user_id": user_id,
                    "type": "expense",
                    "$or": [
                        {"created_at": {"$gte": start}},
                        {"date": {"$gte": start.strftime("%Y-%m-%d")}},
                    ],
                }},
                {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
            ]
            cursor = transactions_collection.aggregate(pipeline)
            rows = await cursor.to_list(length=50)
            spending = {r["_id"]: r["total"] for r in rows}
            status = await budget_svc.get_budget_status(user_id, spending)
            return {"status": "success", "budget_status": status}

        elif name == "set_budget":
            category = str(args.get("category", "other")).lower()
            limit    = float(args.get("limit", 0))
            if limit <= 0:
                return {"status": "error", "message": "Budget limit must be greater than 0."}
            await budget_svc.set_category_budget(user_id, category, limit)
            print(f"[GEMINI_LIVE] set_budget {category}=₹{limit}")
            return {"status": "success", "category": category, "limit": limit}

        elif name == "end_conversation":
            return {"status": "end_conversation"}

        return {"error": f"Unknown tool: {name}"}

    async def _run_in_background(name: str, args: Dict[str, Any]):
        try:
            result = await _execute_tool(name, args)
            if result.get("status") == "error":
                print(f"[GEMINI_LIVE][BG] Tool '{name}' returned error: {result}")
            else:
                print(f"[GEMINI_LIVE][BG] Tool '{name}' completed successfully.")
        except Exception as e:
            print(f"[GEMINI_LIVE][BG] Tool '{name}' raised exception: {e}")

    async def handle_tool_call(name: str, args: Dict[str, Any]) -> Dict:
        print(f"[GEMINI_LIVE] Tool call: {name}  args={args}")
        if name in BACKGROUND_TOOLS:
            asyncio.create_task(_run_in_background(name, args))
            return {"status": "queued", "message": ACK_MESSAGES.get(name, "done.")}
        return await _execute_tool(name, args)

    return handle_tool_call
