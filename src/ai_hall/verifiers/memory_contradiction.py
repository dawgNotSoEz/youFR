from __future__ import annotations

from ai_hall.pipeline.types import Claim, EvidenceSet, VerificationLabel, VerifierOutput


class VerifiedMemoryContradictionVerifier:
    """
    If the claim contradicts previously verified facts, immediately flag CONTRADICT.
    Wraps existing `services/verifier/memory_consistency.py`.
    """

    name = "verified_memory"

    def __init__(self):
        from ai_hall.memory.verified_memory import load_verified_facts

        self._verified_facts = load_verified_facts()

    def verify(self, claim: Claim, evidence: EvidenceSet) -> VerifierOutput:
        from ai_hall.memory.verified_memory import check_memory_contradiction

        memory_result = check_memory_contradiction(claim.text, self._verified_facts)
        if memory_result:
            return VerifierOutput(
                label=VerificationLabel.CONTRADICT,
                confidence=1.0,
                rationale=str(memory_result.get("reason", "Contradicts verified memory")).strip(),
                cited_evidence_ids=[],
                failure_mode="MEMORY_CONTRADICTION",
                diagnostics={"memory": memory_result},
            )

        return VerifierOutput(
            label=VerificationLabel.UNKNOWN,
            confidence=0.0,
            rationale="No contradiction found in verified memory",
            cited_evidence_ids=[],
            failure_mode="NO_MEMORY_SIGNAL",
            diagnostics={},
        )

