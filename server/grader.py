"""
Multi-Dimensional Grader — Design Review Scoring Engine

Computes a composite score across 6 dimensions to evaluate
how well an AI agent performed as a design reviewer.

Dimensions:
  1. Detection Precision (25%) — TP / (TP + FP)
  2. Detection Recall    (25%) — TP / (TP + FN)
  3. Severity Accuracy   (15%) — Correct severity assignments
  4. Efficiency          (10%) — Flaws found per step
  5. Reasoning Quality   (10%) — Standards referenced correctly
  6. Ethical Safety       (15%) — Penalty for missing critical flaws

Produces:
  - Per-step immediate reward
  - Episode-end summary with all metrics
  - Normalized 0-100 composite score
"""

from typing import Dict, Any, List, Optional


# ── Reward Constants ─────────────────────────────────────────────────────

REWARDS = {
    # Positive
    "inspect_new": 0.15,
    "correct_flag": 5.0,
    "correct_severity_bonus": 2.5,
    "correct_standard_bonus": 1.5,
    "correct_approve": 10.0,
    "correct_reject": 8.0,
    "analysis_useful": 0.3,

    # Negative
    "inspect_duplicate": -0.05,
    "false_positive": -3.0,
    "wrong_severity": -0.5,
    "incorrect_approve": -25.0,  # Heavy: approved a flawed design
    "unjustified_reject": -8.0,
    "invalid_action": -1.0,
    "timeout_with_misses": -15.0,
    "request_info_penalty": -0.1,
    "no_justification": -0.5,

    # Neutral
    "analysis_request": -0.05,  # Small cost to prevent spam
    "standard_check": -0.05,
}

# ── Weights for composite score ──────────────────────────────────────────

DIMENSION_WEIGHTS = {
    "detection_precision": 0.25,
    "detection_recall": 0.25,
    "severity_accuracy": 0.15,
    "efficiency": 0.10,
    "reasoning_quality": 0.10,
    "ethical_safety": 0.15,
}


