import os
from typing import Optional

import anthropic

from .base import SpecProvider, SpecGenerationResult, SYSTEM_PROMPTS


class ClaudeProvider(SpecProvider):

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )

    def generate_spec(
        self,
        source_code: str,
        language: str,
        model: Optional[str] = None,
    ) -> SpecGenerationResult:
        model = model or "claude-sonnet-4-6"
        system = SYSTEM_PROMPTS.get(language)
        if system is None:
            raise ValueError(f"No prompt template for language: {language}")

        response = self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": source_code}],
        )

        text = response.content[0].text
        annotated = _extract_code_block(text, language)

        return SpecGenerationResult(
            annotated_source=annotated,
            raw_response=text,
            model=model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )


def _extract_code_block(text: str, language: str) -> str:
    """Extract code from markdown fences if present, otherwise return as-is."""
    import re
    lang_aliases = {
        "java": r"java",
        "c": r"c",
        "rust": r"rust|rs",
        "solidity": r"solidity|sol",
    }
    alias = lang_aliases.get(language, language)
    pattern = rf"```(?:{alias})?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()
