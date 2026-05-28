import os
from typing import Optional

import openai

from .base import SpecProvider, SpecGenerationResult, SYSTEM_PROMPTS


class OpenAIProvider(SpecProvider):

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.client = openai.OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
        )

    def generate_spec(
        self,
        source_code: str,
        language: str,
        model: Optional[str] = None,
    ) -> SpecGenerationResult:
        model = model or "gpt-4o"
        system = SYSTEM_PROMPTS.get(language)
        if system is None:
            raise ValueError(f"No prompt template for language: {language}")

        response = self.client.chat.completions.create(
            model=model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": source_code},
            ],
        )

        text = response.choices[0].message.content
        from .claude import _extract_code_block
        annotated = _extract_code_block(text, language)

        return SpecGenerationResult(
            annotated_source=annotated,
            raw_response=text,
            model=model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
