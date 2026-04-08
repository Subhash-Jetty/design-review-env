"""
Design Review Environment — Core Environment Logic (v2.0)

Server-side OpenEnv Environment implementation for the AI-Driven
Engineering Design Review system. Integrates:

  - Procedural design generation (4 domains × 3 difficulties)
  - Physics-based analysis engine
  - Multi-dimensional grading
  - Full episode transcript logging

The agent acts as a senior design reviewer, systematically
inspecting components, running analyses, cross-referencing
standards, and making approve/reject decisions.
"""

import random
from typing import Optional, Any
from uuid import uuid4

try:
    from openenv.core.env_server import Environment
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:
    try:
        from openenv.core.env_server import Environment, Action, Observation, State
    except ImportError:
        # Fallback for local testing
        from pydantic import BaseModel
        class Environment:
            pass
        class Action(BaseModel):
            pass
        class Observation(BaseModel):
            pass
        class State(BaseModel):
            pass

try:
    from openenv.core.client_types import StepResult
except ImportError:
    from pydantic import BaseModel
    class StepResult(BaseModel):
        observation: dict
        reward: float
        done: bool

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ReviewAction, ReviewObservation, ReviewState
from server.design_catalog import generate_design, DIFFICULTY_CONFIG
from server.physics_engine import PhysicsEngine
from server.grader import Grader


