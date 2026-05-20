from __future__ import annotations

import json
import requests
from ai_hall.pipeline.types import Claim, EvidenceSet, VerificationLabel, VerifierOutput
from ai_hall.config import get_settings


def _normalize_status(value: str) -> str:
    upper = (value or "").strip().upper()
    if upper in {"TRUE", "FALSE", "UNCERTAIN"}:
        return upper
    return "UNCERTAIN"


def _clamp_confidence(value) -> float:
    try:
        confidence = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(confidence, 1.0))


class LocalPhi3Verifier:
    """
    Uses the Ollama-based local verifier (claim-only).
    This is NOT evidence-grounded; we treat it as a weak offline signal.
    """

    name = "local_phi3"
    _ollama_available: bool | None = None

    def verify(self, claim: Claim, evidence: EvidenceSet) -> VerifierOutput:
        settings = get_settings()
        ollama_url = getattr(settings, "ollama_url", "http://localhost:11434")
        url = f"{ollama_url.rstrip('/')}/api/generate"

        # Check connection once and cache the status
        if LocalPhi3Verifier._ollama_available is None:
            try:
                resp = requests.get(ollama_url.rstrip("/"), timeout=0.3)
                LocalPhi3Verifier._ollama_available = (resp.status_code == 200)
            except Exception:
                LocalPhi3Verifier._ollama_available = False

        if not LocalPhi3Verifier._ollama_available:
            res = {
                "status": "UNCERTAIN",
                "confidence": 0.0,
                "reason": "Local verifier (Ollama) is offline or unavailable.",
            }
        else:
            prompt = f"""
You are a strict factual verifier.

Rules:
- Return ONLY JSON
- No explanation outside JSON
- Be conservative

Task:
Verify the claim.

Claim: {claim.text}

Output format:
{{
  "status": "TRUE" or "FALSE" or "UNCERTAIN",
  "confidence": float (0 to 1),
  "reason": "short reason"
}}
"""
            try:
                response = requests.post(
                    url,
                    json={
                        "model": "phi3",
                        "prompt": prompt.strip(),
                        "stream": False
                    },
                    timeout=5,
                )
                response.raise_for_status()
                text = response.json().get("response", "")
                
                start = text.find("{")
                end = text.rfind("}") + 1
                parsed = json.loads(text[start:end])
                status = _normalize_status(parsed.get("status", "UNCERTAIN"))
                confidence = _clamp_confidence(parsed.get("confidence", 0.0))
                reason = str(parsed.get("reason", "no reason provided")).strip() or "no reason provided"
                
                res = {
                    "status": status,
                    "confidence": confidence,
                    "reason": reason
                }
            except Exception as exc:
                res = {
                    "status": "UNCERTAIN",
                    "confidence": 0.0,
                    "reason": f"Local verifier unavailable ({exc})",
                }

        status = res["status"].upper()
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
