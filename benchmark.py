"""
Benchmark Runner — Design Review Environment

Runs the expert agent across multiple episodes and produces
aggregate statistics for evaluating environment quality.

Run:
    python benchmark.py [--episodes 20] [--seed 100]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_agent import run_expert_agent


def run_benchmark(episodes=20, base_seed=100):
    """Run benchmark across all domains and difficulties."""
    print("\n" + "=" * 70)
    print("  📈 DESIGN REVIEW ENVIRONMENT — BENCHMARK SUITE")
    print("=" * 70)

    domains = ["bridge_truss", "pressure_vessel", "gear_assembly", "building_frame"]
    difficulties = ["easy", "medium", "hard"]

    all_results = []

    for domain in domains:
        for difficulty in difficulties:
            scores = []
            for ep in range(episodes // (len(domains) * len(difficulties)) + 1):
                seed = base_seed + ep * 7
                try:
                    summary = run_expert_agent(domain=domain, difficulty=difficulty, seed=seed)
                    if summary:
                        scores.append(summary.get("composite_score", 0))
                except Exception as e:
                    print(f"  ⚠️ Error in {domain}/{difficulty} seed={seed}: {e}")

            if scores:
                avg = sum(scores) / len(scores)
                mn = min(scores)
                mx = max(scores)
                all_results.append({
                    "domain": domain,
                    "difficulty": difficulty,
                    "avg_score": round(avg, 1),
                    "min_score": round(mn, 1),
                    "max_score": round(mx, 1),
                    "episodes": len(scores),
                })

    # Print summary table
    print("\n\n" + "=" * 70)
    print("  📊 BENCHMARK RESULTS")
    print("=" * 70)
    print(f"\n  {'Domain':<20} {'Difficulty':<12} {'Avg':>6} {'Min':>6} {'Max':>6} {'N':>4}")
    print(f"  {'-'*20} {'-'*12} {'-'*6} {'-'*6} {'-'*6} {'-'*4}")

    for r in all_results:
        print(f"  {r['domain']:<20} {r['difficulty']:<12} {r['avg_score']:>6.1f} {r['min_score']:>6.1f} {r['max_score']:>6.1f} {r['episodes']:>4}")

    # Overall stats
    if all_results:
        all_scores = [r["avg_score"] for r in all_results]
        overall_avg = sum(all_scores) / len(all_scores)
        print(f"\n  {'Overall Average':<33} {overall_avg:>6.1f}")

    print(f"\n{'='*70}\n")
    return all_results


def main():
    parser = argparse.ArgumentParser(description="Design Review Environment Benchmark")
    parser.add_argument("--episodes", type=int, default=12, help="Total episodes to run")
    parser.add_argument("--seed", type=int, default=100, help="Base random seed")
    args = parser.parse_args()

    run_benchmark(episodes=args.episodes, base_seed=args.seed)


if __name__ == "__main__":
    main()
