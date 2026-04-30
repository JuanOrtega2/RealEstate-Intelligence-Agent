from pathlib import Path


class PromptManager:
    """
    Manages the construction of system prompts by combining engineering
    rules (RULES.md) and domain instructions (system_prompt.md).
    """

    def __init__(self):
        self.root_path = Path(__file__).parent.parent.parent
        self.rules_path = self.root_path / "RULES.md"
        self.system_prompt_path = (
            self.root_path / "src" / "prompts" / "system_prompt.md"
        )
        self._system_prompt_cache = None

    def get_system_prompt(self) -> str:
        """
        Reads and combines instruction files to create the final prompt.
        Uses a cache to avoid redundant disk reads.
        """
        if self._system_prompt_cache:
            return self._system_prompt_cache

        try:
            # 1. Read Project/Engineering rules
            with open(self.rules_path, "r", encoding="utf-8") as f:
                engineering_rules = f.read()

            # 2. Read Real Estate Agent instructions
            with open(self.system_prompt_path, "r", encoding="utf-8") as f:
                domain_instructions = f.read()

            # 3. Assemble
            full_prompt = (
                f"{domain_instructions}\n\n"
                f"--- EXECUTION RULES & PROJECT PHILOSOPHY ---\n"
                f"{engineering_rules}\n"
                f"--- END OF RULES ---\n\n"
                f"IMPORTANT: As an AI agent for this project, you must apply these "
                f"rules in your responses: be direct, prioritize technical precision, "
                f"and avoid verbosity."
            )

            self._system_prompt_cache = full_prompt
            return full_prompt

        except FileNotFoundError:
            # Simple fallback if any file is missing
            return "You are a real estate expert. Be precise and professional."


# Singleton instance for project-wide use
prompt_manager = PromptManager()
