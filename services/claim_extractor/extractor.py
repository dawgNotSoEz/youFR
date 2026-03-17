import spacy


nlp = spacy.load("en_core_web_sm")

JUNK_PATTERNS = (
    "short answer",
    "answer:",
    "details",
    "explanation",
    "in summary",
)


CLAIM_TYPES = {
    "FACTUAL": "Declarative factual sentence that can be verified.",
    "ENTITY": "Entity mention without a standalone factual assertion.",
    "FRAGMENT": "Incomplete phrase/header/broken sentence.",
    "OPINION": "Subjective statement not suitable for factual verification.",
}


def _clean_line(line: str) -> str:
    return line.strip().replace("- ", "").replace("• ", "").replace("\t", " ")


def _has_verb(doc) -> bool:
    return any(token.pos_ in {"VERB", "AUX"} for token in doc)


def _classify_claim(line: str) -> str:
    lower = line.lower().strip()

    if not lower:
        return "FRAGMENT"

    if any(pattern in lower for pattern in JUNK_PATTERNS):
        return "FRAGMENT"

    if line.endswith(":"):
        return "FRAGMENT"

    if "." not in line:
        return "FRAGMENT"

    doc = nlp(line)
    alpha_tokens = [token for token in doc if token.is_alpha]

    if len(alpha_tokens) <= 2:
        return "ENTITY"

    if not _has_verb(doc):
        return "FRAGMENT"

    has_subject = any(token.dep_ in {"nsubj", "nsubjpass", "expl"} for token in doc)
    if not has_subject:
        return "FRAGMENT"

    if lower.startswith(("i think", "in my opinion", "maybe", "probably")):
        return "OPINION"

    return "FACTUAL"


def extract_claims_with_metadata(text: str) -> dict:
    claims = []
    notes = []
    typed_claims = []

    for raw_line in text.splitlines():
        base_line = _clean_line(raw_line)
        if not base_line:
            continue

        line_doc = nlp(base_line)

        for sent in line_doc.sents:
            line = _clean_line(sent.text)

            if not line or len(line) < 25:
                continue

            claim = line if line.endswith((".", "!", "?")) else f"{line}."

            claim_type = _classify_claim(claim)
            typed_claims.append({"claim": claim, "type": claim_type})

            if claim_type == "FACTUAL":
                claims.append(claim)
            else:
                notes.append(f"Non-claim fragment ignored: '{claim}'")

    return {
        "claims": claims,
        "typed_claims": typed_claims,
        "notes": notes,
    }


def extract_claims(text: str):
    return extract_claims_with_metadata(text)["claims"]