# Design Review Environment — HF Spaces Edition

**Interactive Web Interface for AI-Driven Engineering Design Review**

This is a **Hugging Face Spaces** deployment of the design review environment from the Meta OpenEnv Hackathon 2026. 

## 🎮 Features

- **4 Engineering Domains**: Bridge Truss, Pressure Vessel, Gear Assembly, Building Frame
- **3 Difficulty Levels**: Easy, Medium, Hard
- **7 Action Types**: Inspect, flag issues, request analysis, compare standards, approve, reject
- **Multi-Dimensional Scoring**: Detection precision, recall, severity accuracy, efficiency, reasoning quality, ethical safety
- **Reproducible Episodes**: Seed-based design generation for consistent benchmarking

## 🚀 Quick Start

### 1. Reset Environment
Click **"Reset"** or send:
```bash
curl -X POST https://this-space.hf.space/api/reset \
  -H "Content-Type: application/json" \
  -d '{"domain": "bridge_truss", "difficulty": "medium", "seed": 42}'
```

### 2. Inspect Components
Inspect a design component to understand its parameters.

### 3. Request Analysis
Request structural analysis (stress, buckling, deflection) on suspicious components.

### 4. Flag Issues
Flag identified safety or compliance violations with references to standards.

### 5. Make Decision
Approve or reject the design based on your findings.

## 📊 Scoring Dimensions

| Dimension | Weight | Metric |
|---|---|---|
| Detection Precision | 20% | Correct detections / all detections |
| Detection Recall | 20% | Flaws found / total flaws |
| Severity Accuracy | 15% | Matches to true severity levels |
| Efficiency | 10% | Flaws found per step |
| Reasoning Quality | 10% | Standards referenced, justifications |
| Ethical Safety | 15% | Penalty for missing critical flaws |

## 🔌 API Endpoints

### REST API
- `POST /api/reset` — Initialize environment
- `POST /api/step` — Execute action
- `GET /api/state` — Get state snapshot
- `GET /api/info` — Environment info

### OpenEnv Standard
- `POST /reset` — Reset environment
- `POST /step` — Step environment
- `GET /state` — State snapshot
- `GET /metadata` — Metadata
- `GET /schema` — Schemas
- `GET /health` — Health check

### OpenAPI Documentation
- **Interactive Docs**: `/docs`
- **OpenAPI JSON**: `/openapi.json`

## 📝 Example Workflow

```python
import requests

BASE_URL = "https://this-space.hf.space"

# Reset
resp = requests.post(f"{BASE_URL}/api/reset", json={
    "domain": "bridge_truss",
    "difficulty": "medium",
    "seed": 42
})
obs = resp.json()["observation"]

# Inspect
resp = requests.post(f"{BASE_URL}/api/step", json={
    "action_type": "inspect",
    "component_id": "member_1"
})
print(resp.json()["observation"]["step_feedback"])

# Flag Issue
resp = requests.post(f"{BASE_URL}/api/step", json={
    "action_type": "flag_issue",
    "component_id": "member_1",
    "issue_type": "structural",
    "severity": "major",
    "justification": "Cross-section undersized for applied loading",
    "standard_reference": "AISC 360-22 Chapter F"
})

# Decide
resp = requests.post(f"{BASE_URL}/api/step", json={
    "action_type": "reject"
})
state = resp.json()["state"]
print(f"Final Score: {state['composite_score']}")
```

## 🧩 Project Structure

- **`server/app.py`** — FastAPI web interface
- **`server/environment.py`** — Core environment logic
- **`models.py`** — Pydantic action/observation/state models
- **`static/`** — Web dashboard UI
- **`baseline_inference.py`** — LLM-powered baseline agent

## 📚 Documentation

- **[Full README](https://github.com/Subhash-Jetty/design-review-env/blob/main/README.md)** — Complete project overview
- **[OpenEnv Compliance](https://github.com/Subhash-Jetty/design-review-env/blob/main/OPENENV_COMPLIANCE.md)** — Compliance checklist
- **[Deployment Guide](https://github.com/Subhash-Jetty/design-review-env/blob/main/OPENENV_DEPLOYMENT_GUIDE.md)** — Deployment instructions

## 🔗 Links

- **GitHub**: https://github.com/Subhash-Jetty/design-review-env
- **OpenEnv**: https://github.com/meta-pytorch/OpenEnv
- **PyTorch**: https://pytorch.org

## 📜 License

BSD-3-Clause — See LICENSE file in repository

---

**Built for Meta OpenEnv Hackathon 2026** in partnership with Scaler, Hugging Face, and PyTorch.