class Grader:
    """Multi-dimensional grading engine for design review episodes."""

    def __init__(self):
        self.true_positives = 0
        self.false_positives = 0
        self.severity_correct = 0
        self.severity_attempts = 0
        self.standards_referenced = 0
        self.standards_correct = 0
        self.steps_taken = 0
        self.total_reward = 0.0
        self.critical_flaws_missed = 0
        self.total_flaws = 0
        self.flaws_found = 0
        self.justifications_provided = 0
        self.analyses_requested = 0

    # ── Per-Step Reward Computation ──────────────────────────────────────

    def reward_inspect(self, is_new: bool) -> float:
        """Reward for inspecting a component."""
        self.steps_taken += 1
        r = REWARDS["inspect_new"] if is_new else REWARDS["inspect_duplicate"]
        self.total_reward += r
        return r

    def reward_flag_issue(
        self,
        matched: bool,
        severity_correct: bool,
        standard_correct: bool,
        already_flagged: bool,
        has_justification: bool,
        is_critical: bool = False,
    ) -> float:
        """Reward for flagging an issue."""
        self.steps_taken += 1
        r = 0.0

        if matched and not already_flagged:
            self.true_positives += 1
            self.flaws_found += 1
            r += REWARDS["correct_flag"]

            self.severity_attempts += 1
            if severity_correct:
                self.severity_correct += 1
                r += REWARDS["correct_severity_bonus"]
            else:
                r += REWARDS["wrong_severity"]

            if standard_correct:
                self.standards_correct += 1
                r += REWARDS["correct_standard_bonus"]

            if has_justification:
                self.justifications_provided += 1
            else:
                r += REWARDS["no_justification"]

        elif matched and already_flagged:
            r += REWARDS["inspect_duplicate"]
        else:
            self.false_positives += 1
            r += REWARDS["false_positive"]

        if has_justification:
            self.standards_referenced += 1

        self.total_reward += r
        return r

    def reward_analysis(self) -> float:
        """Reward for requesting physics analysis."""
        self.steps_taken += 1
        self.analyses_requested += 1
        r = REWARDS["analysis_request"]
        self.total_reward += r
        return r

    def reward_standard_check(self) -> float:
        """Reward for checking against a standard."""
        self.steps_taken += 1
        r = REWARDS["standard_check"]
        self.total_reward += r
        return r

    def reward_request_info(self) -> float:
        """Reward for requesting additional info."""
        self.steps_taken += 1
        r = REWARDS["request_info_penalty"]
        self.total_reward += r
        return r

    def reward_approve(self, flaws_remaining: int, total_flaws: int) -> float:
        """Reward for approving the design."""
        self.steps_taken += 1
        self.total_flaws = total_flaws

        if flaws_remaining == 0:
            r = REWARDS["correct_approve"]
        else:
            r = REWARDS["incorrect_approve"]
            # Count critical flaws missed
            self.critical_flaws_missed = flaws_remaining

        self.total_reward += r
        return r

    def reward_reject(self, flaws_found: int, total_flaws: int) -> float:
        """Reward for rejecting the design."""
        self.steps_taken += 1
        self.total_flaws = total_flaws

        if flaws_found > 0:
            r = REWARDS["correct_reject"]
            # Bonus for finding more flaws before rejecting
            r += flaws_found * 1.0
        else:
            r = REWARDS["unjustified_reject"]

        self.total_reward += r
        return r

    def reward_timeout(self, flaws_remaining: int, total_flaws: int) -> float:
        """Penalty for running out of steps."""
        self.total_flaws = total_flaws
        if flaws_remaining > 0:
            r = REWARDS["timeout_with_misses"]
            self.critical_flaws_missed = flaws_remaining
        else:
            r = 0.0
        self.total_reward += r
        return r

    def reward_invalid(self) -> float:
        """Penalty for invalid action."""
        self.steps_taken += 1
        r = REWARDS["invalid_action"]
        self.total_reward += r
        return r

    # ── Episode-End Scoring ──────────────────────────────────────────────

    def compute_composite_score(self, total_flaws: int, max_steps: int) -> Dict[str, Any]:
        """
        Compute the final composite score across all 6 dimensions.
        Returns a detailed scoring breakdown.
        """
        self.total_flaws = max(total_flaws, self.total_flaws)
        flaws_missed = max(0, self.total_flaws - self.flaws_found)

        # 1. Detection Precision: TP / (TP + FP)
        if self.true_positives + self.false_positives > 0:
            precision = self.true_positives / (self.true_positives + self.false_positives)
        else:
            precision = 0.0

        # 2. Detection Recall: TP / (TP + FN)
        if self.total_flaws > 0:
            recall = self.flaws_found / self.total_flaws
        else:
            recall = 1.0

        # 3. Severity Accuracy
        if self.severity_attempts > 0:
            severity_acc = self.severity_correct / self.severity_attempts
        else:
            severity_acc = 0.0

        # 4. Efficiency: flaws found per step (normalized)
        if self.steps_taken > 0 and self.total_flaws > 0:
            optimal_steps = self.total_flaws * 2  # inspect + flag per flaw
            efficiency = min(1.0, optimal_steps / max(self.steps_taken, 1))
        else:
            efficiency = 0.0

        # 5. Reasoning Quality: standards referenced + justifications
        if self.flaws_found > 0:
            reasoning = min(1.0, (self.standards_correct + self.justifications_provided * 0.5) / (self.flaws_found * 1.5))
        else:
            reasoning = 0.0

        # 6. Ethical Safety: penalty for missing critical flaws
        if self.total_flaws > 0:
            ethical = 1.0 - (self.critical_flaws_missed / self.total_flaws)
        else:
            ethical = 1.0

        # Composite weighted score (0-100)
        composite = (
            precision * DIMENSION_WEIGHTS["detection_precision"]
            + recall * DIMENSION_WEIGHTS["detection_recall"]
            + severity_acc * DIMENSION_WEIGHTS["severity_accuracy"]
            + efficiency * DIMENSION_WEIGHTS["efficiency"]
            + reasoning * DIMENSION_WEIGHTS["reasoning_quality"]
            + ethical * DIMENSION_WEIGHTS["ethical_safety"]
        ) * 100

        return {
            "composite_score": round(composite, 1),
            "total_reward": round(self.total_reward, 2),
            "dimensions": {
                "detection_precision": {"score": round(precision * 100, 1), "weight": "25%", "raw": f"{self.true_positives}TP / {self.true_positives + self.false_positives}total"},
                "detection_recall": {"score": round(recall * 100, 1), "weight": "25%", "raw": f"{self.flaws_found}/{self.total_flaws} flaws found"},
                "severity_accuracy": {"score": round(severity_acc * 100, 1), "weight": "15%", "raw": f"{self.severity_correct}/{self.severity_attempts} correct"},
                "efficiency": {"score": round(efficiency * 100, 1), "weight": "10%", "raw": f"{self.steps_taken} steps for {self.flaws_found} flaws"},
                "reasoning_quality": {"score": round(reasoning * 100, 1), "weight": "10%", "raw": f"{self.standards_correct} standards + {self.justifications_provided} justifications"},
                "ethical_safety": {"score": round(ethical * 100, 1), "weight": "15%", "raw": f"{self.critical_flaws_missed} critical misses"},
            },
            "raw_metrics": {
                "true_positives": self.true_positives,
                "false_positives": self.false_positives,
                "flaws_found": self.flaws_found,
                "flaws_missed": flaws_missed,
                "total_flaws": self.total_flaws,
                "severity_correct": self.severity_correct,
                "severity_attempts": self.severity_attempts,
                "steps_taken": self.steps_taken,
                "max_steps": max_steps,
                "analyses_requested": self.analyses_requested,
                "standards_referenced": self.standards_referenced,
            },
        }
