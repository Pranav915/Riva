"""Gmail integration routes.
Endpoints:
 - GET /gmail/status
 - GET /gmail/oauth/url
 - GET /gmail/oauth/callback
 - POST /gmail/fetch
 - GET /gmail/actions
 - GET /gmail/orders
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

from services.gmail_service import GmailService
from services.email_processor import EmailProcessor
from services.db import gmail_tokens_collection, email_state_collection, parsed_emails_collection, orders_collection

load_dotenv()

router = APIRouter(prefix="/gmail", tags=["Gmail"])

_gmail_service = GmailService(gmail_tokens_collection, email_state_collection)
_email_processor = EmailProcessor(_gmail_service)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


class FetchRequest(BaseModel):
    user_id: Optional[str] = None


@router.get("/status")
async def gmail_status(user_id: str = Query(...)):
    connected = await _gmail_service.is_connected(user_id)
    return {"connected": connected, "user_id": user_id}


@router.get("/oauth/url")
async def get_oauth_url(user_id: str = Query(...)):
    redirect_uri = f"{BASE_URL}/gmail/oauth/callback"
    url = await _gmail_service.get_oauth_url(user_id, redirect_uri)
    return {"oauth_url": url}


@router.get("/oauth/callback")
async def oauth_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    if error:
        return {"success": False, "error": error}
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    user_id = state
    redirect_uri = f"{BASE_URL}/gmail/oauth/callback"
    success = await _gmail_service.exchange_code(code, user_id, redirect_uri)
    if success:
        return {"success": True, "message": "Gmail connected", "user_id": user_id}
    else:
        raise HTTPException(status_code=400, detail="Failed to connect Gmail")


@router.post("/fetch")
async def fetch_emails(req: FetchRequest):
    user_id = req.user_id
    if user_id:
        result = await _email_processor.fetch_and_process(user_id)
        return {"success": True, "result": result}
    else:
        # In absence of user_id, trigger for all users with tokens (limited safety)
        cursor = gmail_tokens_collection.find({})
        tasks = []
        async for doc in cursor:
            uid = doc.get("user_id")
            if uid:
                r = await _email_processor.fetch_and_process(uid)
                tasks.append({"user_id": uid, "result": r})
        return {"success": True, "runs": tasks}


@router.get("/actions")
async def list_actions(user_id: str = Query(...)):
    cursor = parsed_emails_collection.find({"user_id": user_id, "action_required": True}).sort("created_at", -1).limit(50)
    results = []
    async for d in cursor:
        d["_id"] = str(d.get("_id"))
        results.append(d)
    return {"count": len(results), "items": results}


@router.get("/orders")
async def list_orders(user_id: str = Query(...), status: Optional[str] = Query(None)):
    q = {"user_id": user_id}
    if status:
        q["order_status"] = status
    cursor = orders_collection.find(q).sort("updated_at", -1).limit(100)
    results = []
    async for d in cursor:
        d["_id"] = str(d.get("_id"))
        results.append(d)
    return {"count": len(results), "orders": results}


@router.get("/orders/summary")
async def orders_summary(user_id: str = Query(...)):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$order_status", "count": {"$sum": 1}}}
    ]
    cursor = orders_collection.aggregate(pipeline)
    stats = await cursor.to_list(length=20)
    summary = {s["_id"]: s["count"] for s in stats}
    total = sum(summary.values())
    return {"total": total, "breakdown": summary}


@router.get("/assistant/summary")
async def assistant_summary(user_id: str = Query(...)):
    # Action emails
    actions_cursor = parsed_emails_collection.find({"user_id": user_id, "action_required": True})
    actions = []
    async for a in actions_cursor:
        actions.append({"subject": a.get("subject"), "task": a.get("parsed_task"), "priority": a.get("priority")})

    # Orders summary
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$order_status", "count": {"$sum": 1}}}
    ]
    cursor = orders_collection.aggregate(pipeline)
    stats = await cursor.to_list(length=20)
    breakdown = {s["_id"]: s["count"] for s in stats}

    summary_text = f"You have {len(actions)} action-required emails. Orders: {breakdown}."
    return {"summary": summary_text, "actions": actions, "orders_breakdown": breakdown}
