from __future__ import annotations
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

from .types import EvalCase, EvalResult, EvalSummary
from .evaluator import Evaluator
from .graders import Grader


# =============================================================================
# Eval Runner
# =============================================================================

class EvalRunner:
    
    def __init__(
        self,
        name: str,
        agent: Any,
        grader: Optional[Grader] = None,
        parallel: bool = False,
        max_concurrent: int = 5,
    ):
        self.name = name
        self.agent = agent
        self.grader = grader
        self.parallel = parallel
        self.max_concurrent = max_concurrent
        self.cases: List[EvalCase] = []
    
    # -------------------------------------------------------------------------
    # Case Management
    # -------------------------------------------------------------------------

    def add_case(self, input: str, expected: Any, name: Optional[str] = None, **metadata) -> "EvalRunner":
        self.cases.append(EvalCase(input=input, expected=expected, name=name, metadata=metadata))
        return self
    
    def add_cases(self, cases: List[EvalCase]) -> "EvalRunner":
        self.cases.extend(cases)
        return self
    
    # -------------------------------------------------------------------------
    # Factory Methods
    # -------------------------------------------------------------------------

    @classmethod
    def from_json(cls, name: str, agent: Any, path: Union[str, Path], grader: Optional[Grader] = None) -> "EvalRunner":
        path = Path(path)
        data = json.loads(path.read_text())
        runner = cls(name, agent, grader)
        for item in data:
            runner.add_case(
                input=item["input"],
                expected=item["expected"],
                name=item.get("name"),
                **item.get("metadata", {}),
            )
        return runner
    
    @classmethod
    def from_list(cls, name: str, agent: Any, cases: List[dict], grader: Optional[Grader] = None) -> "EvalRunner":
        runner = cls(name, agent, grader)
        for item in cases:
            runner.add_case(
                input=item["input"],
                expected=item["expected"],
                name=item.get("name"),
                **item.get("metadata", {}),
            )
        return runner
    
    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    async def run(self) -> EvalSummary:
        evaluator = Evaluator(self.agent, grader=self.grader)
        if self.parallel:
            results = await self._run_parallel(evaluator)
        else:
            results = await self._run_sequential(evaluator)
        return EvalSummary(name=self.name, results=results)
    
    async def _run_sequential(self, evaluator: Evaluator) -> List[EvalResult]:
        results = []
        for i, case in enumerate(self.cases):
            print(f"Running case {i+1}/{len(self.cases)}: {case.name}")
            result = await evaluator.run_case(case)
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            print(f"  {status} Score: {result.score:.2f} | {result.reason[:50]}")
        return results
    
    async def _run_parallel(self, evaluator: Evaluator) -> List[EvalResult]:
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def run_with_limit(case: EvalCase) -> EvalResult:
            async with semaphore:
                return await evaluator.run_case(case)
        
        tasks = [run_with_limit(case) for case in self.cases]
        return list(await asyncio.gather(*tasks))
    
    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save_results(self, summary: EvalSummary, path: Optional[Union[str, Path]] = None) -> str:
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = Path(f"eval_results_{self.name}_{timestamp}.json")
        else:
            path = Path(path)
        path.write_text(json.dumps(summary.to_dict(), indent=2))
        print(f"Results saved to: {path}")
        return str(path)
