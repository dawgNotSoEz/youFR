from __future__ import annotations

from functools import lru_cache

from ai_hall.pipeline.types import Claim, EvidenceSet, VerificationLabel, VerifierOutput


@lru_cache(maxsize=1)
def _load_nli_pipeline():
    """
    Lazy-load an NLI model. If unavailable (no internet / no weights), returns None.
    """
    try:
        from transformers import pipeline

        # Strong default that is commonly available; users can swap later.
        return pipeline("text-classification", model="MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli")
    except Exception:
        return None


class NLIVerifier:
    name = "nli"

    def verify(self, claim: Claim, evidence: EvidenceSet) -> VerifierOutput:
        import os

        if os.getenv("AI_HALL_ENABLE_NLI", "").strip() not in {"1", "true", "TRUE", "yes"}:
            return VerifierOutput(
                label=VerificationLabel.UNKNOWN,
                confidence=0.0,
                rationale="NLI verifier disabled (set AI_HALL_ENABLE_NLI=1 to enable)",
                cited_evidence_ids=[],
                failure_mode="NLI_DISABLED",
            )

        nli = _load_nli_pipeline()
        if nli is None or not evidence.items:
            return VerifierOutput(
                label=VerificationLabel.UNKNOWN,
                confidence=0.0,
                rationale="NLI verifier unavailable or no evidence",
                cited_evidence_ids=[],
                failure_mode="NLI_UNAVAILABLE",
            )

        # Premise = evidence snippet, hypothesis = claim
        best = None
        for it in evidence.items[:5]:
            try:
                out = nli({"text": it.snippet, "text_pair": claim.text}, top_k=None)
            except Exception:
                continue
            # transformers returns list of dicts with label/score
            if isinstance(out, list):
                # pick max score label
                cand = max(out, key=lambda x: float(x.get("score", 0.0)))
            elif isinstance(out, dict):
                cand = out
            else:
                continue
            score = float(cand.get("score", 0.0))
            label = str(cand.get("label", "")).upper()
            if best is None or score > best[0]:
                best = (score, label, it.evidence_id)

        if best is None:
            return VerifierOutput(
                label=VerificationLabel.UNKNOWN,
                confidence=0.0,
                rationale="NLI verifier failed to score evidence",
                cited_evidence_ids=[],
                failure_mode="NLI_FAILED",
            )

        score, label, evid = best
        if "ENTAIL" in label:
            vlabel = VerificationLabel.ENTAIL
        elif "CONTRAD" in label or "REFUTE" in label:
            vlabel = VerificationLabel.CONTRADICT
        else:
            vlabel = VerificationLabel.UNKNOWN

        cited = [evid] if vlabel != VerificationLabel.UNKNOWN else []
        return VerifierOutput(
            label=vlabel,
            confidence=max(0.0, min(1.0, score)),
            rationale="NLI-based verdict from top evidence snippet",
            cited_evidence_ids=cited,
            failure_mode=None if vlabel != VerificationLabel.UNKNOWN else "INSUFFICIENT_EVIDENCE",
            diagnostics={"nli_label": label, "score": score},
        )

