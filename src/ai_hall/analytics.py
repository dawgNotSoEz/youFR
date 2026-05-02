from __future__ import annotations

from ai_hall.memory.failures import FailureMemory
from ai_hall.storage.audit_repository import AuditRepository


def platform_analytics(*, team_id: str | None = None) -> dict[str, object]:
    audit = AuditRepository().analytics_summary(team_id=team_id)
    failures = FailureMemory().summarize(limit=5)
    return {
        "runs": audit,
        "failure_patterns": failures,
    }
