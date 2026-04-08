"""OpenAI baseline inference runner for design_review_env.

This script demonstrates an LLM-powered baseline agent that interacts with the
OpenEnv-compatible environment via the direct Python environment API.

Usage:
    python baseline_inference.py --domain bridge_truss --difficulty medium --seed 42

Requires:
    export OPENAI_API_KEY=<your key>
    or set OPENAI_API_KEY in your shell.
"""

import argparse
import json
import os
import time
import textwrap
from typing import Any, Dict, Optional

try:
    import openai
except ImportError as exc:
    raise SystemExit(
        "openai is required for baseline inference. Install it with `pip install openai`."
    ) from exc

from server.environment import DesignReviewEnvironment
from models import ReviewAction

DEFAULT_MODEL = "gpt-4o-mini"
MAX_STEPS = 30


def get_openai_api_key() -> Optional[str]:
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN")


def build_prompt(observation: dict, state: dict) -> str:
    available_components = observation.get("available_components", [])
    component_list = ", ".join(available_components) or "none"
    current_component = observation.get("current_component") or {}
    current_text = (
        f"Current component: {current_component.get('name', '')} ({current_component.get('component_id', '')})\n"
        f"Details: {json.dumps(current_component, indent=2)}\n"
    ) if current_component else "No current component selected."

    analysis_results = observation.get("analysis_results")
    analysis_text = json.dumps(analysis_results, indent=2) if analysis_results else "No prior analysis results."

    standard_text = json.dumps(observation.get("standard_check_result"), indent=2) if observation.get("standard_check_result") else "No standard comparison results."

    guidance = textwrap.dedent(
        f"""
        You are an engineering design review assistant. The agent is evaluating a design in the domain '{observation.get('design_domain', '')}' with difficulty '{observation.get('design_difficulty', '')}'.

        Design summary:
        {observation.get('design_summary', '')}

        Design requirements:
        {observation.get('design_requirements', '')}

        Available components: {component_list}

        {current_text}

        {analysis_text}

        {standard_text}

        Review progress:
        inspected_components: {observation.get('inspected_components', [])}
        flagged_issues: {observation.get('flagged_issues', [])}
        steps_taken: {observation.get('steps_taken')} / {observation.get('steps_remaining') + observation.get('steps_taken')}
        step_feedback: {observation.get('step_feedback', '')}

        Allowed action types: inspect, flag_issue, request_analysis, compare_standard, request_info, approve, reject.
        When you choose an action, return ONLY valid JSON with keys:
            action_type, component_id, issue_type, severity, justification, standard_reference, analysis_type, parameter_name, parameter_value, standard_code.

        Use the component list and context to select the next best action.
        Prefer inspecting components first, then requesting analysis on suspect parts, then flagging issues, and finally deciding.
        Always return JSON only, without markdown or extra commentary.
        """
    )

    return guidance


def extract_json_object(raw_text: str) -> Optional[str]:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return raw_text[start:end + 1]


def parse_action(response_text: str) -> Dict[str, Any]:
    json_text = extract_json_object(response_text)
    if not json_text:
        raise ValueError("No JSON object found in model response")

    parsed = json.loads(json_text)
    if not isinstance(parsed, dict):
        raise ValueError("Parsed action is not a JSON object")

    return {
        "action_type": parsed.get("action_type", "inspect"),
        "component_id": parsed.get("component_id", ""),
        "issue_type": parsed.get("issue_type", "none"),
        "severity": parsed.get("severity", "none"),
        "justification": parsed.get("justification", ""),
        "standard_reference": parsed.get("standard_reference", ""),
        "analysis_type": parsed.get("analysis_type", ""),
        "parameter_name": parsed.get("parameter_name", ""),
        "parameter_value": float(parsed.get("parameter_value", 0.0) or 0.0),
        "standard_code": parsed.get("standard_code", ""),
    }


