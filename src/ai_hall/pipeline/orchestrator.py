from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Callable

from ai_hall.detection import detect_hallucination
from ai_hall.domains import get_domain_policy
from ai_hall.memory.failures import FailureMemory
from ai_hall.pipeline.types import (
    Claim,
    ClaimAnalysis,
    Correction,
    EvidenceSet,
    Explanation,
    HallucinationScore,
    LLMGeneration,
    PipelineRun,
    QueryRequest,
    TrustReport,
    VerificationLabel,
    VerificationState,
)
from ai_hall.retrievers.ranking import rank_evidence
from ai_hall.utils.hashing import stable_hash


class StageTimings(dict):
    pass


def _now_ms() -> int:
    return int(time.time() * 1000)


def _verification_state(label: VerificationLabel, confidence: float, evidence: EvidenceSet) -> VerificationState:
    if label == VerificationLabel.ENTAIL:
        return VerificationState.TRUE if confidence >= 0.65 else VerificationState.PARTIALLY_TRUE
    if label == VerificationLabel.CONTRADICT:
        return VerificationState.FALSE
    if any(item.quality_score >= 0.75 for item in evidence.items) and confidence < 0.35:
        return VerificationState.CONFLICTING_EVIDENCE
    return VerificationState.INSUFFICIENT_EVIDENCE


def _claim_confidence(evidence: EvidenceSet, verification_result: object, score: HallucinationScore) -> int:
    combined = verification_result.combined
    source_quality = max((item.quality_score or item.credibility for item in evidence.items), default=0.0)
    source_count = min(1.0, len(evidence.items) / 3)
    verifier_conf = float(combined.confidence or 0.0)
    risk_inverse = 1.0 - score.p_hallucination
    value = (0.34 * source_quality) + (0.26 * verifier_conf) + (0.18 * source_count) + (0.22 * risk_inverse)
    return int(round(max(0.0, min(1.0, value)) * 100))


def _risk_level(reliability: int, high: int, policy_floor: str) -> str:
    if high >= 2 or reliability < 35:
        return "CRITICAL"
    if high >= 1 or reliability < 60 or policy_floor == "HIGH":
        return "HIGH"
    if reliability < 80 or policy_floor == "MEDIUM":
        return "MEDIUM"
    return "LOW"


