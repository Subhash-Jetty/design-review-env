"""
Expert Demo Agent — Design Review Environment

A rule-based expert agent that demonstrates the full capabilities
of the Design Review Environment. This agent:

  1. Inspects all available components systematically
  2. Requests physics analysis on structural components
  3. Flags issues with proper justification and standard references
  4. Makes an informed approve/reject decision

Run:
    python demo_agent.py [--domain bridge_truss] [--difficulty medium] [--seed 42]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ReviewAction
from server.environment import DesignReviewEnvironment


# ── Styling ──────────────────────────────────────────────────────────────

HEADER = "=" * 70
DIVIDER = "-" * 70
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def colorize(text, color):
    return f"{color}{text}{RESET}"


# ── Expert Heuristics ────────────────────────────────────────────────────

ANALYSIS_MAP = {
    "chord": "stress",
    "member": "buckling",
    "beam": "deflection",
    "column": "buckling",
    "brace": "buckling",
    "shell": "stress",
    "vessel": "stress",
    "nozzle": "stress",
    "gear": "stress",
    "pinion": "stress",
    "connection": "weld_capacity",
    "flange": "bolt_capacity",
    "support": "weld_capacity",
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


def run_expert_agent(domain="bridge_truss", difficulty="medium", seed=42):
    """Run the expert agent through a full episode."""
    print(f"\n{HEADER}")
    print(colorize("  🤖 EXPERT DESIGN REVIEW AGENT — DEMONSTRATION", BOLD))
    print(f"{HEADER}")
    print(f"  Domain:     {colorize(domain.replace('_', ' ').title(), CYAN)}")
    print(f"  Difficulty: {colorize(difficulty.upper(), YELLOW)}")
    print(f"  Seed:       {seed}")
    print(f"{HEADER}\n")

    env = DesignReviewEnvironment(domain=domain, difficulty=difficulty, seed=seed)
    obs = env.reset()

    print(colorize("📋 DESIGN BRIEFING", BOLD))
    print(f"  {obs.design_summary}")
    print(f"\n  Requirements: {obs.design_requirements}")
    print(f"  Components:   {len(obs.available_components)}")
    print(f"  Max Steps:    {obs.steps_remaining}")
    print(f"\n{DIVIDER}")

    step_num = 0
    issues_found = []
    failed_analyses = []

    # Phase 1: Inspect all components
    print(colorize("\n🔍 PHASE 1: Component Inspection", BOLD))
    print(DIVIDER)

    components_to_inspect = list(obs.available_components)
    for comp_id in components_to_inspect:
        step_num += 1
        action = ReviewAction(action_type="inspect", component_id=comp_id)
        result = env.step(action)
        obs_dict = result.observation

        comp = obs_dict.get("current_component", {})
        comp_name = comp.get("name", comp_id) if comp else comp_id
        comp_type = comp.get("component_type", "unknown") if comp else "unknown"

        print(f"\n  [{step_num}] Inspecting: {colorize(comp_name, CYAN)}")
        if comp:
            for k, v in comp.items():
                if k not in ("component_type", "name"):
                    print(f"       {k}: {v}")

        if result.done:
            break

    # Phase 2: Run physics analysis on structural components
    print(colorize("\n\n📊 PHASE 2: Physics Analysis", BOLD))
    print(DIVIDER)

    for comp_id in components_to_inspect:
        state = env.state
        comp = env._components.get(comp_id, {})
        comp_type = comp.get("component_type", "")
        analysis_type = ANALYSIS_MAP.get(comp_type, None)

        if analysis_type and not state.is_done:
            step_num += 1
            action = ReviewAction(
                action_type="request_analysis",
                component_id=comp_id,
                analysis_type=analysis_type,
            )
            result = env.step(action)
            obs_dict = result.observation
            analysis = obs_dict.get("analysis_results", {})

            if analysis:
                status = analysis.get("status", "N/A")
                sf = analysis.get("safety_factor", "N/A")
                color = RED if status == "FAIL" else (YELLOW if status == "MARGINAL" else GREEN)
                print(f"\n  [{step_num}] {analysis_type.upper()} on {comp_id}: {colorize(status, color)} (SF={sf})")

                if status in ("FAIL", "MARGINAL"):
                    failed_analyses.append((comp_id, comp_type, analysis_type, analysis))
            else:
                print(f"\n  [{step_num}] {analysis_type.upper()} on {comp_id}: No results")

            if result.done:
                break

    # Phase 3: Flag issues based on analysis + flaw manifest knowledge
    print(colorize("\n\n🚩 PHASE 3: Issue Flagging", BOLD))
    print(DIVIDER)

    # Flag issues found via analysis
    for comp_id, comp_type, atype, analysis in failed_analyses:
        state = env.state
        if state.is_done:
            break

        issue_type, severity, standard = ISSUE_HEURISTICS.get(comp_type, ("structural", "major", "N/A"))
        step_num += 1

        action = ReviewAction(
            action_type="flag_issue",
            component_id=comp_id,
            issue_type=issue_type,
            severity=severity,
            justification=f"{atype} analysis shows safety factor of {analysis.get('safety_factor', 'N/A')} which is below the minimum required 1.5. Component parameters are non-compliant.",
            standard_reference=standard,
        )
        result = env.step(action)
        obs_dict = result.observation

        matched = "🎯 CORRECT" if "CORRECT" in obs_dict.get("step_feedback", "") else "❌ FALSE POS"
        color = GREEN if "CORRECT" in matched else RED
        print(f"\n  [{step_num}] {colorize(matched, color)}: {issue_type}/{severity} on {comp_id}")
        print(f"       Standard: {standard}")

        if "CORRECT" in matched:
            issues_found.append(comp_id)

        if result.done:
            break

    # Also flag based on qualitative heuristics for components not caught by analysis
    for comp_id in components_to_inspect:
        state = env.state
        if state.is_done or comp_id in issues_found:
            continue

        comp = env._components.get(comp_id, {})
        comp_type = comp.get("component_type", "")

        # Check for common flaw indicators
        flaw_indicators = []
        if comp.get("weld_size_mm", 99) <= 3:
            flaw_indicators.append(("safety", "critical", "Undersized weld", "AISC 360-22 Table J2.4"))
        if comp.get("flange_thickness_mm", 99) <= 6:
            flaw_indicators.append(("structural", "major", "Thin flange", "AISC 360-22 Section F2"))
        if comp.get("num_bolts", 99) <= 3:
            flaw_indicators.append(("safety", "major", "Insufficient bolts", "AISC 360-22 Ch. J"))
        if comp.get("hardness_hrc", 99) < 40 and comp_type in ("gear", "pinion"):
            flaw_indicators.append(("material", "critical", "Low hardness", "AGMA 2001-D04"))

        for issue_type, severity, desc, standard in flaw_indicators:
            if state.is_done:
                break
            step_num += 1
            action = ReviewAction(
                action_type="flag_issue",
                component_id=comp_id,
                issue_type=issue_type,
                severity=severity,
                justification=f"{desc}: Component parameters suggest non-compliance with {standard}.",
                standard_reference=standard,
            )
            result = env.step(action)
            obs_dict = result.observation

            matched = "🎯 CORRECT" if "CORRECT" in obs_dict.get("step_feedback", "") else "❌ FALSE POS"
            color = GREEN if "CORRECT" in matched else RED
            print(f"\n  [{step_num}] {colorize(matched, color)}: {issue_type}/{severity} on {comp_id}")

            if result.done:
                break

    # Phase 4: Decision
    state = env.state
    if not state.is_done:
        print(colorize("\n\n⚖️  PHASE 4: Final Decision", BOLD))
        print(DIVIDER)

        step_num += 1
        if state.flaws_correctly_found > 0:
            action = ReviewAction(action_type="reject")
            decision = "REJECT"
        else:
            action = ReviewAction(action_type="approve")
            decision = "APPROVE"

        result = env.step(action)
        obs_dict = result.observation
        print(f"\n  [{step_num}] Decision: {colorize(decision, YELLOW)}")
        print(f"       {obs_dict.get('step_feedback', '')}")

    # Final Summary
    state = env.state
    summary = state.episode_summary or {}
    print(f"\n\n{HEADER}")
    print(colorize("  📊 EPISODE RESULTS", BOLD))
    print(HEADER)
    print(f"  Design:      {state.design_id}")
    print(f"  Domain:      {state.design_domain}")
    print(f"  Difficulty:  {state.design_difficulty}")
    print(f"  Decision:    {state.final_decision}")
    print(f"  Steps Used:  {state.steps_taken}/{state.max_steps}")
    print(f"  Flaws Found: {state.flaws_correctly_found}/{state.total_flaws_planted}")
    print(f"  False Pos:   {state.false_positives}")
    print()

    composite = summary.get("composite_score", 0)
    color = GREEN if composite >= 70 else (YELLOW if composite >= 40 else RED)
    print(f"  {colorize(f'COMPOSITE SCORE: {composite}/100', color)}")
    print()

    dims = summary.get("dimensions", {})
    for dim, info in dims.items():
        bar_len = int(info["score"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  {dim:25s} {bar} {info['score']:5.1f}% ({info['weight']})")

    print(f"\n  Total Reward: {summary.get('total_reward', state.total_reward)}")
    print(f"{HEADER}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Expert Design Review Agent Demo")
    parser.add_argument("--domain", default="bridge_truss",
                        choices=["bridge_truss", "pressure_vessel", "gear_assembly", "building_frame"])
    parser.add_argument("--difficulty", default="medium", choices=["easy", "medium", "hard"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--all-domains", action="store_true", help="Run demo across all domains")
    args = parser.parse_args()

    if args.all_domains:
        for domain in ["bridge_truss", "pressure_vessel", "gear_assembly", "building_frame"]:
            run_expert_agent(domain=domain, difficulty=args.difficulty, seed=args.seed)
    else:
        run_expert_agent(domain=args.domain, difficulty=args.difficulty, seed=args.seed)


if __name__ == "__main__":
    main()
