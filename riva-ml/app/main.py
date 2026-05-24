"""
RIVA Backend - Main Application
Personal AI Secretary for productivity and finance.
"""
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio
import os

from services.gmail_service import GmailService
from services.email_processor import EmailProcessor
from services.db import gmail_tokens_collection

# Load environment variables
load_dotenv()

# Import routers
from routers import auth_router, user_router, stream_router, init_stt_provider, finance_router, calendar_router, todo_router, gemini_live_router, gmail_router

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Starting RIVA Backend...")
    # Initialize STT provider
    init_stt_provider()
    print("[OK] RIVA Backend ready")
    # Background Gmail fetcher
    gmail_fetch_enabled = os.getenv("GMAIL_FETCH_ENABLED", "true").lower() in ("1", "true", "yes")
    interval_hours = float(os.getenv("GMAIL_FETCH_INTERVAL_HOURS", "4"))
    max_per_run = int(os.getenv("GMAIL_FETCH_MAX_PER_RUN", "50"))
    delay_between = float(os.getenv("GMAIL_FETCH_DELAY_BETWEEN", "0.5"))

    bg_task = None
    if gmail_fetch_enabled:
        gmail_service = GmailService(gmail_tokens_collection, None)
        email_processor = EmailProcessor(gmail_service)

        async def _gmail_fetch_loop():
            print("[GMAIL_FETCH] Background fetch loop started")
            try:
                while True:
                    runs = 0
                    cursor = gmail_tokens_collection.find({})
                    async for doc in cursor:
                        if runs >= max_per_run:
                            break
                        uid = doc.get("user_id")
                        if not uid:
                            continue
                        try:
                            print(f"[GMAIL_FETCH] Processing user {uid}")
                            await email_processor.fetch_and_process(uid, max_messages=25)
                        except Exception as e:
                            print(f"[GMAIL_FETCH] Error for user {uid}: {e}")
                        runs += 1
                        await asyncio.sleep(delay_between)

                    await asyncio.sleep(interval_hours * 3600)
            except asyncio.CancelledError:
                print("[GMAIL_FETCH] Background fetch loop cancelled")
                return

        bg_task = asyncio.create_task(_gmail_fetch_loop())

    yield
    print("[INFO] Shutting down RIVA Backend...")
    if bg_task:
        bg_task.cancel()

# Create FastAPI app
app = FastAPI(
    title="RIVA API",
    description="Voice-first AI Personal Assistant API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routes ---

# Include routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(stream_router)
app.include_router(finance_router)
app.include_router(calendar_router)
app.include_router(todo_router)
app.include_router(gemini_live_router)
app.include_router(gmail_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "RIVA API",
        "version": "1.0.0"
    }


@app.get("/home")
async def home():
    """Home endpoint."""
    return {"message": "Welcome Home! You are logged in."}


# --- Server Entry Point ---

if __name__ == "__main__":
    import uvicorn
    print("[INFO] Starting RIVA Backend Server...")
    print("[INFO] Server: http://0.0.0.0:8000")
    print("[INFO] API Docs: http://0.0.0.0:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)