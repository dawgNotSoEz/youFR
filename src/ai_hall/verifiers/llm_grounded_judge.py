from __future__ import annotations

import json

from ai_hall.llm.clients.base import LLMClient
from ai_hall.pipeline.types import Claim, EvidenceSet, VerificationLabel, VerifierOutput


def _normalize_label(v: str) -> VerificationLabel:
    up = (v or "").strip().upper()
    if up in {"ENTAIL", "SUPPORTED", "SUPPORT"}:
        return VerificationLabel.ENTAIL
    if up in {"CONTRADICT", "REFUTE", "REFUTED", "CONTRADICTION"}:
        return VerificationLabel.CONTRADICT
    return VerificationLabel.UNKNOWN


class LLMGroundedJudgeVerifier:
    name = "llm_grounded_judge"

    def __init__(self, llm: LLMClient, *, model: str | None = None):
        self.llm = llm
        self.model = model

    def verify(self, claim: Claim, evidence: EvidenceSet) -> VerifierOutput:
        evidence_block = "\n\n".join(
            [f"[{it.evidence_id}] {it.title or it.uri or it.source_type}\n{it.snippet}" for it in evidence.items[:6]]
        )

        prompt = f"""
You are a strict claim verifier operating in EVIDENCE-ONLY mode.

Rules:
- Use ONLY the evidence provided. If evidence is insufficient, output UNKNOWN.
- Return ONLY valid JSON (no markdown).
- If label is ENTAIL or CONTRADICT, you MUST cite at least one evidence_id from the provided evidence.

Claim: {claim.text}

Evidence:
{evidence_block}

Output JSON schema:
{{
  "label": "ENTAIL|CONTRADICT|UNKNOWN",
  "confidence": 0.0-1.0,
  "rationale": "1-2 sentences, must reference evidence content",
  "cited_evidence_ids": ["..."],
  "failure_mode": "INSUFFICIENT_EVIDENCE|CONTRADICTED|IRRELEVANT_EVIDENCE|AMBIGUOUS_CLAIM|OTHER"
}}
""".strip()

        try:
            text = self.llm.judge(prompt, model=self.model)
        except Exception:
            text = ""
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            parsed = json.loads(text[start:end])
            label = _normalize_label(str(parsed.get("label", "UNKNOWN")))
            confidence = float(parsed.get("confidence", 0.0))
            confidence = max(0.0, min(confidence, 1.0))
            cited = parsed.get("cited_evidence_ids", []) or []
            if not isinstance(cited, list):
                cited = []
            cited = [str(x) for x in cited if str(x)]

            if label in {VerificationLabel.ENTAIL, VerificationLabel.CONTRADICT} and not cited:
                label = VerificationLabel.UNKNOWN
                confidence = 0.0

            return VerifierOutput(
                label=label,
                confidence=confidence,
                rationale=str(parsed.get("rationale", "")).strip() or None,
                cited_evidence_ids=cited,
                failure_mode=str(parsed.get("failure_mode", "")).strip() or None,
                diagnostics={"raw": parsed},
            )
        except Exception:
            return VerifierOutput(
                label=VerificationLabel.UNKNOWN,
                confidence=0.0,
                rationale="LLM judge parsing failed",
                cited_evidence_ids=[],
                failure_mode="PARSING_FAILED",
                diagnostics={"raw_text": text},
            )