def choose_fallback_action(observation: dict) -> ReviewAction:
    available = observation.get("available_components", [])
    inspected = set(observation.get("inspected_components", []))
    first_uninspected = next((cid for cid in available if cid not in inspected), None)
    if first_uninspected:
        return ReviewAction(action_type="inspect", component_id=first_uninspected)
    if observation.get("steps_remaining", 0) <= 2:
        return ReviewAction(action_type="approve")
    return ReviewAction(action_type="request_info", component_id=available[0] if available else "")


def ask_model_for_action(model: str, observation: dict, state: dict) -> ReviewAction:
    prompt = build_prompt(observation, state)
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful engineering design review agent."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=250,
    )

    content = response.choices[0].message.content
    try:
        action_data = parse_action(content)
        return ReviewAction(**action_data)
    except Exception as exc:
        print("[WARNING] Failed to parse model response, using fallback action.", exc)
        print("Raw model response:", content)
        return choose_fallback_action(observation)


def run_episode(domain: str, difficulty: str, seed: int, model: str) -> Dict[str, Any]:
    env = DesignReviewEnvironment(domain=domain, difficulty=difficulty, seed=seed)
    obs = env.reset(seed=seed, domain=domain, difficulty=difficulty)
    observation = obs.model_dump() if hasattr(obs, "model_dump") else obs.dict()
    state = env.state.model_dump() if hasattr(env.state, "model_dump") else env.state.dict()

    transcript = []
    total_reward = 0.0
    done = False

    for step_num in range(1, MAX_STEPS + 1):
        print(f"\n=== Step {step_num} / {state.get('max_steps', MAX_STEPS)} ===")
        action = ask_model_for_action(model=model, observation=observation, state=state)
        print("Action:", action.model_dump() if hasattr(action, "model_dump") else action.dict())

        result = env.step(action)
        obs = result.observation
        observation = obs.model_dump() if hasattr(obs, "model_dump") else obs.dict()
        state = env.state.model_dump() if hasattr(env.state, "model_dump") else env.state.dict()
        total_reward += result.reward
        done = result.done

        step_record = {
            "step": step_num,
            "action": action.model_dump() if hasattr(action, "model_dump") else action.dict(),
            "observation": observation,
            "reward": result.reward,
            "done": done,
        }
        transcript.append(step_record)

        print("Reward:", result.reward)
        print("Done:", done)
        print("Feedback:", observation.get("step_feedback", ""))

        if done:
            break

    return {
        "domain": domain,
        "difficulty": difficulty,
        "seed": seed,
        "model": model,
        "total_reward": total_reward,
        "steps": len(transcript),
        "done": done,
        "final_state": state,
        "transcript": transcript,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a baseline OpenAI inference agent on design_review_env.")
    parser.add_argument("--domain", default="bridge_truss", choices=["bridge_truss", "pressure_vessel", "gear_assembly", "building_frame"], help="Design domain")
    parser.add_argument("--difficulty", default="medium", choices=["easy", "medium", "hard"], help="Difficulty level")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible design generation")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model to use for inference")
    parser.add_argument("--output", default="baseline_results.json", help="Output summary JSON file")
    parser.add_argument("--steps", type=int, default=MAX_STEPS, help="Maximum steps per episode")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = get_openai_api_key()
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY or HF_TOKEN is required to run baseline inference."
        )

    openai.api_key = api_key
    global MAX_STEPS
    MAX_STEPS = args.steps

    summary = run_episode(domain=args.domain, difficulty=args.difficulty, seed=args.seed, model=args.model)
    timestamp = int(time.time())
    output_path = args.output or f"baseline_results_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(f"\nSaved baseline inference results to: {output_path}")
    print(json.dumps({
        "domain": summary["domain"],
        "difficulty": summary["difficulty"],
        "seed": summary["seed"],
        "model": summary["model"],
        "total_reward": summary["total_reward"],
        "steps": summary["steps"],
        "done": summary["done"],
        "composite_score": summary["final_state"].get("composite_score"),
    }, indent=2))


if __name__ == "__main__":
    main()
