import os
import json
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from models.schemas import ClaimResult


def _load_groq_api_key() -> str:
    env_path = Path(__file__).resolve().parents[2] / "configs" / "api_keys.env"
    load_dotenv(env_path)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment or configs/api_keys.env")
    return api_key


def _get_client() -> Groq:
    return Groq(api_key=_load_groq_api_key())


def _normalize_status(value: str) -> str:
    upper = (value or "").strip().upper()
    if upper in {"TRUE", "FALSE", "UNCERTAIN"}:
        return upper
    return "UNCERTAIN"


def _clamp_confidence(value) -> float:
    try:
        confidence = float(value)
    except Exception:
        return 0.5
    confidence = max(0.0, min(confidence, 1.0))
    return confidence


def _parse_verifier_output(claim: str, raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if not text:
        return ClaimResult(
            claim=claim,
            status="UNCERTAIN",
            confidence=0.0,
            reason="Invalid verifier response format",
        ).to_dict()

    try:
        payload = json.loads(text)
        status = _normalize_status(payload.get("status", "UNCERTAIN"))
        confidence = _clamp_confidence(payload.get("confidence", 0.5))
        reason = str(payload.get("reason", "no reason provided")).strip()
        return ClaimResult(
            claim=claim,
            status=status.upper(),
            confidence=confidence,
            reason=reason or "no reason provided",
        ).to_dict()
    except Exception:
        return ClaimResult(
            claim=claim,
            status="UNCERTAIN",
            confidence=0.0,
            reason="Invalid verifier response format",
        ).to_dict()


def verify_claim_llm_only(claim: str) -> dict:
    if not claim or not claim.strip():
        return ClaimResult(
            claim=claim,
            status="UNCERTAIN",
            confidence=0.0,
            reason="claim is empty",
        ).to_dict()

    system_prompt = (
        "You are a factual verifier for claims.\n"
        "Use only the claim text and internal reasoning; no external tools are available.\n"
        "If the claim cannot be confidently validated or contradicted from general knowledge, return UNCERTAIN.\n"
        "Respond ONLY in JSON:\n"
        "{\n"
        "\"status\": \"TRUE | FALSE | UNCERTAIN\",\n"
        "\"confidence\": float (0 to 1),\n"
        "\"reason\": \"short explanation\"\n"
        "}"
    )
    user_prompt = f"Claim: {claim}"

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )
    except Exception as exc:
        return ClaimResult(
            claim=claim,
            status="UNCERTAIN",
            confidence=0.0,
            reason=f"verifier request failed ({exc})",
        ).to_dict()

    content = response.choices[0].message.content
    print(f"[verifier-v1] claim: {claim}")
    print(f"[verifier-v1] raw_response: {content}")
    return _parse_verifier_output(claim, content)


def verify_claim(claim: str, evidence: str = None) -> dict:
    if not claim or not claim.strip():
        return ClaimResult(
            claim=claim,
            status="UNCERTAIN",
            confidence=0.0,
            reason="claim is empty",
        ).to_dict()

    evidence_text = (evidence or "").strip()
    print(f"[verifier] claim: {claim}")
    print(f"[verifier] evidence_snippet: {evidence_text[:200]}")

    if not evidence_text or len(evidence_text) < 20:
        return ClaimResult(
            claim=claim,
            status="UNCERTAIN",
            confidence=0.0,
            reason="No sufficient evidence provided",
        ).to_dict()

    system_prompt = (
        "You are a strict factual verifier.\n"
        "Use ONLY the provided evidence.\n"
        "Do NOT use prior knowledge.\n"
        "If the evidence does not clearly support the claim, return UNCERTAIN.\n"
        "Respond ONLY in JSON:\n"
        "{\n"
        "\"status\": \"TRUE | FALSE | UNCERTAIN\",\n"
        "\"confidence\": float (0 to 1),\n"
        "\"reason\": \"short explanation referencing evidence\"\n"
        "}"
    )
    user_prompt = f"Claim: {claim}\nEvidence: {evidence_text}"

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )
    except Exception as exc:
        return ClaimResult(
            claim=claim,
            status="UNCERTAIN",
            confidence=0.0,
            reason=f"verifier request failed ({exc})",
        ).to_dict()

    content = response.choices[0].message.content
    print(f"[verifier] raw_response: {content}")
    return _parse_verifier_output(claim, content)


if __name__ == "__main__":
    user_claim = input("Enter a claim to verify: ").strip()
    result = verify_claim(user_claim)
    print(result)