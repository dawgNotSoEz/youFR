from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainPolicy:
    name: str
    risk_floor: str
    minimum_confidence: int
    correction_style: str


POLICIES = {
    "medical": DomainPolicy("medical", "HIGH", 85, "Use conservative clinical wording and avoid treatment instructions unless evidence is authoritative."),
    "legal": DomainPolicy("legal", "HIGH", 85, "Use jurisdiction-aware wording and avoid legal advice when evidence is incomplete."),
    "finance": DomainPolicy("finance", "HIGH", 82, "Prefer regulator filings, timestamped market data, and explicit uncertainty for projections."),
    "academic": DomainPolicy("academic", "MEDIUM", 78, "Prefer primary literature, DOI-backed sources, and distinguish findings from hypotheses."),
    "general": DomainPolicy("general", "MEDIUM", 70, "Prefer concise corrections grounded in retrieved evidence."),
}


def get_domain_policy(domain: str | None) -> DomainPolicy:
    return POLICIES.get((domain or "general").lower(), POLICIES["general"])
