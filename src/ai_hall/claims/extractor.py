from __future__ import annotations

import re
from typing import Iterable

from ai_hall.pipeline.types import Claim, ClaimType, TextSpan
from ai_hall.utils.hashing import stable_hash

# Try loading spaCy but support graceful fallback if import or load fails (e.g. Python 3.14 incompatibilities)
try:
    import spacy
    try:
        _nlp = spacy.load("en_core_web_sm")
    except BaseException:
        # Fallback: basic English pipeline for sentence splitting.
        _nlp = spacy.blank("en")
        if "sentencizer" not in _nlp.pipe_names:
            _nlp.add_pipe("sentencizer")
except BaseException:
    _nlp = None


JUNK_PATTERNS = (
    "short answer",
    "answer:",
    "details",
    "explanation",
    "in summary",
)


def _clean_line(line: str) -> str:
    return line.strip().replace("- ", "").replace("• ", "").replace("\t", " ")


def _has_verb(doc) -> bool:
    return any(token.pos_ in {"VERB", "AUX"} for token in doc)


def _is_opinion(line: str) -> bool:
    lower = (line or "").lower().strip()
    return lower.startswith(("i think", "in my opinion", "maybe", "probably"))


def _claim_type_heuristic(text: str) -> ClaimType:
    t = (text or "").lower()
    if re.search(r"\b\d+(\.\d+)?\b", t):
        return ClaimType.NUMERIC
    if '"' in t or "“" in t or "”" in t:
        return ClaimType.QUOTE
    if re.search(r"\bis defined as\b|\bmeans\b", t):
        return ClaimType.DEFINITION
    if re.search(r"\bcauses\b|\bleads to\b|\bresults in\b", t):
        return ClaimType.CAUSAL
    if re.search(r"\bmore than\b|\bless than\b|\bcompared to\b", t):
        return ClaimType.COMPARISON
    return ClaimType.FACTUAL


def extract_claims(answer_text: str) -> list[Claim]:
    claims: list[Claim] = []
    seen: set[str] = set()

    offset = 0
    for raw_line in (answer_text or "").splitlines():
        base = _clean_line(raw_line)
        if not base:
            offset += len(raw_line) + 1
            continue

        if _nlp is not None:
            try:
                doc = _nlp(base)
                sents = [sent.text for sent in doc.sents]
            except Exception:
                sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', base) if s.strip()]
        else:
            # Premium pure-Python sentence splitter fallback
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', base) if s.strip()]

        for sent_text in sents:
            s = _clean_line(sent_text)
            if not s or len(s) < 20:
                continue
            lower = s.lower()
            if any(p in lower for p in JUNK_PATTERNS):
                continue
            if _is_opinion(s):
                continue

            if _nlp is not None:
                try:
                    sdoc = _nlp(s)
                    has_syntax = any(p in _nlp.pipe_names for p in ("tagger", "parser"))
                    if has_syntax:
                        # Require verb and a subject-like token for factuality.
                        if not _has_verb(sdoc):
                            continue
                        has_subject = any(tok.dep_ in {"nsubj", "nsubjpass", "expl"} for tok in sdoc)
                        if not has_subject:
                            continue

                    entities = [ent.text for ent in getattr(sdoc, "ents", [])][:10]
                except Exception:
                    # Inner fallback if document parsing fails
                    entities = list(set(re.findall(r'\b[A-Z][a-zA-Z0-9-]+\b', s)))[:10]
            else:
                # Premium pure-Python entity parser fallback (regex word capitalization matching)
                entities = list(set(re.findall(r'\b[A-Z][a-zA-Z0-9-]+\b', s)))[:10]

            claim_text = s if s.endswith((".", "!", "?")) else f"{s}."
            if claim_text in seen:
                continue
            seen.add(claim_text)

            ctype = _claim_type_heuristic(claim_text)
            claim_id = stable_hash({"claim": claim_text})

            claims.append(
                Claim(
                    claim_id=claim_id,
                    text=claim_text,
                    span=None,
                    claim_type=ctype,
                    entities=entities,
                    normalized=claim_text.strip(),
                    source_sentence_id=claim_id,
                )
            )

        offset += len(raw_line) + 1

    return claims


