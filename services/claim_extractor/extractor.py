import spacy


nlp = spacy.load("en_core_web_sm")


CLAIM_TYPES = {
    "FACTUAL": "Declarative factual sentence that can be verified.",
    "ENTITY": "Entity mention without a standalone factual assertion.",
    "FRAGMENT": "Incomplete phrase/header/broken sentence.",
    "OPINION": "Subjective statement not suitable for factual verification.",
}


def _clean_line(line: str) -> str:
    return line.strip().replace("- ", "").replace("• ", "")


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


def _resolve_pronoun_prefix(sentence: str, last_entity: str | None) -> str:
    if not last_entity:
        return sentence

    words = sentence.split()
    if not words:
        return sentence

    first = words[0].lower().strip(" ,:;-")
    if first in {"he", "she", "his", "her"}:
        words[0] = last_entity
        return " ".join(words)

    return sentence


def extract_claims_with_metadata(text: str) -> dict:
    doc = nlp(text)

    claims = []
    notes = []
    typed_claims = []

    last_entity = None

    for sent in doc.sents:
        sentence_people = [ent.text for ent in sent.ents if ent.label_ == "PERSON"]

        line = _clean_line(sent.text)

        if not line or len(line) < 25:
            if sentence_people:
                last_entity = sentence_people[0]
            continue

        resolved = _resolve_pronoun_prefix(line, last_entity)
        claim = resolved if resolved.endswith(".") else f"{resolved}."

        claim_type = _classify_claim(claim)
        typed_claims.append({"claim": claim, "type": claim_type})

        if claim_type == "FACTUAL":
            claims.append(claim)
        else:
            notes.append(f"Non-claim fragment ignored: '{claim}'")

        if sentence_people:
            last_entity = sentence_people[0]

    return {
        "claims": claims,
        "typed_claims": typed_claims,
        "notes": notes,
    }


def extract_claims(text: str):
    return extract_claims_with_metadata(text)["claims"]