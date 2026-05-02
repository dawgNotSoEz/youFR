from __future__ import annotations

import re

from ai_hall.pipeline.types import (
    Claim,
    EvidenceSet,
    HallucinationFinding,
    HallucinationScore,
    HallucinationType,
    VerificationLabel,
    VerificationResult,
)


CONFIDENT_TERMS = re.compile(r"\b(always|never|definitely|certainly|undoubtedly|proven|guaranteed|all|none)\b", re.I)
ATTRIBUTION_TERMS = re.compile(r"\b(invented|discovered|founded|wrote|said|claimed|according to|by)\b", re.I)


def detect_hallucination(
    claim: Claim,
    evidence: EvidenceSet,
    verification: VerificationResult,
    score: HallucinationScore,
) -> HallucinationFinding:
    signals = list(score.reasons)
    combined = verification.combined
    detected = score.p_hallucination >= 0.45
    htype = HallucinationType.NONE

    if combined.label == VerificationLabel.CONTRADICT:
        htype = HallucinationType.CONTRADICTION
        signals.append("Trusted verifier reported contradiction.")
    elif not evidence.items:
        htype = HallucinationType.FABRICATION
        signals.append("No supporting source was found.")
    elif combined.label == VerificationLabel.UNKNOWN and CONFIDENT_TERMS.search(claim.text):
        htype = HallucinationType.OVERCONFIDENCE
        signals.append("Claim uses confident wording despite weak evidence.")
    elif combined.label == VerificationLabel.UNKNOWN and ATTRIBUTION_TERMS.search(claim.text):
        htype = HallucinationType.MISATTRIBUTION
        signals.append("Attribution-style claim could not be verified.")
    elif combined.label == VerificationLabel.UNKNOWN:
        htype = HallucinationType.UNSUPPORTED_EXTRAPOLATION
        signals.append("Claim goes beyond available evidence.")

    if not detected:
        return HallucinationFinding(
            claim_id=claim.claim_id,
            hallucination_detected=False,
            type=HallucinationType.NONE,
            rationale="Claim has sufficient support for the configured risk threshold.",
            signals=signals,
        )

    return HallucinationFinding(
        claim_id=claim.claim_id,
        hallucination_detected=True,
        type=htype,
        rationale=f"Risk={score.p_hallucination:.2f}; uncertainty={score.uncertainty:.2f}; verifier={combined.label.value}.",
        signals=signals,
    )
