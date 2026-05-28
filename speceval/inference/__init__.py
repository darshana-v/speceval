from .base import SpecProvider, SpecGenerationResult
from .claude import ClaudeProvider
from .openai_provider import OpenAIProvider

PROVIDERS = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
}


def create_provider(name: str, **kwargs) -> SpecProvider:
    if name not in PROVIDERS:
        raise ValueError(
            f"Unknown provider: {name}. Choose from {list(PROVIDERS.keys())}"
        )
    return PROVIDERS[name](**kwargs)
