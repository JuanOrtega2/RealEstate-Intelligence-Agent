import json
import os
import sys
from typing import Any, Dict

# Automatically add the project root to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.nvidia_client import nvidia_client  # noqa: E402

JUDGE_SYSTEM_PROMPT = """
You are a Senior Quality Auditor for Real Estate Financial Systems.
Your goal is to evaluate the response of an AI Agent based on a specific user input
and expected behavior.

SCORING RUBRIC (1-10):
- 10: Perfect adherence to protocol. Asks for missing data or calculates
      only when authorized.
- 8-9: Very good, but tone could be slightly better.
- 5-7: Minor issues (e.g., asked for too many things at once, or
      didn't summarize well).
- 1-4: CRITICAL FAILURE (The Golden Rule violation).

GOLDEN RULE:
The agent MUST NOT assume costs or invent data (Price, Community Fees, IBI,
CCAA, etc.) unless the user explicitly says "estimate", "use standard values",
or similar. If the agent assumes a value without permission, you MUST assign
a score of 3 or lower.

Your output must be a JSON object:
{
  "score": <int>,
  "reasoning": "<brief explanation of the score>",
  "golden_rule_violated": <bool>
}
"""


class Judge:
    async def evaluate(
        self, user_input: str, agent_response: str, expected_behavior: str
    ) -> Dict[str, Any]:
        prompt = f"""
        TASK:
        User Input: {user_input}
        Expected Behavior: {expected_behavior}

        AGENT RESPONSE:
        {agent_response}

        Evaluate the AGENT RESPONSE based on the GOLDEN RULE and the EXPECTED BEHAVIOR.
        """

        messages = [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = await nvidia_client.achat_completion(messages, stream=False)
        content = response["choices"][0]["message"]["content"]

        # Clean possible markdown blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(content)
        except Exception as e:
            return {
                "score": 0,
                "reasoning": f"Failed to parse judge output: {e}. Raw: {content}",
                "golden_rule_violated": True,
            }
