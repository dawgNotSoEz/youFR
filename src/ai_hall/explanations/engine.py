from __future__ import annotations

from ai_hall.pipeline.types import (
    Claim,
    EvidenceSet,
    Explanation,
    HallucinationScore,
    VerificationLabel,
    VerificationResult,
)


def explain_claim(
    claim: Claim, evidence: EvidenceSet, verification: VerificationResult, score: HallucinationScore
) -> Explanation:
    v = verification.combined

    if v.label == VerificationLabel.CONTRADICT:
        failure_mode = v.failure_mode or "CONTRADICTED"
        text = "This statement is unreliable because source conflict was detected and retrieved evidence contradicts the claim."
    elif v.label == VerificationLabel.UNKNOWN:
        failure_mode = v.failure_mode or "INSUFFICIENT_EVIDENCE"
        text = "This statement is unreliable because confidence is low and no strong supporting evidence was found."
    else:
        failure_mode = "SUPPORTED"
        text = "This claim appears supported by retrieved evidence."

    if v.rationale:
        text = f"{text} Verifier rationale: {v.rationale}"
    if score.reasons:
        text = f"{text} Risk signals: {'; '.join(score.reasons[:4])}."

    citations = v.cited_evidence_ids[:]
    return Explanation(
        claim_id=claim.claim_id,
        failure_mode=failure_mode,
        explanation_text=text,
        citations=citations,
    )

