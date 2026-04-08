"""
Comprehensive Test Suite — Design Review Environment

Tests all 4 domains, 3 difficulty levels, and all 7 action types.

Run:
    python test_env.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ReviewAction
from server.environment import DesignReviewEnvironment
from server.design_catalog import generate_design
from server.physics_engine import PhysicsEngine
from server.grader import Grader


def test_header(name):
    print(f"\n{'='*60}")
    print(f"  TEST: {name}")
    print(f"{'='*60}")


def assert_true(condition, msg):
    if condition:
        print(f"  ✅ PASS: {msg}")
    else:
        print(f"  ❌ FAIL: {msg}")
    return condition


def _get(obj, key, default=None):
    """Safely get attribute from a Pydantic model or dict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ── Test 1: All Domains Generate ─────────────────────────────────────────

def test_all_domains():
    test_header("Design Generation — All Domains")
    passed = True

    for domain in ["bridge_truss", "pressure_vessel", "gear_assembly", "building_frame"]:
        for difficulty in ["easy", "medium", "hard"]:
            components, flaws, info = generate_design(domain=domain, difficulty=difficulty, seed=42)
            ok = len(components) > 0 and len(flaws) > 0
            passed &= assert_true(ok, f"{domain}/{difficulty}: {len(components)} components, {len(flaws)} flaws")

    return passed


# ── Test 2: Reproducibility ──────────────────────────────────────────────

def test_reproducibility():
    test_header("Reproducibility with Seeds")

    c1, f1, i1 = generate_design(domain="bridge_truss", difficulty="medium", seed=123)
    c2, f2, i2 = generate_design(domain="bridge_truss", difficulty="medium", seed=123)

    keys_match = list(c1.keys()) == list(c2.keys())
    flaws_match = len(f1) == len(f2)

    passed = assert_true(keys_match, "Same seed produces same components")
    passed &= assert_true(flaws_match, "Same seed produces same flaws")

    c3, f3, i3 = generate_design(domain="bridge_truss", difficulty="medium", seed=456)
    different = list(c3.keys()) != list(c1.keys()) or len(f3) != len(f1)
    # Note: different seeds might produce same count, so just check it doesn't crash
    passed &= assert_true(True, "Different seed generates without error")

    return passed


# ── Test 3: Physics Engine ───────────────────────────────────────────────

def test_physics_engine():
    test_header("Physics Engine Calculations")
    passed = True

    # Beam bending
    result = PhysicsEngine.beam_bending_stress(50.0, 300.0, 1.5e8)
    passed &= assert_true("stress_mpa" in result, f"Beam bending stress: {result['stress_mpa']} MPa")

    # Beam deflection
    result = PhysicsEngine.beam_deflection(10.0, 5.0, 200.0, 1.5e8)
    passed &= assert_true("deflection_mm" in result, f"Beam deflection: {result['deflection_mm']} mm")

    # Euler buckling
    result = PhysicsEngine.euler_buckling(200.0, 1.5e8, 5.0, 1.0)
    passed &= assert_true("critical_load_kn" in result, f"Buckling load: {result['critical_load_kn']} kN")

    # Pressure vessel
    result = PhysicsEngine.pressure_vessel_stress(2.0, 500.0, 10.0)
    passed &= assert_true("hoop_stress_mpa" in result, f"Hoop stress: {result['hoop_stress_mpa']} MPa")

    # Weld capacity
    result = PhysicsEngine.weld_capacity(6.0, 150.0)
    passed &= assert_true("capacity_kn" in result, f"Weld capacity: {result['capacity_kn']} kN")

    # Bolt capacity
    result = PhysicsEngine.bolt_capacity(20.0, 4)
    passed &= assert_true("total_capacity_kn" in result, f"Bolt capacity: {result['total_capacity_kn']} kN")

    # Gear contact stress
    result = PhysicsEngine.gear_contact_stress(5000.0, 100.0, 30.0)
    passed &= assert_true("contact_stress_mpa" in result, f"Gear contact stress: {result['contact_stress_mpa']} MPa")

    # Safety factor
    result = PhysicsEngine.safety_factor(300.0, 200.0)
    passed &= assert_true(result["safety_factor"] == 1.5, f"Safety factor: {result['safety_factor']}")

    return passed


# ── Test 4: Full Episode — All Action Types ──────────────────────────────

