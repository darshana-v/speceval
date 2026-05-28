from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SpecGenerationResult:
    annotated_source: str
    raw_response: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


SYSTEM_PROMPTS = {
    "java": (
        "You are a formal verification expert. Given Java source code, "
        "add JML annotations (requires, ensures, invariant, assignable) "
        "that fully specify the method's behavior. Return ONLY the annotated "
        "Java source code, no explanation."
    ),
    "c": (
        "You are a formal verification expert. Given C source code, "
        "add ACSL annotations (requires, ensures, loop invariant, assigns) "
        "that fully specify the function's behavior. Return ONLY the annotated "
        "C source code, no explanation."
    ),
    "rust": (
        "You are a formal verification expert. Given Rust source code, "
        "add Prusti annotations (#[requires(...)], #[ensures(...)]) using "
        "prusti_contracts. Return ONLY the annotated Rust source code, no explanation."
    ),
    "solidity": (
        "You are a formal verification expert. Given Solidity source code, "
        "add require() preconditions and assert() postconditions that fully "
        "specify the contract's behavior for SMTChecker verification. "
        "Return ONLY the annotated Solidity source code, no explanation."
    ),
}


class SpecProvider(ABC):

    @abstractmethod
    def generate_spec(
        self,
        source_code: str,
        language: str,
        model: Optional[str] = None,
    ) -> SpecGenerationResult:
        pass
