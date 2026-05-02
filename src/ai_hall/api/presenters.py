from __future__ import annotations

from ai_hall.api.models import VerifiedClaim, VerifyResponse
from ai_hall.pipeline.types import ClaimAnalysis, PipelineRun


def _evidence_payload(analysis: ClaimAnalysis) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for item in analysis.evidence.items[:3]:
        payload.append(
            {
                "title": item.title,
                "url": item.uri,
                "snippet": item.snippet,
                "quality_score": item.quality_score,
                "source_type": item.source_type,
            }
        )
    return payload


def to_verify_response(run: PipelineRun) -> VerifyResponse:
    claims = [
        VerifiedClaim(
            text=analysis.claim.text.rstrip("."),
            status=analysis.verification.state.value,
            confidence=analysis.confidence,
            hallucination_type=(
                analysis.hallucination.type.value
                if analysis.hallucination and analysis.hallucination.type.value != "none"
                else "verified"
            ),
            explanation=analysis.explanation.explanation_text if analysis.explanation else run.summary.reason,
            suggested_correction=(
                analysis.explanation.suggested_correction
                if analysis.explanation and analysis.explanation.suggested_correction
                else (analysis.correction.corrected_text if analysis.correction else None)
            ),
            supporting_evidence=_evidence_payload(analysis),
            source_urls=analysis.verification.source_urls,
        )
        for analysis in run.analyses
    ]
    return VerifyResponse(
        request_id=run.run_id,
        overall_score=run.summary.overall_reliability,
        risk_level=run.summary.risk_level,
        model_used=run.generation.model,
        latency_ms=run.generation.latency_ms,
        claims=claims,
        corrected_text=run.corrected_answer,
        trace={
            "reason": run.summary.reason,
            "error_type": run.summary.error_type,
            "learnings": run.summary.learnings,
        },
    )
