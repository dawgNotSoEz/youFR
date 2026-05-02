from __future__ import annotations

from typing import Literal

from ai_hall.pipeline.types import PipelineRun


def export_report(run: PipelineRun, *, format: Literal["json", "markdown"] = "json") -> str:
    if format == "json":
        return run.model_dump_json(indent=2)

    lines = [
        f"# AI Hall Trust Report",
        "",
        f"- Run ID: `{run.run_id}`",
        f"- Query: {run.request.query}",
        f"- Model: {run.generation.model or 'unknown'} via {run.generation.provider or 'unknown'}",
        f"- Overall reliability: {run.summary.overall_reliability}/100",
        f"- Risk level: {run.summary.risk_level}",
        f"- Claims verified: {run.summary.claims_verified}",
        f"- Claims failed: {run.summary.claims_failed}",
        "",
        "## Claim Analysis",
    ]
    for analysis in run.analyses:
        lines.extend(
            [
                "",
                f"### {analysis.claim.text}",
                f"- State: {analysis.verification.state.value}",
                f"- Confidence: {analysis.confidence}/100",
                f"- Hallucination: {analysis.hallucination.type.value if analysis.hallucination else 'none'}",
                f"- Explanation: {analysis.explanation.explanation_text if analysis.explanation else 'No explanation available.'}",
            ]
        )
        for item in analysis.evidence.items[:3]:
            source = item.uri or item.title or item.evidence_id
            lines.append(f"- Evidence: {source} ({item.quality_score:.2f})")
    return "\n".join(lines)
