---
title: Design Review Environment
emoji: 🏗️
colorFrom: blue
colorTo: cyan
sdk: docker
sdk_version: latest
python_version: "3.10"
app_file: server/app.py
pinned: false
---

# AI-Driven Engineering Design Review Environment

**OpenEnv-compatible multi-domain RL environment for training design review agents**

Interactive web interface powered by FastAPI. This Space is auto-deployed from [GitHub](https://github.com/Subhash-Jetty/design-review-env).

## 🎮 Features

- **4 Engineering Domains**: Bridge Truss, Pressure Vessel, Gear Assembly, Building Frame
- **3 Difficulty Levels**: Easy, Medium, Hard  
- **7 Action Types**: Inspect, flag issues, request analysis, compare standards, approve, reject
- **Multi-Dimensional Scoring**: Precision, recall, severity accuracy, efficiency, reasoning, ethical safety
- **Reproducible Design Generation**: Seed-based for consistent benchmarking

## 🚀 Quick Start

### 1. Reset Environment
```bash
curl -X POST https://this-space.hf.space/api/reset \
  -H "Content-Type: application/json" \
  -d '{"domain": "bridge_truss", "difficulty": "medium", "seed": 42}'
```

### 2. Inspect Components
```bash
curl -X POST https://this-space.hf.space/api/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "inspect", "component_id": "member_1"}'
```

### 3. Flag Issues
```bash
curl -X POST https://this-space.hf.space/api/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "flag_issue",
    "component_id": "member_1",
    "issue_type": "structural",
    "severity": "major",
    "justification": "Cross-section undersized",
    "standard_reference": "AISC 360-22 Chapter F"
  }'
```

## 📊 Scoring System

| Dimension | Weight | Metric |
|---|---|---|
| Detection Precision | 25% | TP / (TP + FP) |
| Detection Recall | 25% | TP / (TP + FN) |
| Severity Accuracy | 15% | Correct classifications |
| Efficiency | 10% | Flaws per step |
| Reasoning Quality | 10% | Standards & justifications |
| Ethical Safety | 15% | Penalty for missed criticals |

## 🔌 API Endpoints

### REST API
- `POST /api/reset` — Initialize environment
- `POST /api/step` — Execute action
- `GET /api/state` — Get state snapshot

### OpenEnv Standard
- `GET /health` — Health check
- `GET /metadata` — Environment metadata
- `GET /schema` — Action/Observation/State schemas
- `GET /openapi.json` — Full API spec

## 📚 Documentation

- **Full README**: [GitHub](https://github.com/Subhash-Jetty/design-review-env/blob/main/README.md)
- **OpenEnv Compliance**: [GitHub](https://github.com/Subhash-Jetty/design-review-env/blob/main/OPENENV_COMPLIANCE.md)
- **Setup Guide**: [GitHub](https://github.com/Subhash-Jetty/design-review-env/blob/main/HF_SPACES_SETUP.md)

## 🔗 Links

- **GitHub Repository**: https://github.com/Subhash-Jetty/design-review-env
- **OpenEnv Framework**: https://github.com/meta-pytorch/OpenEnv
- **Meta Hackathon 2026**: https://sites.research.facebook/mlcommons-openenv-hackathon-2026/

## 📜 License

BSD-3-Clause

---

**Built for Meta OpenEnv Hackathon 2026** in partnership with Scaler, Hugging Face, and PyTorch.
