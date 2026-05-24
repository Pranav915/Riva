from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class GmailToken(BaseModel):
    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: Optional[str] = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EmailState(BaseModel):
    user_id: str
    last_read_at: Optional[datetime] = None
    history_id: Optional[str] = None
    updated_at: Optional[datetime] = None


class ParsedEmail(BaseModel):
    user_id: str
    message_id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    snippet: Optional[str] = None
    from_address: Optional[str] = None
    to_addresses: Optional[str] = None
    date: Optional[datetime] = None
    action_required: bool = False
    action_type: Optional[str] = None  # e.g. "register", "apply", "order", "follow_up"
    parsed_task: Optional[str] = None
    parsed_due_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_headers: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
