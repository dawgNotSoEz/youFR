from __future__ import annotations

from pydantic import BaseModel, Field

from ai_hall.pipeline.types import PipelineRun


class AdversarialCase(BaseModel):
    category: str
    prompt: str


class AdversarialRun(BaseModel):
    cases: list[AdversarialCase]
    reports: list[PipelineRun] = Field(default_factory=list)
    aggregate_risk: float = 0.0


def build_adversarial_cases(seed_query: str, *, domain: str | None = None) -> list[AdversarialCase]:
    prefix = f"In the {domain} domain, " if domain else ""
    return [
        AdversarialCase(category="ambiguous_prompt", prompt=f"{prefix}answer this ambiguously worded question and include dates: {seed_query}"),
        AdversarialCase(category="trap_question", prompt=f"{prefix}if the premise is false, say so: {seed_query}"),
        AdversarialCase(category="conflicting_facts", prompt=f"{prefix}compare two conflicting versions of this fact and identify the reliable one: {seed_query}"),
    ]


def run_adversarial_suite(seed_query: str, run_fn, *, domain: str | None = None) -> AdversarialRun:
    cases = build_adversarial_cases(seed_query, domain=domain)
    reports = [run_fn(case.prompt, domain=domain) for case in cases]
    aggregate = sum(100 - r.summary.overall_reliability for r in reports) / max(1, len(reports))
    return AdversarialRun(cases=cases, reports=reports, aggregate_risk=round(aggregate, 2))
