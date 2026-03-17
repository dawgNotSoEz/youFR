import re


STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "is",
    "are",
    "was",
    "were",
    "be",
    "by",
    "from",
    "that",
    "this",
    "it",
    "as",
    "at",
}


def _extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]+", (text or "").lower())
    keywords = [token for token in tokens if len(token) >= 4 and token not in STOPWORDS]
    if keywords:
        return list(dict.fromkeys(keywords))
    fallback = [token for token in tokens if len(token) >= 3 and token not in STOPWORDS]
    return list(dict.fromkeys(fallback))


def is_evidence_relevant(claim: str, evidence: str) -> bool:
    claim_keywords = _extract_keywords(claim)
    if not claim_keywords:
        return False

    evidence_text = (evidence or "").lower()
    if not evidence_text.strip():
        return False

    matches = 0
    for keyword in claim_keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", evidence_text):
            matches += 1

    threshold = 2 if len(claim_keywords) >= 4 else 1
    return matches >= threshold