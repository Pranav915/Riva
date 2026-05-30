"""
RIVA Backend - Main Application
Personal AI Secretary for productivity and finance.
"""
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from routers import auth_router, user_router, finance_router, calendar_router, todo_router, gemini_live_router

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] Starting RIVA Backend...")
    print("[OK] RIVA Backend ready")
    yield
    print("[INFO] Shutting down RIVA Backend...")

# Create FastAPI app
app = FastAPI(
    title="RIVA API",
    description="Voice-first AI Personal Assistant API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
cors_origins = os.getenv("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if cors_origins == "*" else [o.strip() for o in cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routes ---

# Include routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(finance_router)
app.include_router(calendar_router)
app.include_router(todo_router)
app.include_router(gemini_live_router)


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
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print("[INFO] Starting RIVA Backend Server...")
    print(f"[INFO] Server: http://{host}:{port}")
    print(f"[INFO] API Docs: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)