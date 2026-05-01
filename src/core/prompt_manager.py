import os
from pathlib import Path
from typing import Optional


class PromptManager:
    """
    Manages the construction of system prompts using domain instructions.
    RULES.md is excluded to prioritize domain-specific behavior.
    """

    def __init__(self):
        self.root_path = Path(__file__).parent.parent.parent
        self.system_prompt_path = (
            self.root_path / "src" / "prompts" / "system_prompt.md"
        )

        # Smart Cache state
        self._cache_content: Optional[str] = None
        self._last_mtime_system: float = 0

    def get_system_prompt(self) -> str:
        """
        Returns the prompt from system_prompt.md. Re-reads only if changed.
        """
        try:
            # Check modification time
            mtime_system = os.path.getmtime(self.system_prompt_path)

            # Use cache if file hasn't changed
            if self._cache_content and mtime_system == self._last_mtime_system:
                return self._cache_content

            # Read Domain instructions
            with open(self.system_prompt_path, "r", encoding="utf-8") as f:
                domain_instructions = f.read()

            # Update cache state
            self._cache_content = domain_instructions
            self._last_mtime_system = mtime_system

            return domain_instructions

        except Exception:
            # Fallback
            return "You are a real estate expert specialized in the Spanish market."


# Singleton instance
prompt_manager = PromptManager()
