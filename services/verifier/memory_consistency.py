import json
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
VERIFIED_FACTS_PATH = ROOT_DIR / "memory" / "verified_facts.json"


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _negation_variant(text: str) -> str:
    normalized = _normalize_text(text)
    replacements = [
        (" is not ", " is "),
        (" are not ", " are "),
        (" was not ", " was "),
        (" were not ", " were "),
        (" cannot ", " can "),
        (" can't ", " can "),
        (" does not ", " does "),
        (" do not ", " do "),
    ]

    for old, new in replacements:
        if old in normalized:
            return normalized.replace(old, new)

    if " is " in normalized:
        return normalized.replace(" is ", " is not ", 1)
    if " are " in normalized:
        return normalized.replace(" are ", " are not ", 1)

    return normalized


def load_verified_facts(path: Path | None = None) -> list[dict]:
    facts_path = path or VERIFIED_FACTS_PATH
    if not facts_path.exists():
        return []

    try:
        data = json.loads(facts_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_verified_facts(facts: list[dict], path: Path | None = None) -> None:
    facts_path = path or VERIFIED_FACTS_PATH
    facts_path.parent.mkdir(parents=True, exist_ok=True)
    facts_path.write_text(json.dumps(facts, indent=2), encoding="utf-8")


def check_memory_contradiction(claim: str, facts: list[dict]) -> dict | None:
    normalized_claim = _normalize_text(claim)
    claim_negation = _negation_variant(normalized_claim)

    for fact in facts:
        if str(fact.get("status", "")).upper() != "TRUE":
            continue

        fact_claim = _normalize_text(str(fact.get("claim", "")))
        if not fact_claim:
            continue

        fact_negation = _negation_variant(fact_claim)

        if normalized_claim == fact_negation or claim_negation == fact_claim:
            return {
                "status": "FALSE",
                "confidence": 1.0,
                "reason": f"Contradicts previously verified fact: {fact.get('claim', '')}",
                "conflicting_fact": fact,
            }

    return None


def append_verified_claims(
    facts: list[dict],
    claims: list[str],
    source_query: str,
) -> list[dict]:
    existing = {_normalize_text(str(item.get("claim", ""))) for item in facts}
    now_iso = datetime.now(timezone.utc).isoformat()

    for claim in claims:
        normalized = _normalize_text(claim)
        if not normalized or normalized in existing:
            continue

        facts.append(
            {
                "claim": claim,
                "status": "TRUE",
                "source_query": source_query,
                "verified_at": now_iso,
            }
        )
        existing.add(normalized)

    return facts
