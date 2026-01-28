from __future__ import annotations
from abc import ABC, abstractmethod
from ..types import EvalCase


# =============================================================================
# Base Grader
# =============================================================================

class Grader(ABC):
    
    @abstractmethod
    def grade(self, output: str, case: EvalCase) -> tuple[bool, float, str]:
        pass
