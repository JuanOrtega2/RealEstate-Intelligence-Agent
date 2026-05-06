"""
Unified Evaluation Runner — Real Estate Intelligence Agent
============================================================
Runs ALL evaluation datasets (standard + stress) through the LLM Agent
and scores every response using the Judge.

Supports parallel execution with configurable concurrency.

Usage:
    python -m src.evals.eval_runner                     # Run ALL datasets
    python -m src.evals.eval_runner --dataset standard   # Only standard cases
    python -m src.evals.eval_runner --dataset stress     # Only stress cases
    python -m src.evals.eval_runner --workers 5          # 5 cases in parallel
    python -m src.evals.eval_runner --workers 1          # Sequential (safe mode)
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

# Automatically add the project root to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Fix Windows terminal encoding for unicode output
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.nvidia_client import nvidia_client  # noqa: E402
from src.core.prompt_manager import prompt_manager  # noqa: E402
from src.evals.judge import Judge  # noqa: E402

# ── Configuration ─────────────────────────────────────────────────────────
EVALS_DIR = os.path.dirname(__file__)
DATASETS = {
    "standard": os.path.join(EVALS_DIR, "dataset.json"),
    "stress": os.path.join(EVALS_DIR, "stress_dataset.json"),
}
RESULTS_FILE = os.path.join(EVALS_DIR, "results.json")

# Default parallel workers. NVIDIA NIM free tier tolerates ~3-5 concurrent
# requests before hitting 429. Adjust with --workers flag.
DEFAULT_WORKERS = 3


def load_datasets(filter_name: str | None = None) -> list[dict]:
    """Load and merge selected datasets. Returns a flat list of test cases."""
    all_cases = []
    targets = {filter_name: DATASETS[filter_name]} if filter_name else DATASETS

    for name, path in targets.items():
        if not os.path.exists(path):
            print(f"⚠️  Dataset '{name}' not found at {path} — skipping.")
            continue
        with open(path, "r", encoding="utf-8") as f:
            cases = json.load(f)
        # Tag each case with its source dataset
        for case in cases:
            case["_dataset"] = name
        all_cases.extend(cases)
        print(f"📂 Loaded {len(cases)} cases from '{name}' ({os.path.basename(path)})")

    return all_cases


# ── Single case evaluation ────────────────────────────────────────────────


async def evaluate_case(
    case: dict,
    index: int,
    total: int,
    judge: Judge,
    system_prompt: str,
    semaphore: asyncio.Semaphore,
    print_lock: asyncio.Lock,
) -> dict:
    """Evaluate a single case (Agent call + Judge scoring), respecting concurrency."""
    dataset_tag = case.get("_dataset", "unknown")
    case_id = case.get("id", index)
    scenario = case.get("scenario", "Unnamed")
    user_input = case["user_input"]
    expected = case["expected_behavior"]

    max_retries = 3
    async with semaphore:
        for attempt in range(max_retries):
            try:
                # ── 1. Get Agent response (blocking → offload to thread) ──
                agent_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ]

                agent_response_raw = await nvidia_client.achat_completion(
                    agent_messages,
                    stream=False,
                )
                agent_response = agent_response_raw["choices"][0]["message"]["content"]

                # ── 2. Judge evaluation ──
                eval_result = await judge.evaluate(user_input, agent_response, expected)

                score = eval_result.get("score", 0)
                violated = eval_result.get("golden_rule_violated", False)
                reasoning = eval_result.get("reasoning", "No reasoning provided")

                if score >= 8:
                    icon = "✅"
                elif score >= 5:
                    icon = "⚠️"
                else:
                    icon = "❌"

                # Thread-safe print
                async with print_lock:
                    print(
                        f"[{index:02d}/{total}] [{dataset_tag.upper():>8}] {scenario}"
                    )
                    print(
                        f"   💬 Agent: {agent_response[:120].replace(chr(10), ' ')}..."
                    )
                    status = "VIOLATED" if violated else "OK"
                    print(f"   {icon} Score: {score}/10 | Golden Rule: {status}")
                    print(f"   📝 {reasoning[:150]}")
                    print("-" * 60)

                return {
                    "case_id": case_id,
                    "dataset": dataset_tag,
                    "scenario": scenario,
                    "user_input": user_input,
                    "expected_behavior": expected,
                    "agent_response": agent_response,
                    "evaluation": eval_result,
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg and attempt < max_retries - 1:
                    async with print_lock:
                        print(
                            f"⚠️  [{index:02d}] Rate limit hit (429). "
                            f"Esperando 60s antes de reintentar "
                            f"({attempt + 1}/{max_retries})..."
                        )
                    await asyncio.sleep(60)
                    continue

                async with print_lock:
                    print(
                        f"[{index:02d}/{total}] [{dataset_tag.upper():>8}] {scenario}"
                    )
                    print(f"   💥 Error: {e}")
                    print("-" * 60)

                return {
                    "case_id": case_id,
                    "dataset": dataset_tag,
                    "scenario": scenario,
                    "user_input": user_input,
                    "expected_behavior": expected,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }


# ── Main runner ───────────────────────────────────────────────────────────


async def run_evaluations(
    filter_name: str | None = None,
    max_workers: int = DEFAULT_WORKERS,
):
    test_cases = load_datasets(filter_name)
    if not test_cases:
        print("❌ No test cases loaded. Exiting.")
        return

    judge = Judge()
    system_prompt = prompt_manager.get_system_prompt()
    total = len(test_cases)

    semaphore = asyncio.Semaphore(max_workers)
    print_lock = asyncio.Lock()

    mode = "PARALLEL" if max_workers > 1 else "SEQUENTIAL"
    print(f"\n🚀 Running {total} cases — {mode} (workers: {max_workers})\n")
    print("=" * 60)

    start_time = time.perf_counter()

    # ── Launch all cases concurrently (bounded by semaphore) ──
    tasks = [
        evaluate_case(case, i, total, judge, system_prompt, semaphore, print_lock)
        for i, case in enumerate(test_cases, 1)
    ]
    results = await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start_time

    # ── Save results ──────────────────────────────────────────────────────
    # Sort by case_id to keep output deterministic regardless of finish order
    results = sorted(results, key=lambda r: r.get("case_id", 0))

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ── Summary statistics ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📊 EVALUATION SUMMARY")
    print("=" * 60)

    valid = [r for r in results if "evaluation" in r]
    errors = [r for r in results if "error" in r]

    if valid:
        scores = [r["evaluation"]["score"] for r in valid]
        avg_score = sum(scores) / len(scores)
        violations = sum(
            1 for r in valid if r["evaluation"].get("golden_rule_violated")
        )
        high = sum(1 for s in scores if s >= 8)
        mid = sum(1 for s in scores if 5 <= s < 8)
        low = sum(1 for s in scores if s < 5)

        print(f"  Total cases:          {total}")
        print(f"  Evaluated:            {len(valid)}")
        print(f"  Errors:               {len(errors)}")
        print(f"  Average Score:        {avg_score:.1f}/10")
        print(f"  Golden Rule Violated: {violations}")
        print(f"  ✅ High (8-10):       {high}")
        print(f"  ⚠️  Mid (5-7):        {mid}")
        print(f"  ❌ Low (1-4):         {low}")
        print(
            f"  ⏱️  Elapsed:          {elapsed:.1f}s ({elapsed / total:.1f}s/case avg)"
        )

        # Per-dataset breakdown
        for ds_name in DATASETS:
            ds_results = [r for r in valid if r.get("dataset") == ds_name]
            if ds_results:
                ds_avg = sum(r["evaluation"]["score"] for r in ds_results) / len(
                    ds_results
                )
                ds_violations = sum(
                    1 for r in ds_results if r["evaluation"].get("golden_rule_violated")
                )
                print(
                    f"\n  [{ds_name.upper()}] {len(ds_results)} cases — "
                    f"Avg: {ds_avg:.1f}/10 — Violations: {ds_violations}"
                )
    else:
        print("  No valid results to calculate statistics.")

    print(f"\n💾 Full report saved to {RESULTS_FILE}")
    print("=" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────


def _parse_arg(flag: str, default=None):
    """Parse a --flag value from sys.argv."""
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


if __name__ == "__main__":
    ds_filter = _parse_arg("--dataset")
    if ds_filter and ds_filter not in DATASETS:
        print(f"❌ Unknown dataset '{ds_filter}'. Available: {list(DATASETS.keys())}")
        sys.exit(1)

    workers_str = _parse_arg("--workers", str(DEFAULT_WORKERS))
    try:
        workers = max(1, int(workers_str))
    except ValueError:
        print(f"❌ --workers must be an integer, got '{workers_str}'")
        sys.exit(1)

    asyncio.run(run_evaluations(ds_filter, workers))