class DesignReviewEnvironment(Environment):
    """
    Server-side Environment for AI-Driven Engineering Design Review.

    Supports:
      - 4 engineering domains: bridge_truss, pressure_vessel, gear_assembly, building_frame
      - 3 difficulty levels: easy, medium, hard
      - 7 action types: inspect, flag_issue, request_analysis, compare_standard, request_info, approve, reject
      - Multi-dimensional grading across 6 axes
      - Full episode transcript for training data generation
    """

    def __init__(
        self,
        domain: str = "bridge_truss",
        difficulty: str = "medium",
        seed: Optional[int] = None,
    ):
        try:
            super().__init__()
        except TypeError:
            pass

        self.default_domain = domain
        self.default_difficulty = difficulty
        self.default_seed = seed

        self._state = ReviewState()
        self._components = {}
        self._flaws = []
        self._design_info = {}
        self._grader = Grader()
        self._inspected = []
        self._flagged_correctly = []
        self._flagged_issues_detail = []
        self._physics = PhysicsEngine()

    def reset(
        self,
        seed: Optional[int] = None,
        domain: Optional[str] = None,
        difficulty: Optional[str] = None,
        **kwargs,
    ) -> ReviewObservation:
        """
        Reset the environment and generate a new design.

        Args:
            seed: Random seed for reproducible design generation
            domain: Engineering domain (bridge_truss, pressure_vessel, gear_assembly, building_frame)
            difficulty: Difficulty level (easy, medium, hard)
        """
        actual_seed = seed or self.default_seed or random.randint(1, 99999)
        actual_domain = domain or self.default_domain
        actual_difficulty = difficulty or self.default_difficulty

        # Generate new design
        self._components, self._flaws, self._design_info = generate_design(
            domain=actual_domain,
            difficulty=actual_difficulty,
            seed=actual_seed,
        )

        cfg = DIFFICULTY_CONFIG[actual_difficulty]
        max_steps = cfg["max_steps"]

        # Initialize state
        self._state = ReviewState(
            design_id=f"{actual_domain.upper()[:4]}-{actual_seed}",
            design_type=self._design_info.get("design_type", actual_domain),
            design_domain=actual_domain,
            design_difficulty=actual_difficulty,
            seed=actual_seed,
            total_flaws_planted=len(self._flaws),
            flaw_manifest=self._flaws,
            total_components=len(self._components),
            max_steps=max_steps,
        )

        # Reset tracking
        self._inspected = []
        self._flagged_correctly = []
        self._flagged_issues_detail = []
        self._grader = Grader()

        return ReviewObservation(
            design_id=self._state.design_id,
            design_type=self._state.design_type,
            design_domain=actual_domain,
            design_summary=self._design_info.get("summary", ""),
            design_requirements=self._design_info.get("requirements", ""),
            design_difficulty=actual_difficulty,
            available_components=list(self._components.keys()),
            inspected_components=[],
            flagged_issues=[],
            steps_taken=0,
            steps_remaining=max_steps,
            step_feedback=(
                f"🔧 Design Review Session Started\n"
                f"Design: {self._state.design_id} ({actual_domain.replace('_', ' ').title()})\n"
                f"Difficulty: {actual_difficulty.upper()}\n"
                f"Components: {len(self._components)} | Max Steps: {max_steps}\n"
                f"Standards: {', '.join(self._design_info.get('applicable_standards', []))}\n"
                f"\nBegin by inspecting components to identify potential flaws."
            ),
            action_valid=True,
        )

    def step(self, action: ReviewAction) -> StepResult:
        """Execute a step in the environment."""
        self._state.steps_taken += 1
        steps_remaining = self._state.max_steps - self._state.steps_taken

        feedback = ""
        valid = True
        reward = 0.0
        current_comp = None
        comp_context = ""
        analysis_results = None
        standard_check_result = None
        is_done = False
        hint = ""

        action_type = action.action_type

        # ── INSPECT ──────────────────────────────────────────────────
        if action_type == "inspect":
            if action.component_id in self._components:
                current_comp = self._components[action.component_id]
                comp_context = self._get_component_context(action.component_id)

                if action.component_id not in self._inspected:
                    self._inspected.append(action.component_id)
                    self._state.components_inspected += 1
                    reward = self._grader.reward_inspect(is_new=True)
                    feedback = f"✅ Inspected: {current_comp.get('name', action.component_id)}"
                else:
                    reward = self._grader.reward_inspect(is_new=False)
                    feedback = f"ℹ️ Already inspected: {current_comp.get('name', action.component_id)}"
            else:
                feedback = f"❌ Component '{action.component_id}' not found. Available: {list(self._components.keys())}"
                valid = False
                reward = self._grader.reward_invalid()

        # ── FLAG ISSUE ───────────────────────────────────────────────
        elif action_type == "flag_issue":
            matched_flaw = None
            for flaw in self._flaws:
                if (flaw["component_id"] == action.component_id and
                    flaw["issue_type"] == action.issue_type):
                    matched_flaw = flaw
                    break

            already_flagged = action.component_id in self._flagged_correctly
            severity_correct = matched_flaw and matched_flaw.get("severity") == action.severity

            # Check if standard reference is relevant
            standard_correct = False
            if matched_flaw and action.standard_reference:
                flaw_std = matched_flaw.get("standard", "").lower()
                ref = action.standard_reference.lower()
                # Partial match is acceptable
                standard_correct = any(
                    part in ref for part in flaw_std.split() if len(part) > 3
                ) or any(
                    part in flaw_std for part in ref.split() if len(part) > 3
                )

            has_justification = len(action.justification) > 10

            reward = self._grader.reward_flag_issue(
                matched=matched_flaw is not None,
                severity_correct=severity_correct,
                standard_correct=standard_correct,
                already_flagged=already_flagged,
                has_justification=has_justification,
                is_critical=matched_flaw and matched_flaw.get("severity") == "critical" if matched_flaw else False,
            )

            if matched_flaw and not already_flagged:
                self._flagged_correctly.append(action.component_id)
                self._state.flaws_correctly_found += 1
                sev_msg = "✓ correct" if severity_correct else f"✗ actual: {matched_flaw['severity']}"
                feedback = (
                    f"🎯 CORRECT: {action.issue_type} issue identified on {action.component_id}\n"
                    f"   Severity: {action.severity} ({sev_msg})\n"
                    f"   Ground truth: {matched_flaw.get('description', '')}"
                )
                if severity_correct:
                    self._state.severity_accuracy += 1
            elif matched_flaw and already_flagged:
                feedback = f"⚠️ Already flagged: {action.issue_type} on {action.component_id}"
            else:
                self._state.false_positives += 1
                feedback = f"❌ FALSE POSITIVE: No {action.issue_type} issue exists on {action.component_id}"

            self._flagged_issues_detail.append({
                "component_id": action.component_id,
                "issue_type": action.issue_type,
                "severity": action.severity,
                "matched": matched_flaw is not None,
                "justification": action.justification,
            })

        # ── REQUEST ANALYSIS ─────────────────────────────────────────
        elif action_type == "request_analysis":
            if action.component_id in self._components:
                comp = self._components[action.component_id]
                atype = action.analysis_type or "stress"
                analysis_results = PhysicsEngine.analyze_component(comp, atype)
                self._state.analyses_requested += 1
                reward = self._grader.reward_analysis()
                feedback = f"📊 Analysis complete: {atype} on {comp.get('name', action.component_id)}"

                # Give a hint if analysis reveals a problem
                if analysis_results.get("status") == "FAIL":
                    hint = f"⚠️ Analysis indicates potential failure — safety factor below minimum."
                    reward += 0.3  # bonus for useful analysis
                elif analysis_results.get("status") == "MARGINAL":
                    hint = f"⚡ Analysis shows marginal performance — investigate further."
                    reward += 0.1
            else:
                feedback = f"❌ Component '{action.component_id}' not found."
                valid = False
                reward = self._grader.reward_invalid()

        # ── COMPARE STANDARD ─────────────────────────────────────────
        elif action_type == "compare_standard":
            if action.component_id in self._components:
                comp = self._components[action.component_id]
                self._state.standards_checked += 1
                reward = self._grader.reward_standard_check()

                # Simulate a standards check
                param = action.parameter_name
                value = action.parameter_value
                std_code = action.standard_code

                check_result = self._check_against_standard(comp, param, value, std_code)
                standard_check_result = check_result
                feedback = f"📋 Standard check: {param} vs {std_code}"
            else:
                feedback = f"❌ Component '{action.component_id}' not found."
                valid = False
                reward = self._grader.reward_invalid()

        # ── REQUEST INFO ─────────────────────────────────────────────
        elif action_type == "request_info":
            reward = self._grader.reward_request_info()
            # Provide applicable standards info
            standards = self._design_info.get("applicable_standards", [])
            feedback = (
                f"📚 Applicable Standards:\n"
                + "\n".join(f"  • {s}" for s in standards)
                + f"\n\nDesign Requirements:\n  {self._design_info.get('requirements', 'N/A')}"
            )

        # ── APPROVE ──────────────────────────────────────────────────
        elif action_type == "approve":
            self._state.final_decision = "approved"
            is_done = True
            flaws_remaining = self._state.total_flaws_planted - self._state.flaws_correctly_found
            reward = self._grader.reward_approve(flaws_remaining, self._state.total_flaws_planted)

            if flaws_remaining == 0:
                feedback = "✅ Design APPROVED — All flaws were identified before approval. Excellent review!"
            else:
                self._state.critical_flaws_missed = flaws_remaining
                missed_desc = [f for f in self._flaws if f["component_id"] not in self._flagged_correctly]
                feedback = (
                    f"🚨 DANGEROUS APPROVAL — {flaws_remaining} flaw(s) remain unfound:\n"
                    + "\n".join(f"  ❌ {f['component_id']}: {f['description']}" for f in missed_desc)
                )

        # ── REJECT ───────────────────────────────────────────────────
        elif action_type == "reject":
            self._state.final_decision = "rejected"
            is_done = True
            reward = self._grader.reward_reject(
                self._state.flaws_correctly_found,
                self._state.total_flaws_planted,
            )

            if self._state.flaws_correctly_found > 0:
                feedback = (
                    f"✅ Design REJECTED — {self._state.flaws_correctly_found}/{self._state.total_flaws_planted} "
                    f"flaws documented before rejection."
                )
            else:
                feedback = "⚠️ UNJUSTIFIED REJECTION — No flaws were documented to support this decision."

        # ── UNKNOWN ──────────────────────────────────────────────────
        else:
            valid = False
            reward = self._grader.reward_invalid()
            feedback = (
                f"❌ Unknown action: '{action_type}'. "
                f"Valid actions: inspect, flag_issue, request_analysis, compare_standard, request_info, approve, reject"
            )

        # ── Step limit check ─────────────────────────────────────────
        if steps_remaining <= 0 and not is_done:
            is_done = True
            flaws_remaining = self._state.total_flaws_planted - self._state.flaws_correctly_found
            timeout_reward = self._grader.reward_timeout(
                flaws_remaining, self._state.total_flaws_planted
            )
            reward += timeout_reward
            feedback += f"\n\n⏰ TIME'S UP — Review session ended after {self._state.max_steps} steps."
            if flaws_remaining > 0:
                feedback += f" {flaws_remaining} flaw(s) remain unfound."

        # ── Update state ─────────────────────────────────────────────
        self._state.total_reward += reward
        self._state.is_done = is_done

        # Log action to transcript
        self._state.action_history.append({
            "step": self._state.steps_taken,
            "action_type": action_type,
            "component_id": action.component_id,
            "reward": round(reward, 2),
            "valid": valid,
        })

        # Compute episode summary on done
        if is_done:
            summary = self._grader.compute_composite_score(
                total_flaws=self._state.total_flaws_planted,
                max_steps=self._state.max_steps,
            )
            self._state.episode_summary = summary
            self._state.composite_score = summary["composite_score"]
            self._state.detection_precision = summary["dimensions"]["detection_precision"]["score"]
            self._state.detection_recall = summary["dimensions"]["detection_recall"]["score"]
            self._state.severity_accuracy = summary["dimensions"]["severity_accuracy"]["score"]
            self._state.efficiency_score = summary["dimensions"]["efficiency"]["score"]
            self._state.reasoning_quality = summary["dimensions"]["reasoning_quality"]["score"]
            self._state.ethical_score = summary["dimensions"]["ethical_safety"]["score"]

            feedback += f"\n\n{'='*50}\n📊 EPISODE SCORE: {summary['composite_score']}/100\n{'='*50}"
            for dim, info in summary["dimensions"].items():
                feedback += f"\n  {dim}: {info['score']}% (weight: {info['weight']})"

        # ── Build observation ────────────────────────────────────────
        obs = ReviewObservation(
            design_id=self._state.design_id,
            design_type=self._state.design_type,
            design_domain=self._state.design_domain,
            design_summary=self._design_info.get("summary", ""),
            design_requirements=self._design_info.get("requirements", ""),
            design_difficulty=self._state.design_difficulty,
            current_component=current_comp,
            component_context=comp_context,
            analysis_results=analysis_results,
            standard_check_result=standard_check_result,
            available_components=[c for c in self._components if c not in self._inspected],
            inspected_components=list(self._inspected),
            flagged_issues=self._flagged_issues_detail,
            review_progress=self._state.flaws_correctly_found / max(1, self._state.total_flaws_planted),
            steps_taken=self._state.steps_taken,
            steps_remaining=max(0, self._state.max_steps - self._state.steps_taken),
            step_feedback=feedback,
            action_valid=valid,
            hint=hint,
            reward=reward,
            done=is_done,
        )

        return StepResult(
            observation=obs,
            reward=reward,
            done=is_done,
        )

    @property
    def state(self) -> ReviewState:
        """Get the current environment state."""
        return self._state

    # ── Private Helpers ──────────────────────────────────────────────────

    def _get_component_context(self, comp_id: str) -> str:
        """Get relevant standards context for a component."""
        comp = self._components.get(comp_id, {})
        ct = comp.get("component_type", "")
        standards = self._design_info.get("applicable_standards", [])

        context_map = {
            "chord": "Check: member capacity (AISC Ch. E/F), slenderness limits, connection adequacy.",
            "member": "Check: axial capacity, slenderness ratio (<200 for compression), connection details.",
            "beam": "Check: flexural capacity (AISC Ch. F), deflection (L/360), lateral bracing.",
            "column": "Check: combined axial+bending (AISC Ch. H), effective length, base plate.",
            "brace": "Check: slenderness ratio, connection capacity, seismic compactness (AISC 341).",
            "connection": "Check: bolt capacity (AISC Ch. J), weld size (Table J2.4), block shear.",
            "shell": "Check: wall thickness (ASME UG-27), corrosion allowance, PWHT requirements.",
            "nozzle": "Check: reinforcement (ASME UG-37), weld details, nozzle loads.",
            "flange": "Check: pressure-temperature rating (ASME B16.5), bolt loading, gasket seating.",
            "bearing": "Check: bearing capacity, pad dimensions, contact pressure.",
            "gear": "Check: contact stress (AGMA), bending stress, hardness requirements.",
            "pinion": "Check: contact stress (AGMA), face width (8-12× module), hardness.",
            "shaft": "Check: torsional capacity, keyway stress concentration, critical speed.",
            "housing": "Check: wall thickness, mounting bolt capacity, seal integrity.",
            "support": "Check: saddle weld capacity, contact angle adequacy, local shell stress.",
        }

        base = context_map.get(ct, f"Review all parameters against applicable standards.")
        return f"{base}\nApplicable standards: {', '.join(standards)}"

    def _check_against_standard(self, comp, param, value, std_code):
        """Simulate checking a parameter against a standard."""
        # Simplified standard checks
        result = {
            "parameter": param,
            "submitted_value": value,
            "standard": std_code,
            "component_value": comp.get(param, "N/A"),
        }

        if param in comp:
            actual = comp[param]
            if isinstance(actual, (int, float)):
                if value > 0:
                    ratio = actual / value if value != 0 else float("inf")
                    result["ratio"] = round(ratio, 3)
                    result["compliant"] = ratio >= 1.0
                    result["status"] = "COMPLIANT" if ratio >= 1.0 else "NON-COMPLIANT"
                else:
                    result["status"] = "INVALID_VALUE"
            else:
                result["status"] = "NON-NUMERIC"
        else:
            result["status"] = "PARAMETER_NOT_FOUND"
            result["available_parameters"] = list(comp.keys())

        return result