"""
Design Review Environment — FastAPI Application

Creates the OpenEnv-compatible FastAPI server with:
  - WebSocket-based environment interaction
  - Health check endpoint
  - Environment info/capabilities endpoint
  - CORS middleware for HF Spaces deployment
"""

import os
import sys

# Ensure the parent package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from openenv.core.env_server import create_web_interface_app
except ImportError:
    create_web_interface_app = None

from models import ReviewAction, ReviewObservation
from server.environment import DesignReviewEnvironment

# ── Create App ───────────────────────────────────────────────────────────

enable_web = os.getenv("ENABLE_WEB_INTERFACE", "true").lower() == "true"

if create_web_interface_app and enable_web:
    app = create_web_interface_app(DesignReviewEnvironment, ReviewAction, ReviewObservation)
else:
    app = FastAPI(
        title="Design Review Environment",
        description="AI-Driven Engineering Design Review RL Environment",
        version="2.0.0",
    )

# ── CORS ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health & Info Endpoints ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "environment": "design_review_env", "version": "2.0.0"}


@app.get("/info")
async def info():
    return {
        "name": "design_review_env",
        "version": "2.0.0",
        "description": "AI-Driven Engineering Design Review — an agentic RL environment where AI acts as a senior design reviewer across 4 engineering domains.",
        "domains": ["bridge_truss", "pressure_vessel", "gear_assembly", "building_frame"],
        "difficulties": ["easy", "medium", "hard"],
        "action_types": ["inspect", "flag_issue", "request_analysis", "compare_standard", "request_info", "approve", "reject"],
        "scoring_dimensions": ["detection_precision", "detection_recall", "severity_accuracy", "efficiency", "reasoning_quality", "ethical_safety"],
        "applicable_standards": ["AISC 360-22", "ASME BPVC VIII-1", "AGMA 2001-D04", "ASCE 7-22", "AWS D1.1", "ISO 6336"],
        "openenv_api": ["reset()", "step(action)", "state()"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
