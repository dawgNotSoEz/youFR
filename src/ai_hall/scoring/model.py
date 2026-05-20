from __future__ import annotations

from ai_hall.pipeline.types import (
    Claim,
    EvidenceSet,
    HallucinationScore,
    VerificationLabel,
    VerificationResult,
)


def score_hallucination(claim: Claim, evidence: EvidenceSet, verification: VerificationResult) -> HallucinationScore:
    combined = verification.combined
    reasons: list[str] = []

    # Premium fail-soft scoring model
    # Only block if we have actual negative proof (CONTRADICT)
    if combined.label == VerificationLabel.CONTRADICT:
        p = 0.85
        reasons.append("Verifier detected direct contradiction with evidence")
    elif combined.label == VerificationLabel.UNKNOWN:
        # Check if the UNKNOWN label was due to a verifier being offline or unconfigured
        is_offline_failure = combined.failure_mode in {
            "NO_VERIFIER", "VERIFIER_ERROR", "UNGROUNDED_SIGNAL", "NLI_UNAVAILABLE", "NLI_DISABLED"
        }
        
        if is_offline_failure:
            p = 0.25  # Fail-soft: offline/unconfigured is not a hallucination
            reasons.append("Verifier offline or unconfigured; operating in fail-soft mode")
        elif not evidence.items:
            p = 0.60  # Medium risk if we literally retrieved absolutely zero evidence
            reasons.append("No evidence retrieved to support claim")
        else:
            p = 0.35  # Low-medium risk: we have evidence, but can't verify fully
            reasons.append("Insufficient evidence to confirm or deny claim")
    else:
        p = 0.10
        reasons.append("Verifier confirmed support from evidence")

    # Claim type risk prior adjustments
    if claim.claim_type.value in {"NUMERIC", "QUOTE"} and combined.label != VerificationLabel.ENTAIL:
        p = min(1.0, p + 0.1)
        reasons.append(f"Higher-risk claim type: {claim.claim_type.value}")

    # Confidence adjustment: scale risk slightly based on confidence
    # But do not blow up offline/fail-soft scores into high-risk range
    if combined.label == VerificationLabel.CONTRADICT:
        p = max(0.5, min(1.0, p + (0.15 * (1.0 - combined.confidence))))
    elif combined.label == VerificationLabel.UNKNOWN:
        p = max(0.0, min(0.65, p + (0.1 * (1.0 - combined.confidence))))
    else:
        p = max(0.0, min(0.35, p + (0.1 * (1.0 - combined.confidence))))

    if p >= 0.70:
        severity = "high"
    elif p >= 0.40:
        severity = "medium"
    else:
        severity = "low"

    # Uncertainty calculation
    uncertainty = 0.6 if combined.label == VerificationLabel.UNKNOWN else 0.3
    uncertainty = max(0.0, min(1.0, uncertainty + (0.2 * (1.0 - combined.confidence))))

    return HallucinationScore(
        claim_id=claim.claim_id,
        p_hallucination=float(p),
        severity=severity,
        reasons=reasons,
        uncertainty=float(uncertainty),
    )


