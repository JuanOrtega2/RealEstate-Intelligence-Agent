import asyncio
import json
import os
import sys

# Automatically add the project root to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.nvidia_client import nvidia_client  # noqa: E402
from src.core.prompt_manager import prompt_manager  # noqa: E402
from src.evals.judge import Judge  # noqa: E402


async def run_evaluations():
    print("Starting Evaluation Loop...")

    # 1. Load Dataset
    dataset_path = "src/evals/dataset.json"
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    judge = Judge()
    results = []

    # 2. Get the real System Prompt of the project
    system_prompt = prompt_manager.get_system_prompt()

    print(f"Running {len(test_cases)} test cases...")

    for case in test_cases:
        try:
            print(f"--- Case {case['id']}: {case['scenario']} ---")
            user_input = case["user_input"]

            # Simulate Agent Call
            agent_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]

            # We use stream=False for easier capture during evaluation
            agent_response_raw = nvidia_client.chat_completion(
                agent_messages, stream=False
            )
            agent_response = agent_response_raw["choices"][0]["message"]["content"]

            print(f"Agent Response: {agent_response[:100]}...")

            # Evaluate with Judge
            eval_result = await judge.evaluate(
                user_input, agent_response, case["expected_behavior"]
            )

            print(f"Score: {eval_result['score']}/10")
            print(f"Golden Rule Violated: {eval_result['golden_rule_violated']}")
            print(f"Reasoning: {eval_result['reasoning']}\n")

            results.append(
                {
                    "case_id": case["id"],
                    "scenario": case["scenario"],
                    "user_input": user_input,
                    "agent_response": agent_response,
                    "evaluation": eval_result,
                }
            )
        except Exception as e:
            print(f"Error processing case {case['id']}: {e}")
            results.append(
                {"case_id": case["id"], "scenario": case["scenario"], "error": str(e)}
            )

    # 3. Save Final Report
    with open("src/evals/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary Statistics
    valid_results = [r for r in results if "evaluation" in r]
    if valid_results:
        avg_score = sum(r["evaluation"]["score"] for r in valid_results) / len(
            valid_results
        )
        violations = sum(
            1 for r in valid_results if r["evaluation"]["golden_rule_violated"]
        )
        print(f"Average Score: {avg_score:.2f} / 10")
        print(f"Golden Rule Violations: {violations}")
    else:
        print("No valid results to calculate statistics.")
    print("Detailed report saved in src/evals/results.json")
    print("========================================")


if __name__ == "__main__":
    asyncio.run(run_evaluations())
