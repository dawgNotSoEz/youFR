import requests
import json

def verify_local(claim: str):

    prompt = f"""Verify the following claim.

Respond ONLY in JSON:
{{
  "status": "TRUE | FALSE | UNCERTAIN",
  "confidence": 0 to 1,
  "reason": "short explanation"
}}

Claim: {claim}
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "phi3",
            "prompt": prompt,
            "stream": False
        }
    )

    text = response.json()["response"]

    # Try parsing JSON
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        parsed = json.loads(text[start:end])
        return parsed
    except:
        return {
            "status": "UNCERTAIN",
            "confidence": 0.0,
            "reason": "Parsing failed",
            "raw": text
        }