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

    # Base risk from verifier label.
    if combined.label == VerificationLabel.CONTRADICT:
        p = 0.9
        reasons.append("Verifier indicates contradiction with evidence")
    elif combined.label == VerificationLabel.UNKNOWN:
        p = 0.6
        reasons.append("Verifier indicates insufficient evidence / unknown")
    else:
        p = 0.15
        reasons.append("Verifier indicates support from evidence")

    # Evidence coverage heuristic.
    if not evidence.items:
        p = max(p, 0.75)
        reasons.append("No evidence retrieved")

    # Claim type risk prior.
    if claim.claim_type.value in {"NUMERIC", "QUOTE"}:
        p = min(1.0, p + 0.1)
        reasons.append(f"Higher-risk claim type: {claim.claim_type.value}")

    # Confidence adjustment.
    p = max(0.0, min(1.0, p + (0.3 * (1.0 - combined.confidence) - 0.1)))

    if p >= 0.75:
        severity = "high"
    elif p >= 0.45:
        severity = "medium"
    else:
        severity = "low"

    # Uncertainty: high when UNKNOWN or low confidence.
    uncertainty = 0.7 if combined.label == VerificationLabel.UNKNOWN else 0.4
    uncertainty = max(0.0, min(1.0, uncertainty + (0.3 * (1.0 - combined.confidence))))

    return HallucinationScore(
        claim_id=claim.claim_id,
        p_hallucination=float(p),
        severity=severity,
        reasons=reasons,
        uncertainty=float(uncertainty),
    )

