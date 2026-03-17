import re


CLAIM_TYPES = {
    "FACTUAL": "Declarative, verifiable factual claim.",
    "ENTITY": "Entity-only mention without a verifiable fact.",
    "FRAGMENT": "Incomplete sentence, header, or formatting fragment.",
    "OPINION": "Subjective/opinion statement.",
}


def _clean_line(line: str) -> str:
    cleaned = line.strip()
    for prefix in ("- ", "• ", "* ", "1. ", "2. ", "3. ", "4. ", "5. "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


def _classify_claim(line: str) -> str:
    lower = line.lower().strip()

    if not lower:
        return "FRAGMENT"

    if lower.startswith(("short answer", "details", "answer:", "summary:")):
        return "FRAGMENT"

    if line.endswith(":"):
        return "FRAGMENT"

    if "." not in line:
        return "FRAGMENT"

    tokens = [token for token in line.replace(".", "").split() if token]
    if len(tokens) <= 2:
        return "ENTITY"

    if lower.startswith(("i think", "in my opinion", "maybe", "probably")):
        return "OPINION"

    return "FACTUAL"


def extract_claims_with_metadata(text: str) -> dict:
    claims = []
    notes = []
    typed_claims = []

    for raw_line in text.split("\n"):
        line = _clean_line(raw_line)

        if not line:
            continue

        sentence_candidates = re.split(r"(?<=[.!?])\s+", line)
        for candidate in sentence_candidates:
            candidate = candidate.strip()
            if not candidate:
                continue

            claim_type = _classify_claim(candidate)
            typed_claims.append({"claim": candidate, "type": claim_type})

            if claim_type == "FACTUAL":
                claims.append(candidate)
            elif claim_type in {"FRAGMENT", "ENTITY", "OPINION"}:
                notes.append(f"Non-claim fragment ignored: '{candidate}'")

    return {
        "claims": claims,
        "typed_claims": typed_claims,
        "notes": notes,
    }


def extract_claims(text: str):
    return extract_claims_with_metadata(text)["claims"]