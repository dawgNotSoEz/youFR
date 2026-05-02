from __future__ import annotations

from ai_hall.pipeline.types import Claim, EvidenceSet, VerificationResult
from ai_hall.verifiers.combiner import combine_verdicts


class VerifierEnsemble:
    def __init__(self, verifiers: list[object]):
        self.verifiers = verifiers

    def verify(self, claim: Claim, evidence: EvidenceSet) -> VerificationResult:
        outputs = {}
        for v in self.verifiers:
            name = getattr(v, "name", v.__class__.__name__)
            try:
                outputs[name] = v.verify(claim, evidence)
            except Exception as e:
                from ai_hall.pipeline.types import VerificationLabel, VerifierOutput

                outputs[name] = VerifierOutput(
                    label=VerificationLabel.UNKNOWN,
                    confidence=0.0,
                    rationale=f"Verifier error: {e.__class__.__name__}",
                    cited_evidence_ids=[],
                    failure_mode="VERIFIER_ERROR",
                    diagnostics={"error": str(e)},
                )

        combined = combine_verdicts(outputs)
        return VerificationResult(claim_id=claim.claim_id, outputs=outputs, combined=combined)

