from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


# =============================================================================
# Tool Call
# =============================================================================

@dataclass
class ToolCall:
    name: str
    input_parameters: Dict[str, Any] = field(default_factory=dict)
    output: Optional[Any] = None
    description: Optional[str] = None
    
    def matches(self, other: "ToolCall", check_params: bool = False) -> bool:
        if self.name != other.name:
            return False
        if check_params and self.input_parameters != other.input_parameters:
            return False
        return True


# =============================================================================
# Reasoning Step
# =============================================================================

@dataclass
class ReasoningStep:
    thought: str
    action: Optional[str] = None
    observation: Optional[str] = None


# =============================================================================
# Eval Case
# =============================================================================

@dataclass
class EvalCase:
    input: str
    expected: Any
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Enhanced fields for new graders
    expected_tools: Optional[List[str]] = None
    expected_sources: Optional[List[str]] = None
    known_facts: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.name is None:
            self.name = self.input[:50] + "..." if len(self.input) > 50 else self.input
        # Copy enhanced fields to metadata for grader access
        if self.expected_tools:
            self.metadata["expected_tools"] = self.expected_tools
        if self.expected_sources:
            self.metadata["expected_sources"] = self.expected_sources
        if self.known_facts:
            self.metadata["known_facts"] = self.known_facts


# =============================================================================
# Eval Result
# =============================================================================

@dataclass
class EvalResult:
    case: EvalCase
    output: Optional[str]
    passed: bool
    score: float = 1.0
    reason: str = ""
    latency_ms: float = 0.0
    trace: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    grader_type: str = "custom"
    # Enhanced fields for detailed results
    grader_breakdown: Optional[Dict[str, Dict[str, Any]]] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    tools_used: Optional[List[str]] = None
    sources_cited: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.case.name,
            "input": self.case.input,
            "expected": self.case.expected,
            "output": self.output,
            "passed": self.passed,
            "score": self.score,
            "reason": self.reason,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "grader_type": self.grader_type,
        }
        # Add enhanced fields if present
        if self.grader_breakdown:
            result["grader_breakdown"] = self.grader_breakdown
        if self.tokens_used is not None:
            result["tokens_used"] = self.tokens_used
        if self.cost_usd is not None:
            result["cost_usd"] = self.cost_usd
        if self.tools_used:
            result["tools_used"] = self.tools_used
        if self.sources_cited:
            result["sources_cited"] = self.sources_cited
        return result


# =============================================================================
# Eval Summary
# =============================================================================

@dataclass
class EvalSummary:
    name: str
    results: List[EvalResult]
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    avg_score: float = 0.0
    avg_latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        if self.results:
            self.total = len(self.results)
            self.passed = sum(1 for r in self.results if r.passed and not r.error)
            self.failed = sum(1 for r in self.results if not r.passed and not r.error)
            self.errors = sum(1 for r in self.results if r.error)
            self.avg_score = sum(r.score for r in self.results) / self.total
            self.avg_latency_ms = sum(r.latency_ms for r in self.results) / self.total
    
    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total) * 100 if self.total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "pass_rate": self.pass_rate,
            "avg_score": round(self.avg_score, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "results": [r.to_dict() for r in self.results],
            "total_cost_usd": 0.0, # Placeholder as backend doesn't calculate this yet
        }
    
    def print_summary(self) -> None:
        print(f"\n{'='*60}")
        print(f"Eval: {self.name}")
        print(f"{'='*60}")
        print(f"Total: {self.total} | Passed: {self.passed} | Failed: {self.failed} | Errors: {self.errors}")
        print(f"Pass Rate: {self.pass_rate:.1f}%")
        print(f"Avg Score: {self.avg_score:.3f}")
        print(f"Avg Latency: {self.avg_latency_ms:.2f}ms")
        print(f"{'='*60}\n")
        
        failed = [r for r in self.results if not r.passed]
        if failed:
            print("Failed Cases:")
            for r in failed:
                print(f"  - {r.case.name}")
                print(f"    Expected: {r.case.expected}")
                print(f"    Got: {r.output}")
                print(f"    Reason: {r.reason}")
                print()
