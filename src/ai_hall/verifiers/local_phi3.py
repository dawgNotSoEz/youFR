from __future__ import annotations

from ai_hall.pipeline.types import Claim, EvidenceSet, VerificationLabel, VerifierOutput


class LocalPhi3Verifier:
    """
    Uses the existing Ollama-based local verifier (claim-only).
    This is NOT evidence-grounded; we treat it as a weak signal.
    """

    name = "local_phi3"

    def verify(self, claim: Claim, evidence: EvidenceSet) -> VerifierOutput:
        from services.verifier.local_verifier import verify_locally

        res = verify_locally(claim.text) or {}
        status = (res.get("status") or "UNCERTAIN").upper()
        if status == "TRUE":
            label = VerificationLabel.ENTAIL
        elif status == "FALSE":
            label = VerificationLabel.CONTRADICT
        else:
            label = VerificationLabel.UNKNOWN

        conf = float(res.get("confidence", 0.0) or 0.0)
        conf = max(0.0, min(conf, 1.0))

        return VerifierOutput(
            label=label,
            confidence=conf * 0.7,  # downweight because it's not grounded
            rationale=str(res.get("reason", "")).strip() or None,
            cited_evidence_ids=[],
            failure_mode=None if label != VerificationLabel.UNKNOWN else "UNGROUNDED_SIGNAL",
            diagnostics={"raw": res},
        )