def run_explain_pipeline(
    request: QueryRequest,
    *,
    generate_fn: Callable[[QueryRequest], LLMGeneration],
    extract_claims_fn: Callable[[str], list[Claim]],
    retrieve_fn: Callable[[Claim], EvidenceSet],
    verify_fn: Callable[[Claim, EvidenceSet], tuple[dict[str, object], object]],
    score_fn: Callable[[Claim, EvidenceSet, object], HallucinationScore],
    explain_fn: Callable[[Claim, EvidenceSet, object, HallucinationScore], Explanation],
    correct_fn: Callable[[QueryRequest, LLMGeneration, list[ClaimAnalysis]], str | None],
) -> PipelineRun:
    run_id = str(uuid.uuid4())
    policy = get_domain_policy(request.domain)
    trace: dict[str, object] = {
        "run_id": run_id,
        "started_at_ms": _now_ms(),
        "timings_ms": StageTimings(),
        "domain_policy": asdict(policy),
    }

    t0 = _now_ms()
    generation = generate_fn(request)
    trace["timings_ms"]["generate"] = _now_ms() - t0

    t1 = _now_ms()
    claims = extract_claims_fn(generation.answer_text)
    trace["timings_ms"]["extract_claims"] = _now_ms() - t1

    analyses: list[ClaimAnalysis] = []
    for claim in claims:
        t_r = _now_ms()
        evidence = retrieve_fn(claim)
        evidence = rank_evidence(evidence, domain=request.domain)
        trace.setdefault("timings_ms_per_claim", {}).setdefault(claim.claim_id, {})["retrieve"] = _now_ms() - t_r

        t_v = _now_ms()
        outputs_by_name, combined = verify_fn(claim, evidence)
        combined.state = _verification_state(combined.combined.label, combined.combined.confidence, evidence)
        combined.source_urls = [item.uri for item in evidence.items if item.uri]
        combined.checked_at = datetime.now(timezone.utc).isoformat()
        trace.setdefault("timings_ms_per_claim", {}).setdefault(claim.claim_id, {})["verify"] = _now_ms() - t_v

        t_s = _now_ms()
        score = score_fn(claim, evidence, combined)
        confidence = _claim_confidence(evidence, combined, score)
        if confidence < policy.minimum_confidence and combined.combined.label != VerificationLabel.ENTAIL:
            score.reasons.append(f"Below {policy.name} domain confidence threshold ({policy.minimum_confidence}).")
        trace.setdefault("timings_ms_per_claim", {}).setdefault(claim.claim_id, {})["score"] = _now_ms() - t_s

        t_e = _now_ms()
        explanation = explain_fn(claim, evidence, combined, score)
        finding = detect_hallucination(claim, evidence, combined, score)
        if explanation:
            top = evidence.items[0] if evidence.items else None
            explanation.confidence_reasoning = (
                f"Confidence {confidence}/100 from source quality, agreement, semantic verification, and uncertainty. "
                f"Top evidence: {top.rank_reason if top else 'none'}."
            )
            if finding.hallucination_detected and top:
                explanation.suggested_correction = f"Rewrite conservatively using evidence from {top.title or top.uri or top.evidence_id}."
        trace.setdefault("timings_ms_per_claim", {}).setdefault(claim.claim_id, {})["explain"] = _now_ms() - t_e

        analyses.append(
            ClaimAnalysis(
                claim=claim,
                evidence=evidence,
                verification=combined,
                score=score,
                confidence=confidence,
                hallucination=finding,
                explanation=explanation,
                correction=None,
            )
        )

    corrected_answer = correct_fn(request, generation, analyses)

    # Summary: hard gate passes only if no claim is high-risk hallucination and all are entailed.
    total = len(analyses)
    high = sum(1 for a in analyses if a.score.p_hallucination >= 0.7)
    medium = sum(1 for a in analyses if 0.4 <= a.score.p_hallucination < 0.7)
    verified = sum(1 for a in analyses if a.verification.state == VerificationState.TRUE)
    failed = sum(1 for a in analyses if a.verification.state in {VerificationState.FALSE, VerificationState.CONFLICTING_EVIDENCE})
    reliability = int(round(sum(a.confidence for a in analyses) / total)) if total else 0
    learnings = FailureMemory().record(request.query, analyses)

    if total == 0:
        hallucination = True
        hard_gate_passed = False
        reason = "No verifiable claims were extracted; output is not trustworthy"
        error_type = "CLAIM_EXTRACTION_ERROR"
    else:
        hallucination = high > 0
        hard_gate_passed = (not hallucination) and high == 0 and medium == 0 and reliability >= policy.minimum_confidence
        reason = (
            "All claims appear supported by retrieved evidence"
            if hard_gate_passed
            else "One or more claims are unsupported, contradicted, or below the domain confidence threshold"
        )
        error_type = "VALID" if hard_gate_passed else "FACTUAL_ERROR"

    summary = TrustReport(
        hallucination=hallucination,
        hard_gate_passed=hard_gate_passed,
        reason=reason,
        error_type=error_type,
        overall_reliability=reliability,
        claims_verified=verified,
        claims_failed=failed,
        risk_level=_risk_level(reliability, high, policy.risk_floor),
        metrics={
            "total_claims": total,
            "high_risk_claims": high,
            "medium_risk_claims": medium,
            "minimum_domain_confidence": policy.minimum_confidence,
        },
        learnings=learnings,
    )

    trace["ended_at_ms"] = _now_ms()
    trace["timings_ms"]["total"] = trace["ended_at_ms"] - trace["started_at_ms"]
    trace["config_hash"] = stable_hash({"version": "0.1.0"})

    return PipelineRun(
        run_id=run_id,
        request=request,
        generation=generation,
        claims=claims,
        analyses=analyses,
        corrected_answer=corrected_answer,
        summary=summary,
        trace=trace,
    )

