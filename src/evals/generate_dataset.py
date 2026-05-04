import asyncio
import json
import os
import sys

# Añadir la raíz del proyecto al PYTHONPATH automáticamente
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.nvidia_client import nvidia_client  # noqa: E402

SYSTEM_GEN_PROMPT = """
You are an expert QA Engineer specialized in Real Estate AI Agents.
Your task is to generate a diverse set of test cases for a Real Estate Investment Agent.

The agent follows 5 Pillars:
1. Property Info (Price/CCAA)
2. Mortgage Setup (Cash/Mortgage)
3. Rental Info
4. Annual Expenses
5. Financing Details

GOLDEN RULE: The agent MUST NOT assume or invent data unless the user explicitly
asks for estimates. If the agent assumes a cost without being told, it is a
critical failure.

Generate a JSON list of test cases. Each case must have:
- 'id': incremental integer.
- 'scenario': description of what we are testing.
- 'user_input': the message the user sends.
- 'expected_behavior': what the agent should do.

Create 10 diverse cases:
- Cases with only a price.
- Cases with a price and a city.
- Cases where the user says "Calculate with estimates".
- Cases where the user provides partial data and expects a full report.
- Cases with cash payment vs mortgage.

Return ONLY the JSON list.
"""


async def generate_dataset():
    print("Generating synthetic dataset using NVIDIA NIM...")
    messages = [
        {"role": "system", "content": SYSTEM_GEN_PROMPT},
        {"role": "user", "content": "Generate 10 diverse test cases in JSON format."},
    ]

    response_gen = nvidia_client.chat_completion(messages, stream=False)
    content = response_gen["choices"][0]["message"]["content"]

    # Clean possible markdown blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        dataset = json.loads(content)
        with open("src/evals/dataset.json", "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Dataset generated with {len(dataset)} cases in src/evals/dataset.json")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw content: {content}")


if __name__ == "__main__":
    asyncio.run(generate_dataset())
