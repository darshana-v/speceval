from .base import Verifier, VerificationResult
from .openjml import OpenJMLVerifier
from .framac import FramaCVerifier
from .prusti import PrustiVerifier
from .smtchecker import SMTCheckerVerifier

VERIFIERS = {
    "java": OpenJMLVerifier,
    "c": FramaCVerifier,
    "rust": PrustiVerifier,
    "solidity": SMTCheckerVerifier,
}


def create_verifier(language: str, **kwargs) -> Verifier:
    if language not in VERIFIERS:
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Choose from {list(VERIFIERS.keys())}"
        )
    return VERIFIERS[language](**kwargs)