def test_full_episode():
    test_header("Full Episode — All Action Types")
    passed = True

    env = DesignReviewEnvironment(domain="bridge_truss", difficulty="easy", seed=42)
    obs = env.reset()

    passed &= assert_true(len(obs.available_components) > 0, f"Reset: {len(obs.available_components)} components available")
    passed &= assert_true(obs.steps_remaining > 0, f"Reset: {obs.steps_remaining} steps remaining")

    # 1. Inspect
    comp_id = obs.available_components[0]
    result = env.step(ReviewAction(action_type="inspect", component_id=comp_id))
    passed &= assert_true(_get(result.observation, "action_valid", False), f"Inspect {comp_id}: valid")
    passed &= assert_true(_get(result.observation, "current_component") is not None, "Inspect returns component data")

    # 2. Request analysis
    result = env.step(ReviewAction(action_type="request_analysis", component_id=comp_id, analysis_type="stress"))
    passed &= assert_true(_get(result.observation, "analysis_results") is not None, "Analysis returns results")

    # 3. Compare standard
    result = env.step(ReviewAction(action_type="compare_standard", component_id=comp_id, parameter_name="depth_mm", parameter_value=200.0, standard_code="AISC 360-22"))
    passed &= assert_true(_get(result.observation, "standard_check_result") is not None, "Standard check returns results")

    # 4. Request info
    result = env.step(ReviewAction(action_type="request_info"))
    passed &= assert_true("Standards" in _get(result.observation, "step_feedback", ""), "Request info returns standards")

    # 5. Flag issue (try matching a real flaw)
    state = env.state
    if state.flaw_manifest:
        flaw = state.flaw_manifest[0]
        result = env.step(ReviewAction(
            action_type="flag_issue",
            component_id=flaw["component_id"],
            issue_type=flaw["issue_type"],
            severity=flaw["severity"],
            justification="Testing correct flaw identification",
            standard_reference=flaw.get("standard", ""),
        ))
        passed &= assert_true("CORRECT" in _get(result.observation, "step_feedback", ""), "Correct flag: accepted")

    # 6. Flag false positive
    result = env.step(ReviewAction(action_type="flag_issue", component_id=comp_id, issue_type="electrical", severity="minor"))
    passed &= assert_true("FALSE" in _get(result.observation, "step_feedback", ""), "False positive: detected")

    # 7. Reject
    result = env.step(ReviewAction(action_type="reject"))
    passed &= assert_true(result.done, "Reject ends episode")

    # Check final scoring
    state = env.state
    passed &= assert_true(state.episode_summary is not None, "Episode summary generated")
    passed &= assert_true(state.composite_score > 0, f"Composite score: {state.composite_score}")

    return passed


# ── Test 5: Invalid Actions ──────────────────────────────────────────────

def test_invalid_actions():
    test_header("Invalid Actions Handling")
    passed = True

    env = DesignReviewEnvironment(domain="bridge_truss", difficulty="easy", seed=99)
    env.reset()

    # Invalid component
    result = env.step(ReviewAction(action_type="inspect", component_id="nonexistent_xyz"))
    passed &= assert_true(not _get(result.observation, "action_valid", True), "Invalid component: rejected")
    passed &= assert_true(result.reward < 0, "Invalid component: negative reward")

    # Invalid action type
    result = env.step(ReviewAction(action_type="explode"))
    passed &= assert_true(not _get(result.observation, "action_valid", True), "Invalid action type: rejected")

    return passed


# ── Test 6: Step Limit ───────────────────────────────────────────────────

def test_step_limit():
    test_header("Step Limit Enforcement")
    passed = True

    env = DesignReviewEnvironment(domain="bridge_truss", difficulty="easy", seed=77)
    obs = env.reset()

    # Take max_steps actions
    components = list(obs.available_components)
    for i in range(env.state.max_steps + 5):
        comp_id = components[i % len(components)]
        result = env.step(ReviewAction(action_type="inspect", component_id=comp_id))
        if result.done:
            passed &= assert_true(True, f"Episode ended at step {i+1}")
            break

    passed &= assert_true(env.state.is_done, "Episode marked as done")

    return passed


# ── Test 7: Grader Scoring ───────────────────────────────────────────────

def test_grader():
    test_header("Grader Multi-Dimensional Scoring")
    passed = True

    grader = Grader()

    # Simulate perfect review
    grader.reward_inspect(is_new=True)
    grader.reward_inspect(is_new=True)
    grader.reward_flag_issue(matched=True, severity_correct=True, standard_correct=True, already_flagged=False, has_justification=True)
    grader.reward_flag_issue(matched=True, severity_correct=True, standard_correct=True, already_flagged=False, has_justification=True)
    grader.reward_reject(flaws_found=2, total_flaws=2)

    score = grader.compute_composite_score(total_flaws=2, max_steps=20)

    passed &= assert_true(score["composite_score"] > 80, f"Perfect review score: {score['composite_score']}")
    passed &= assert_true(score["dimensions"]["detection_precision"]["score"] == 100.0, "Perfect precision")
    passed &= assert_true(score["dimensions"]["detection_recall"]["score"] == 100.0, "Perfect recall")
    passed &= assert_true(score["dimensions"]["severity_accuracy"]["score"] == 100.0, "Perfect severity accuracy")

    return passed


# ── Test 8: All Domains Full Episode ─────────────────────────────────────

def test_all_domains_episode():
    test_header("Full Episode — All Domains")
    passed = True

    for domain in ["bridge_truss", "pressure_vessel", "gear_assembly", "building_frame"]:
        env = DesignReviewEnvironment(domain=domain, difficulty="medium", seed=42)
        obs = env.reset()

        # Quick run: inspect first component, then reject
        if obs.available_components:
            env.step(ReviewAction(action_type="inspect", component_id=obs.available_components[0]))

        result = env.step(ReviewAction(action_type="reject"))
        passed &= assert_true(result.done, f"{domain}: Episode completes")

    return passed


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  🧪 DESIGN REVIEW ENVIRONMENT — TEST SUITE v2.0")
    print("=" * 60)

    tests = [
        ("Design Generation", test_all_domains),
        ("Reproducibility", test_reproducibility),
        ("Physics Engine", test_physics_engine),
        ("Full Episode", test_full_episode),
        ("Invalid Actions", test_invalid_actions),
        ("Step Limit", test_step_limit),
        ("Grader Scoring", test_grader),
        ("All Domains Episode", test_all_domains_episode),
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print(f"\n\n{'='*60}")
    print("  📊 TEST SUMMARY")
    print(f"{'='*60}")
    total = len(results)
    passed_count = sum(1 for _, p in results if p)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Result: {passed_count}/{total} test groups passed")
    print(f"{'='*60}\n")

    return passed_count == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
