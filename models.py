"""
Design Review Environment — Data Models (v2.0)

Defines strongly-typed Action, Observation, and State models for the
AI-Driven Engineering Design Review RL Environment.

An LLM agent acts as a senior design reviewer, systematically inspecting
engineering designs across multiple domains to identify structural flaws,
safety violations, and standards non-compliance.

Supports 4 engineering domains:
  - Bridge Truss (AISC 360-22)
  - Pressure Vessel (ASME BPVC Section VIII)
  - Gear Assembly (AGMA 2001-D04)
  - Building Frame (AISC 360-22 / IBC)
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import Field

try:
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:
    from openenv.core.env_server import Action, Observation, State


# ── Enums for type safety ──────────────────────────────────────────────────

class ActionType(str, Enum):
    INSPECT = "inspect"
    FLAG_ISSUE = "flag_issue"
    REQUEST_ANALYSIS = "request_analysis"
    COMPARE_STANDARD = "compare_standard"
    REQUEST_INFO = "request_info"
    APPROVE = "approve"
    REJECT = "reject"


class IssueType(str, Enum):
    STRUCTURAL = "structural"
    MATERIAL = "material"
    SAFETY = "safety"
    TOLERANCE = "tolerance"
    DIMENSIONAL = "dimensional"
    ELECTRICAL = "electrical"
    FATIGUE = "fatigue"
    CORROSION = "corrosion"
    THERMAL = "thermal"
    NONE = "none"


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"
    NONE = "none"


class DesignDomain(str, Enum):
    BRIDGE_TRUSS = "bridge_truss"
    PRESSURE_VESSEL = "pressure_vessel"
    GEAR_ASSEMBLY = "gear_assembly"
    BUILDING_FRAME = "building_frame"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AnalysisType(str, Enum):
    STRESS = "stress"
    DEFLECTION = "deflection"
    BUCKLING = "buckling"
    FATIGUE_LIFE = "fatigue_life"
    WELD_CAPACITY = "weld_capacity"
    BOLT_CAPACITY = "bolt_capacity"
    PRESSURE_RATING = "pressure_rating"
    GEAR_CONTACT = "gear_contact"
    SAFETY_FACTOR = "safety_factor"


# ── Action ─────────────────────────────────────────────────────────────────

class ReviewAction(Action):
    """
    An action taken by the reviewer agent at each step.

    Supported action_types:
        - "inspect"          : Inspect a specific component for its parameters
        - "flag_issue"       : Flag a detected issue on a component
        - "request_analysis" : Request physics-based analysis on a component
        - "compare_standard" : Check a parameter against a specific standard
        - "request_info"     : Request contextual information
        - "approve"          : Approve the entire design (ends episode)
        - "reject"           : Reject the entire design (ends episode)
    """

    action_type: str = "inspect"
    component_id: str = ""
    issue_type: str = "none"
    severity: str = "none"
    justification: str = ""
    standard_reference: str = ""

    # For request_analysis
    analysis_type: str = ""  # stress, deflection, buckling, etc.

    # For compare_standard
    parameter_name: str = ""
    parameter_value: float = 0.0
    standard_code: str = ""  # e.g., "AISC 360-22 J4.1"


# ── Observation ────────────────────────────────────────────────────────────

class ReviewObservation(Observation):
    """
    What the reviewer agent observes after each action.
    """

    # Design context
    design_id: str = ""
    design_type: str = ""
    design_domain: str = ""
    design_summary: str = ""
    design_requirements: str = ""
    design_difficulty: str = "medium"

    # Current component details (after inspect)
    current_component: Optional[Dict[str, Any]] = None
    component_context: str = ""

    # Analysis results (after request_analysis)
    analysis_results: Optional[Dict[str, Any]] = None

    # Standard comparison results (after compare_standard)
    standard_check_result: Optional[Dict[str, Any]] = None

    # Review progress
    available_components: List[str] = Field(default_factory=list)
    inspected_components: List[str] = Field(default_factory=list)
    flagged_issues: List[Dict[str, Any]] = Field(default_factory=list)
    review_progress: float = 0.0
    steps_taken: int = 0
    steps_remaining: int = 0

    # Feedback
    step_feedback: str = ""
    action_valid: bool = True
    hint: str = ""


# ── State ──────────────────────────────────────────────────────────────────

class ReviewState(State):
    """
    Internal state tracking the review session.
    Exposed via state() for monitoring and evaluation.
    """

    # Episode tracking
    design_id: str = ""
    design_type: str = ""
    design_domain: str = ""
    design_difficulty: str = "medium"
    seed: int = 0

    # Ground truth (hidden from agent in observations)
    total_flaws_planted: int = 0
    flaw_manifest: List[Dict[str, Any]] = Field(default_factory=list)

    # Review metrics
    flaws_correctly_found: int = 0
    flaws_missed: int = 0
    false_positives: int = 0
    critical_flaws_missed: int = 0
    components_inspected: int = 0
    total_components: int = 0
    analyses_requested: int = 0
    standards_checked: int = 0

    # Scoring (computed by grader)
    detection_precision: float = 0.0
    detection_recall: float = 0.0
    severity_accuracy: float = 0.0
    efficiency_score: float = 0.0
    reasoning_quality: float = 0.0
    ethical_score: float = 1.0
    composite_score: float = 0.0
    total_reward: float = 0.0

    # Episode state
    is_done: bool = False
    final_decision: str = ""
    max_steps: int = 30
    steps_taken: int = 0

    # Episode transcript
    action_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Episode summary (populated on episode end)
    episode_summary: Optional[Dict[str, Any]] = None
