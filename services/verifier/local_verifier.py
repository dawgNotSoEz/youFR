import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"


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

def verify_locally(claim: str):

    prompt = f"""
You are a strict factual verifier.

Rules:
- Return ONLY JSON
- No explanation outside JSON
- Be conservative

Task:
Verify the claim.

Claim: {claim}

Output format:
{{
  "status": "TRUE" or "FALSE" or "UNCERTAIN",
  "confidence": float (0 to 1),
  "reason": "short reason"
}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=20,
        )
        response.raise_for_status()
        text = response.json().get("response", "")
    except Exception:
        return {
            "status": "UNCERTAIN",
            "confidence": 0.0,
            "reason": "Local verifier unavailable",
        }

    # Try parsing JSON
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        parsed = json.loads(text[start:end])
        return {
            "status": _normalize_status(parsed.get("status", "UNCERTAIN")),
            "confidence": _clamp_confidence(parsed.get("confidence", 0.0)),
            "reason": str(parsed.get("reason", "no reason provided")).strip() or "no reason provided",
        }
    except Exception:
        return {
            "status": "UNCERTAIN",
            "confidence": 0.0,
            "reason": "Parsing failed",
            "raw": text
        }


def verify_local(claim: str):
    return verify_locally(claim)