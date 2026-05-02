from __future__ import annotations

from ai_hall.pipeline.types import VerificationLabel, VerifierOutput


def combine_verdicts(outputs: dict[str, VerifierOutput]) -> VerifierOutput:
    """
    Conservative combiner:
    - any strong CONTRADICT dominates
    - else if strong ENTAIL and no contradict => ENTAIL
    - else UNKNOWN
    """
    if not outputs:
        return VerifierOutput(
            label=VerificationLabel.UNKNOWN,
            confidence=0.0,
            rationale="No verifier outputs available",
            cited_evidence_ids=[],
            failure_mode="NO_VERIFIER",
        )

    contradict = [o for o in outputs.values() if o.label == VerificationLabel.CONTRADICT]
    entail = [o for o in outputs.values() if o.label == VerificationLabel.ENTAIL]

    if contradict:
        best = max(contradict, key=lambda o: o.confidence)
        return VerifierOutput(
            label=VerificationLabel.CONTRADICT,
            confidence=min(1.0, 0.7 + 0.3 * best.confidence),
            rationale=best.rationale or "Contradicted by verifier ensemble",
            cited_evidence_ids=best.cited_evidence_ids,
            failure_mode=best.failure_mode or "CONTRADICTED",
            diagnostics={"combined_from": list(outputs.keys())},
        )

    if entail:
        best = max(entail, key=lambda o: o.confidence)
        if best.confidence >= 0.6:
            return VerifierOutput(
                label=VerificationLabel.ENTAIL,
                confidence=min(1.0, 0.6 + 0.4 * best.confidence),
                rationale=best.rationale or "Supported by verifier ensemble",
                cited_evidence_ids=best.cited_evidence_ids,
                failure_mode=None,
                diagnostics={"combined_from": list(outputs.keys())},
            )

    best_any = max(outputs.values(), key=lambda o: o.confidence)
    return VerifierOutput(
        label=VerificationLabel.UNKNOWN,
        confidence=min(0.8, best_any.confidence),
        rationale=best_any.rationale or "Insufficient evidence to decide",
        cited_evidence_ids=best_any.cited_evidence_ids,
        failure_mode=best_any.failure_mode or "INSUFFICIENT_EVIDENCE",
        diagnostics={"combined_from": list(outputs.keys())},
    )

