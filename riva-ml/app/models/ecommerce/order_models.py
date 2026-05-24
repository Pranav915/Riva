from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class EcommerceOrder(BaseModel):
    user_id: str
    order_id: str
    order_status: str = "pending"  # pending | shipped | delivered | cancelled
    merchant: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    item_summary: Optional[List[Dict[str, Any]]] = None
    tracking_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
