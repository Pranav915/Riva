"""Gmail Service - lightweight Gmail REST API wrapper using per-user OAuth tokens.

This service mirrors the style of CalendarService and stores tokens in MongoDB.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

GOOGLE_GMAIL_CLIENT_ID = os.getenv("GOOGLE_CALENDAR_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID", ""))
GOOGLE_GMAIL_CLIENT_SECRET = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", os.getenv("GOOGLE_CLIENT_SECRET", ""))
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailService:
    def __init__(self, tokens_collection=None, email_state_collection=None):
        self.tokens_collection = tokens_collection
        self.email_state_collection = email_state_collection

    async def get_oauth_url(self, user_id: str, redirect_uri: str) -> str:
        from urllib.parse import urlencode

        params = {
            "client_id": GOOGLE_GMAIL_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": user_id,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def exchange_code(self, code: str, user_id: str, redirect_uri: str) -> bool:
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": GOOGLE_GMAIL_CLIENT_ID,
                        "client_secret": GOOGLE_GMAIL_CLIENT_SECRET,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
                token_data = response.json()

                if "access_token" not in token_data:
                    print(f"[GMAIL] Token exchange failed: {token_data}")
                    return False

                await self._store_tokens(user_id, token_data)
                return True
        except Exception as e:
            print(f"[GMAIL] Token exchange error: {e}")
            return False

    async def _store_tokens(self, user_id: str, token_data: Dict):
        if self.tokens_collection is None:
            return

        await self.tokens_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token"),
                    "token_type": token_data.get("token_type", "Bearer"),
                    "expires_at": datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600)),
                    "scope": token_data.get("scope", ""),
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {"created_at": datetime.utcnow()},
            },
            upsert=True,
        )

    async def _get_access_token(self, user_id: str) -> Optional[str]:
        if self.tokens_collection is None:
            return None

        token_doc = await self.tokens_collection.find_one({"user_id": user_id})
        if not token_doc:
            return None

        expires_at = token_doc.get("expires_at")
        if expires_at and datetime.utcnow() >= expires_at:
            refreshed = await self._refresh_token(user_id, token_doc.get("refresh_token"))
            if not refreshed:
                return None
            token_doc = await self.tokens_collection.find_one({"user_id": user_id})

        return token_doc.get("access_token")

    async def _refresh_token(self, user_id: str, refresh_token: str) -> bool:
        if not refresh_token:
            return False

        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": GOOGLE_GMAIL_CLIENT_ID,
                        "client_secret": GOOGLE_GMAIL_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                token_data = response.json()

                if "access_token" not in token_data:
                    print(f"[GMAIL] Token refresh failed: {token_data}")
                    return False

                token_data.setdefault("refresh_token", refresh_token)
                await self._store_tokens(user_id, token_data)
                return True
        except Exception as e:
            print(f"[GMAIL] Token refresh error: {e}")
            return False

    async def is_connected(self, user_id: str) -> bool:
        if self.tokens_collection is None:
            return False
        token_doc = await self.tokens_collection.find_one({"user_id": user_id})
        return token_doc is not None and token_doc.get("access_token") is not None

    async def disconnect(self, user_id: str) -> bool:
        if self.tokens_collection is None:
            return False
        await self.tokens_collection.delete_one({"user_id": user_id})
        return True

    async def _make_request(self, user_id: str, method: str, endpoint: str, params: Dict = None, body: Dict = None) -> Optional[Dict]:
        import httpx

        access_token = await self._get_access_token(user_id)
        if not access_token:
            print(f"[GMAIL] No access token for user {user_id}")
            return None

        base_url = "https://gmail.googleapis.com/gmail/v1"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{base_url}{endpoint}"
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body, params=params)
                else:
                    response = await client.request(method, url, headers=headers, json=body, params=params)

                if response.status_code in (200, 201):
                    return response.json()
                else:
                    print(f"[GMAIL] API error {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            print(f"[GMAIL] Request error: {e}")
            return None

    async def list_messages_since(self, user_id: str, query: str = None, since_history_id: str = None, max_results: int = 50) -> List[Dict]:
        """List message IDs since a history id or using Gmail query syntax."""
        params = {}
        if query:
            params["q"] = query
        if max_results:
            params["maxResults"] = max_results

        # If we have a history id we could use history.list but for simplicity list messages and filter by internalDate
        res = await self._make_request(user_id, "GET", f"/users/me/messages", params=params)
        if not res:
            return []
        return res.get("messages", [])

    async def get_message(self, user_id: str, message_id: str) -> Optional[Dict]:
        return await self._make_request(user_id, "GET", f"/users/me/messages/{message_id}", params={"format": "full"})
