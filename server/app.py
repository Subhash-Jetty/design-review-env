"""
Design Review Environment — FastAPI Application

Creates the OpenEnv-compatible FastAPI server with:
  - REST API endpoints for environment interaction
  - Static file serving for the web dashboard
  - Health check and environment info endpoints
  - Expert agent step-through API
  - CORS middleware for HF Spaces deployment
"""

import os
import sys
import json

# Ensure the parent package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

try:
    from openenv.core.env_server import create_web_interface_app
except ImportError:
    create_web_interface_app = None

from models import ReviewAction, ReviewObservation, ReviewState
from server.environment import DesignReviewEnvironment

# ── Create App ───────────────────────────────────────────────────────────

app = FastAPI(
    title="Design Review Environment",
    description="AI-Driven Engineering Design Review RL Environment",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Environment Instance ─────────────────────────────────────────

_env: Optional[DesignReviewEnvironment] = None
_last_obs: Optional[dict] = None
_demo_state: dict = {
    "phase": None,
    "step_index": 0,
    "components_to_inspect": [],
    "components_to_analyze": [],
    "failed_analyses": [],
    "issues_found": [],
    "is_running": False,
}

# ── Expert Agent Heuristics ─────────────────────────────────────────────

ANALYSIS_MAP = {
    "chord": "stress", "member": "buckling", "beam": "deflection",
    "column": "buckling", "brace": "buckling", "shell": "stress",
    "vessel": "stress", "nozzle": "stress", "gear": "stress",
    "pinion": "stress", "connection": "weld_capacity",
    "flange": "bolt_capacity", "support": "weld_capacity",
}

ISSUE_HEURISTICS = {
    "chord": ("structural", "major", "AISC 360-22 Ch. F"),
    "member": ("structural", "major", "AISC 360-22 Ch. E"),
    "beam": ("safety", "critical", "AISC 360-22 Ch. L"),
    "column": ("structural", "critical", "AISC 360-22 Ch. E"),
    "brace": ("material", "minor", "AISC 341-22"),
    "shell": ("structural", "critical", "ASME BPVC VIII-1 UG-27"),
    "vessel": ("structural", "critical", "ASME BPVC VIII-1 UG-27"),
    "nozzle": ("safety", "critical", "ASME BPVC VIII-1 UG-37"),
    "gear": ("structural", "major", "AGMA 2001-D04 Sec. 7"),
    "pinion": ("material", "critical", "AGMA 2001-D04 Table 3"),
    "connection": ("safety", "major", "AISC 360-22 Ch. J"),
    "shaft": ("safety", "critical", "ASME B106.1M"),
}


# ── Request/Response Models ─────────────────────────────────────────────

class ResetRequest(BaseModel):
    domain: str = "bridge_truss"
    difficulty: str = "medium"
    seed: Optional[int] = None

class StepRequest(BaseModel):
    action_type: str = "inspect"
    component_id: str = ""
    issue_type: str = "none"
    severity: str = "none"
    justification: str = ""
    standard_reference: str = ""
    analysis_type: str = ""
    parameter_name: str = ""
    parameter_value: float = 0.0
    standard_code: str = ""


# ── Helper: serialize observation ────────────────────────────────────────

def _obs_to_dict(obs) -> dict:
    """Convert observation to a JSON-safe dict."""
    if hasattr(obs, 'model_dump'):
        return obs.model_dump()
    elif hasattr(obs, 'dict'):
        return obs.dict()
    elif isinstance(obs, dict):
        return obs
    else:
        return {k: getattr(obs, k, None) for k in dir(obs) if not k.startswith('_')}

def _state_to_dict(state) -> dict:
    """Convert state to a JSON-safe dict."""
    if hasattr(state, 'model_dump'):
        return state.model_dump()
    elif hasattr(state, 'dict'):
        return state.dict()
    elif isinstance(state, dict):
        return state
    else:
        return {k: getattr(state, k, None) for k in dir(state) if not k.startswith('_')}

def _schema_to_dict(model) -> dict:
    """Convert a Pydantic model class to a JSON schema payload."""
    if hasattr(model, 'model_json_schema'):
        return model.model_json_schema()
    if hasattr(model, 'schema'):
        return model.schema()
    return {}

# ── API Endpoints ────────────────────────────────────────────────────────

@app.post("/api/reset")
async def api_reset(req: ResetRequest):
    """Reset the environment with a new design."""
    global _env, _last_obs, _demo_state
    import random

    seed = req.seed or random.randint(1, 99999)
    _env = DesignReviewEnvironment(domain=req.domain, difficulty=req.difficulty, seed=seed)
    obs = _env.reset(seed=seed, domain=req.domain, difficulty=req.difficulty)

    _last_obs = _obs_to_dict(obs)

    # Reset demo state
    _demo_state = {
        "phase": None, "step_index": 0,
        "components_to_inspect": [], "components_to_analyze": [],
        "failed_analyses": [], "issues_found": [], "is_running": False,
    }

    # Include components info for the UI
    components_detail = {}
    for cid, comp in _env._components.items():
        components_detail[cid] = comp

    return {
        "observation": _last_obs,
        "components": components_detail,
        "flaws_count": _env._state.total_flaws_planted,
        "state": _state_to_dict(_env.state),
    }


@app.post("/api/step")
async def api_step(req: StepRequest):
    """Take a step in the environment."""
    global _env, _last_obs
    if _env is None:
        return JSONResponse(status_code=400, content={"error": "Environment not initialized. Call /api/reset first."})

    action = ReviewAction(
        action_type=req.action_type,
        component_id=req.component_id,
        issue_type=req.issue_type,
        severity=req.severity,
        justification=req.justification,
        standard_reference=req.standard_reference,
        analysis_type=req.analysis_type,
        parameter_name=req.parameter_name,
        parameter_value=req.parameter_value,
        standard_code=req.standard_code,
    )

    result = _env.step(action)

    obs = result.observation
    if hasattr(obs, 'model_dump'):
        obs_dict = obs.model_dump()
    elif hasattr(obs, 'dict'):
        obs_dict = obs.dict()
    elif isinstance(obs, dict):
        obs_dict = obs
    else:
        obs_dict = _obs_to_dict(obs)

    _last_obs = obs_dict

    return {
        "observation": obs_dict,
        "reward": result.reward,
        "done": result.done,
        "state": _state_to_dict(_env.state),
    }


@app.get("/api/state")
async def api_state():
    """Get current environment state."""
    global _env
    if _env is None:
        return JSONResponse(status_code=400, content={"error": "Environment not initialized."})
    return {
        "state": _state_to_dict(_env.state),
        "last_observation": _last_obs,
    }


@app.post("/reset")
async def reset(req: ResetRequest):
    """Reset the environment using the OpenEnv simulation contract."""
    return await api_reset(req)


@app.post("/step")
async def step(req: StepRequest):
    """Take a step in the environment using the OpenEnv simulation contract."""
    return await api_step(req)


@app.get("/state")
async def state():
    """Get the current OpenEnv state snapshot."""
    return await api_state()


@app.get("/metadata")
async def metadata():
    """Return OpenEnv environment metadata for runtime discovery."""
    return {
        "name": "design_review_env",
        "version": "2.0.0",
        "description": "AI-Driven Engineering Design Review — a multi-domain OpenEnv environment for engineering safety review.",
        "domains": ["bridge_truss", "pressure_vessel", "gear_assembly", "building_frame"],
        "difficulties": ["easy", "medium", "hard"],
    }


@app.get("/schema")
async def schema():
    """Return OpenEnv Action, Observation, and State schemas."""
    return {
        "action": _schema_to_dict(ReviewAction),
        "observation": _schema_to_dict(ReviewObservation),
        "state": _schema_to_dict(ReviewState),
    }


@app.post("/mcp")
async def mcp(payload: Dict[str, Any]):
    """Minimal JSON-RPC endpoint for OpenEnv runtime interoperability."""
    response = {"jsonrpc": "2.0", "result": {"status": "ready"}}
    if payload.get("id") is not None:
        response["id"] = payload.get("id")
    if payload.get("method") is not None:
        response["result"]["method"] = payload.get("method")
    return response


@app.post("/api/demo/start")
async def api_demo_start(req: ResetRequest):
    """Start an expert agent demo by resetting the environment."""
    global _env, _last_obs, _demo_state
    import random

    seed = req.seed or random.randint(1, 99999)
    _env = DesignReviewEnvironment(domain=req.domain, difficulty=req.difficulty, seed=seed)
    obs = _env.reset(seed=seed, domain=req.domain, difficulty=req.difficulty)
    _last_obs = _obs_to_dict(obs)

    # Prepare expert agent plan
    components_list = list(_env._components.keys())
    _demo_state = {
        "phase": "inspect",
        "step_index": 0,
        "components_to_inspect": list(components_list),
        "components_to_analyze": [],
        "failed_analyses": [],
        "issues_found": [],
        "flagged_comps": [],
        "is_running": True,
        "total_planned_steps": len(components_list) * 2 + 5,  # rough estimate
    }

    # Determine which components need analysis
    for cid in components_list:
        comp = _env._components.get(cid, {})
        comp_type = comp.get("component_type", "")
        if comp_type in ANALYSIS_MAP:
            _demo_state["components_to_analyze"].append((cid, ANALYSIS_MAP[comp_type]))

    components_detail = {}
    for cid, comp in _env._components.items():
        components_detail[cid] = comp

    return {
        "observation": _last_obs,
        "components": components_detail,
        "demo_state": {
            "phase": _demo_state["phase"],
            "total_components": len(components_list),
            "total_analyses": len(_demo_state["components_to_analyze"]),
        },
        "state": _state_to_dict(_env.state),
    }


@app.post("/api/demo/next")
async def api_demo_next():
    """Execute the next expert agent step."""
    global _env, _last_obs, _demo_state

    if _env is None or not _demo_state.get("is_running"):
        return JSONResponse(status_code=400, content={"error": "Demo not started. Call /api/demo/start first."})

    if _env.state.is_done:
        _demo_state["is_running"] = False
        return {
            "action": None,
            "observation": _last_obs,
            "reward": 0,
            "done": True,
            "phase": "complete",
            "agent_reasoning": "Episode has already ended.",
            "state": _state_to_dict(_env.state),
        }

    phase = _demo_state["phase"]
    action_data = None
    reasoning = ""

    # ── Phase 1: Inspect ──
    if phase == "inspect":
        idx = _demo_state["step_index"]
        comps = _demo_state["components_to_inspect"]

        if idx < len(comps):
            cid = comps[idx]
            comp = _env._components.get(cid, {})
            action_data = {"action_type": "inspect", "component_id": cid}
            reasoning = f"Phase 1 — Systematic Inspection: Examining {comp.get('name', cid)} to understand its parameters, material, and loading conditions."
            _demo_state["step_index"] = idx + 1
        else:
            # Move to analysis phase
            _demo_state["phase"] = "analyze"
            _demo_state["step_index"] = 0
            return await api_demo_next()

    # ── Phase 2: Analysis ──
    elif phase == "analyze":
        idx = _demo_state["step_index"]
        analyses = _demo_state["components_to_analyze"]

        if idx < len(analyses):
            cid, atype = analyses[idx]
            comp = _env._components.get(cid, {})
            action_data = {
                "action_type": "request_analysis",
                "component_id": cid,
                "analysis_type": atype,
            }
            reasoning = f"Phase 2 — Physics Analysis: Running {atype} analysis on {comp.get('name', cid)} to verify structural adequacy."
            _demo_state["step_index"] = idx + 1
        else:
            _demo_state["phase"] = "flag"
            _demo_state["step_index"] = 0
            return await api_demo_next()

    # ── Phase 3: Flag Issues ──
    elif phase == "flag":
        # First: flag from failed analyses
        idx = _demo_state["step_index"]
        failed = _demo_state["failed_analyses"]
        flagged = _demo_state.get("flagged_comps", [])

        if idx < len(failed):
            cid, comp_type, atype, analysis = failed[idx]
            issue_type, severity, standard = ISSUE_HEURISTICS.get(comp_type, ("structural", "major", "N/A"))
            sf = analysis.get("safety_factor", "N/A")
            action_data = {
                "action_type": "flag_issue",
                "component_id": cid,
                "issue_type": issue_type,
                "severity": severity,
                "justification": f"{atype} analysis shows safety factor of {sf} which is below the minimum required 1.5. Component parameters are non-compliant.",
                "standard_reference": standard,
            }
            reasoning = f"Phase 3 — Issue Flagging: {atype} analysis revealed SF={sf} (below 1.5) on {cid}. Flagging as {severity} {issue_type} issue per {standard}."
            _demo_state["step_index"] = idx + 1
            _demo_state.get("flagged_comps", []).append(cid)
        else:
            # Try qualitative heuristics
            found_qual = False
            for cid in _demo_state["components_to_inspect"]:
                if _env.state.is_done or cid in _demo_state.get("flagged_comps", []):
                    continue
                comp = _env._components.get(cid, {})
                comp_type = comp.get("component_type", "")

                flaw_indicators = []
                if comp.get("weld_size_mm", 99) <= 3:
                    flaw_indicators.append(("safety", "critical", "Undersized weld detected", "AISC 360-22 Table J2.4"))
                if comp.get("flange_thickness_mm", 99) <= 6:
                    flaw_indicators.append(("structural", "major", "Critically thin flange", "AISC 360-22 Section F2"))
                if comp.get("num_bolts", 99) <= 3:
                    flaw_indicators.append(("safety", "major", "Insufficient bolt count", "AISC 360-22 Ch. J"))
                if comp.get("hardness_hrc", 99) < 40 and comp_type in ("gear", "pinion"):
                    flaw_indicators.append(("material", "critical", "Surface hardness below minimum", "AGMA 2001-D04"))

                if flaw_indicators:
                    it, sv, desc, std = flaw_indicators[0]
                    action_data = {
                        "action_type": "flag_issue",
                        "component_id": cid,
                        "issue_type": it,
                        "severity": sv,
                        "justification": f"{desc}: Component parameters suggest non-compliance with {std}.",
                        "standard_reference": std,
                    }
                    reasoning = f"Phase 3 — Qualitative Check: {desc} detected on {cid}. Flagging per {std}."
                    _demo_state.get("flagged_comps", []).append(cid)
                    found_qual = True
                    break

            if not found_qual:
                _demo_state["phase"] = "decide"
                return await api_demo_next()

    # ── Phase 4: Decision ──
    elif phase == "decide":
        state = _env.state
        if state.flaws_correctly_found > 0:
            action_data = {"action_type": "reject"}
            reasoning = f"Phase 4 — Final Decision: {state.flaws_correctly_found} flaw(s) identified. Design is REJECTED for safety reasons."
        else:
            action_data = {"action_type": "approve"}
            reasoning = "Phase 4 — Final Decision: No flaws conclusively identified. Design APPROVED."

    if action_data is None:
        _demo_state["is_running"] = False
        return {
            "action": None, "observation": _last_obs,
            "reward": 0, "done": True, "phase": "complete",
            "agent_reasoning": "Expert agent has completed all phases.",
            "state": _state_to_dict(_env.state),
        }

    # Execute the action
    action = ReviewAction(**action_data)
    result = _env.step(action)

    obs = result.observation
    if hasattr(obs, 'model_dump'):
        obs_dict = obs.model_dump()
    elif hasattr(obs, 'dict'):
        obs_dict = obs.dict()
    elif isinstance(obs, dict):
        obs_dict = obs
    else:
        obs_dict = _obs_to_dict(obs)

    _last_obs = obs_dict

    # Track failed analyses for flag phase
    if action_data.get("action_type") == "request_analysis":
        analysis = obs_dict.get("analysis_results", {})
        if analysis and analysis.get("status") in ("FAIL", "MARGINAL"):
            cid = action_data["component_id"]
            comp = _env._components.get(cid, {})
            comp_type = comp.get("component_type", "")
            atype = action_data.get("analysis_type", "stress")
            _demo_state["failed_analyses"].append((cid, comp_type, atype, analysis))

    if action_data.get("action_type") == "flag_issue" and "CORRECT" in obs_dict.get("step_feedback", ""):
        _demo_state["issues_found"].append(action_data["component_id"])

    if result.done:
        _demo_state["is_running"] = False
        _demo_state["phase"] = "complete"

    return {
        "action": action_data,
        "observation": obs_dict,
        "reward": result.reward,
        "done": result.done,
        "phase": _demo_state["phase"],
        "agent_reasoning": reasoning,
        "state": _state_to_dict(_env.state),
    }


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


# ── Static Files & Dashboard ────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Dashboard not found. Place index.html in static/"}


# Mount static files AFTER specific routes
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def main() -> None:
    """Run the FastAPI server via Uvicorn."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
