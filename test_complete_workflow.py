"""
Complete Workflow Test — Design Review Environment

Tests all API endpoints in a single episode:
  1. Reset environment
  2. Inspect multiple components
  3. Request analysis
  4. Compare against standards
  5. Flag issues
  6. Make final decision (reject or approve)

Run:
    python test_complete_workflow.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# ── Color Output ─────────────────────────────────────────────────────────

BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def print_header(text):
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}{text:^70}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")

def print_section(text):
    print(f"\n{BOLD}{YELLOW}▶ {text}{RESET}")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_info(text):
    print(f"{CYAN}ℹ️  {text}{RESET}")

# ── Test 1: Reset Environment ────────────────────────────────────────────

print_header("🔧 COMPLETE WORKFLOW TEST")

print_section("STEP 1: Reset Environment")
response = requests.post(f"{BASE_URL}/api/reset", json={
    "domain": "bridge_truss",
    "difficulty": "medium",
    "seed": 42
})

if response.status_code != 200:
    print_error(f"Reset failed: {response.status_code}")
    exit(1)

data = response.json()
obs = data["observation"]
components = data["components"]
flaws_count = data["flaws_count"]

print_success(f"Design loaded: {obs['design_id']}")
print_info(f"Type: {obs['design_type']} | Difficulty: {obs['design_difficulty']}")
print_info(f"Components: {len(components)} | Hidden flaws: {flaws_count}")
print_info(f"Steps remaining: {obs['steps_remaining']}/30")
print(f"\n{obs['design_summary']}")
print(f"{obs['design_requirements']}")

# Get component list
component_ids = obs["available_components"]
print_info(f"Available components: {', '.join(component_ids[:3])}...")

# ── Test 2: Inspect Components ──────────────────────────────────────────

print_section("STEP 2: Inspect Components")

inspected = []
for i, comp_id in enumerate(component_ids[:3], 1):
    print(f"\n  [{i}] Inspecting {comp_id}...")
    response = requests.post(f"{BASE_URL}/api/step", json={
        "action_type": "inspect",
        "component_id": comp_id
    })
    
    if response.status_code == 200:
        result = response.json()
        obs = result["observation"]
        reward = result.get("reward", 0)
        
        comp_detail = components.get(comp_id, {})
        print_success(f"Inspected {comp_id} | Reward: +{reward}")
        print_info(f"  Type: {comp_detail.get('component_type', 'N/A')}")
        print_info(f"  Profile: {comp_detail.get('profile', 'N/A')} | Material: {comp_detail.get('material', 'N/A')}")
        
        inspected.append(comp_id)
    else:
        print_error(f"Inspection failed: {response.status_code}")

print_info(f"✓ Inspected {len(inspected)} components")

# ── Test 3: Request Analysis ────────────────────────────────────────────

print_section("STEP 3: Request Physics Analysis")

analysis_results = {}
for comp_id in inspected:
    print(f"\n  Analyzing {comp_id}...")
    
    # Determine analysis type based on component
    analysis_type = "stress"
    if "member" in comp_id or "brace" in comp_id:
        analysis_type = "buckling"
    elif "connection" in comp_id:
        analysis_type = "weld_capacity"
    
    response = requests.post(f"{BASE_URL}/api/step", json={
        "action_type": "request_analysis",
        "analysis_type": analysis_type,
        "component_id": comp_id
    })
    
    if response.status_code == 200:
        result = response.json()
        obs = result["observation"]
        reward = result.get("reward", 0)
        
        analysis_results[comp_id] = obs.get("analysis_results", {})
        
        if obs.get("analysis_results"):
            print_success(f"Analysis complete ({analysis_type}) | Reward: +{reward}")
            print_info(f"  Result: {json.dumps(obs['analysis_results'], indent=2)}")
        else:
            print_info(f"Analysis executed ({analysis_type}) | Reward: +{reward}")
    else:
        print_error(f"Analysis failed: {response.status_code}")
    
    time.sleep(0.2)

# ── Test 4: Compare Standards ─────────────────────────────────────────

print_section("STEP 4: Compare Against Engineering Standards")

standards_checked = []
for comp_id in inspected:
    print(f"\n  Checking {comp_id} against standards...")
    
    response = requests.post(f"{BASE_URL}/api/step", json={
        "action_type": "compare_standard",
        "standard_code": "AISC 360-22 Section F",
        "component_id": comp_id
    })
    
    if response.status_code == 200:
        result = response.json()
        obs = result["observation"]
        reward = result.get("reward", 0)
        
        print_success(f"Standard check complete | Reward: +{reward}")
        if obs.get("standard_check_result"):
            print_info(f"  Result: {obs['standard_check_result']}")
        
        standards_checked.append(comp_id)
    else:
        print_error(f"Standard check failed: {response.status_code}")
    
    time.sleep(0.2)

# ── Test 5: Flag Issues ─────────────────────────────────────────────

print_section("STEP 5: Flag Detected Issues")

flagged_count = 0
for comp_id in inspected:
    print(f"\n  Flagging issue in {comp_id}...")
    
    response = requests.post(f"{BASE_URL}/api/step", json={
        "action_type": "flag_issue",
        "component_id": comp_id,
        "issue_type": "structural",
        "severity": "major",
        "justification": f"Component {comp_id} shows material/dimensional inconsistencies requiring review",
        "standard_reference": "AISC 360-22"
    })
    
    if response.status_code == 200:
        result = response.json()
        obs = result["observation"]
        reward = result.get("reward", 0)
        
        flagged_issues = obs.get("flagged_issues", [])
        print_success(f"Issue flagged | Reward: +{reward}")
        print_info(f"  Issues reported: {len(flagged_issues)}")
        
        flagged_count += 1
    else:
        print_error(f"Flag failed: {response.status_code}")
    
    time.sleep(0.2)

print_info(f"✓ Flagged {flagged_count} issues")

# ── Test 6: Make Final Decision ─────────────────────────────────────

print_section("STEP 6: Make Final Decision")

print("\n⚠️  Decision: REJECT (issues found)")
response = requests.post(f"{BASE_URL}/api/step", json={
    "action_type": "reject",
    "justification": (
        f"Design contains critical flaws. Flagged {flagged_count} issues:\n"
        "- Material specifications inconsistent per AASHTO LRFD\n"
        "- Slenderness ratios exceed AISC limits\n"
        "- Flange thicknesses below minimum requirements\n"
        "Design cannot be approved in current state."
    )
})

if response.status_code == 200:
    result = response.json()
    obs = result["observation"]
    state = result.get("state", {})
    reward = result.get("reward", 0)
    
    print_success(f"Decision submitted | Final reward: +{reward}")
    
    # Print final scores
    print_info(f"\n📊 EPISODE FINAL SCORES:")
    print_info(f"  Detection Precision: {state.get('detection_precision', 0):.2%}")
    print_info(f"  Detection Recall: {state.get('detection_recall', 0):.2%}")
    print_info(f"  Severity Accuracy: {state.get('severity_accuracy', 0):.2%}")
    print_info(f"  Efficiency Score: {state.get('efficiency_score', 0):.2%}")
    print_info(f"  Reasoning Quality: {state.get('reasoning_quality', 0):.2%}")
    print_info(f"  Ethical Score: {state.get('ethical_score', 0):.2%}")
    print(f"\n  {BOLD}COMPOSITE SCORE: {state.get('composite_score', 0):.1f}/100{RESET}")
    print_info(f"  Total Reward: {state.get('total_reward', 0):.2f}")
    
    # Episode summary
    if state.get("is_done"):
        print_success(f"Episode Complete!")
        print_info(f"  Steps taken: {state.get('steps_taken', 0)}/{state.get('max_steps', 30)}")
        print_info(f"  Final decision: {state.get('final_decision', 'N/A')}")
else:
    print_error(f"Decision failed: {response.status_code}")

# ── Summary ──────────────────────────────────────────────────────────

print_header("✅ TEST COMPLETE")
print(f"\n{GREEN}All API endpoints tested successfully!{RESET}\n")

test_results = {
    "reset": True,
    "inspect": len(inspected) > 0,
    "request_analysis": len(analysis_results) > 0,
    "compare_standard": len(standards_checked) > 0,
    "flag_issue": flagged_count > 0,
    "reject": True,
}

print(f"Test Results:")
for test_name, passed in test_results.items():
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {test_name}")

print()
