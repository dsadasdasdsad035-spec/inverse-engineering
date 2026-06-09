"""Self-eval: rule-based scoring + MiniMax LLM fallback."""
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.llm_router import eval_llm, eval_llm_batch

from .term_filter import scan as term_scan


@dataclass
class EvalResult:
    tech_agnostic_score: float
    completeness_score: float
    uml_coverage_score: float

    def passes(self) -> bool:
        return (
            self.tech_agnostic_score >= 1.0
            and self.completeness_score >= 0.8
            and self.uml_coverage_score >= 0.9
        )

    def failing_dimensions(self) -> list[str]:
        dims = []
        if self.tech_agnostic_score < 1.0:
            dims.append("tech_agnostic")
        if self.completeness_score < 0.8:
            dims.append("completeness")
        if self.uml_coverage_score < 0.9:
            dims.append("uml_coverage")
        return dims


def evaluate(srs_text: str, fr_list: list, route_count: int,
             uml_generated: int, uml_expected: int,
             llm_call=None) -> EvalResult:
    # Rule: tech agnostic — confirm ambiguous hits via MiniMax (batch)
    violations = term_scan(srs_text)
    if violations:
        _eval_batch = getattr(llm_call, "eval_llm_batch", None) or eval_llm_batch
        prompts = [f"Is '{t}' a tech term in this context? Answer yes/no only:\n{srs_text[:500]}" for t in violations]
        results = _eval_batch(prompts)
        violations = [
            t for t, res in zip(violations, results)
            if res.strip().lower().startswith("yes")
        ]
        tech_score = 0.0 if violations else 1.0
    else:
        tech_score = 1.0

    # Rule: completeness = meaningful (non-technical) FR count / 10
    _TECH = re.compile(
        r'\b(class|method|function|interface|service|repository|controller|impl|bean|dto|vo|po|dao)\b',
        re.IGNORECASE
    )
    meaningful = [f for f in fr_list
                  if not _TECH.search(f.get("description", ""))
                  and len(f.get("description", "")) > 5]
    completeness = min(len(meaningful) / 10, 1.0)

    # Rule: UML coverage
    uml_cov = (uml_generated / uml_expected) if uml_expected > 0 else 1.0

    return EvalResult(
        tech_agnostic_score=tech_score,
        completeness_score=completeness,
        uml_coverage_score=min(uml_cov, 1.0),
    )
