from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VerificationStatus(Enum):
    VERIFIED = "verified"
    FAILED = "failed"
    COMPILE_ERROR = "compile_error"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"


@dataclass
class VerificationResult:
    status: VerificationStatus
    error_count: int
    raw_output: str
    spec_path: str
    duration_seconds: Optional[float] = None


class Verifier(ABC):

    @abstractmethod
    def verify(
        self,
        spec_path: str,
        timeout: int = 1800,
        basedir: str = "",
    ) -> VerificationResult:
        pass

    @abstractmethod
    def clean_up(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_up()
        return False
