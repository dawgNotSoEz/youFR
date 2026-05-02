from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from ai_hall.pipeline.types import EvidenceItem, EvidenceSet


HIGH_AUTHORITY_DOMAINS = {
    "nih.gov": 0.98,
    "who.int": 0.96,
    "cdc.gov": 0.95,
    "sec.gov": 0.95,
    "federalreserve.gov": 0.94,
    "irs.gov": 0.93,
    "supreme.justia.com": 0.92,
    "law.cornell.edu": 0.9,
    "wikipedia.org": 0.72,
}

DOMAIN_DEFAULTS = {
    "medical": {"nih.gov", "who.int", "cdc.gov", "mayoclinic.org"},
    "legal": {"law.cornell.edu", "supreme.justia.com", "justice.gov", "govinfo.gov"},
    "finance": {"sec.gov", "federalreserve.gov", "irs.gov", "treasury.gov"},
    "academic": {"doi.org", "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com"},
}


def _host(uri: str | None) -> str:
    if not uri:
        return ""
    parsed = urlparse(uri if "://" in uri else f"https://{uri}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.")


def _domain_authority(uri: str | None, domain: str | None) -> float:
    host = _host(uri)
    if not host:
        return 0.55
    for trusted, score in HIGH_AUTHORITY_DOMAINS.items():
        if host.endswith(trusted):
            return score
    if domain and any(host.endswith(d) for d in DOMAIN_DEFAULTS.get(domain.lower(), set())):
        return 0.9
    if host.endswith(".gov") or host.endswith(".edu"):
        return 0.86
    if host.endswith(".org"):
        return 0.7
    return 0.6


def _recency_score(item: EvidenceItem) -> float:
    if not item.retrieved_at:
        return 0.5
    try:
        dt = datetime.fromisoformat(item.retrieved_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.5
    age_days = max(0, (datetime.now(timezone.utc) - dt).days)
    if age_days <= 30:
        return 1.0
    if age_days <= 365:
        return 0.85
    return 0.65


def rank_evidence(evidence: EvidenceSet, *, domain: str | None = None) -> EvidenceSet:
    hosts = [_host(item.uri) for item in evidence.items if item.uri]
    duplicate_host_penalty = {host: 0.05 * max(0, hosts.count(host) - 1) for host in set(hosts)}
    ranked: list[EvidenceItem] = []

    for item in evidence.items:
        authority = _domain_authority(item.uri, domain)
        recency = _recency_score(item)
        retrieval = max(0.0, min(1.0, float(item.score or 0.0)))
        consistency = 0.8 if hosts.count(_host(item.uri)) <= 1 else 0.7
        penalty = duplicate_host_penalty.get(_host(item.uri), 0.0)
        quality = max(0.0, min(1.0, (0.38 * authority) + (0.22 * recency) + (0.25 * retrieval) + (0.15 * consistency) - penalty))
        ranked.append(
            item.model_copy(
                update={
                    "credibility": max(item.credibility, authority),
                    "quality_score": round(quality, 4),
                    "rank_reason": f"authority={authority:.2f}; recency={recency:.2f}; retrieval={retrieval:.2f}; consistency={consistency:.2f}",
                }
            )
        )

    return EvidenceSet(claim_id=evidence.claim_id, items=sorted(ranked, key=lambda x: x.quality_score, reverse=True))
