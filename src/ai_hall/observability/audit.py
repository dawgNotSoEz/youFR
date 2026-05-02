from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_hall.config import get_settings
from ai_hall.pipeline.types import PipelineRun
from ai_hall.storage.audit_repository import AuditRepository


logger = logging.getLogger("ai_hall.audit")


@dataclass
class AuditLogger:
    path: Path | None = None
    repository: AuditRepository | None = None

    def __post_init__(self) -> None:
        if self.path is None:
            self.path = get_settings().audit_log_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.repository is None:
            self.repository = AuditRepository(path=self.path)

    def record_run(self, run: PipelineRun, *, actor: str | None = None, team_id: str | None = None) -> None:
        event = {
            "event_type": "pipeline_run",
            "at": datetime.now(timezone.utc).isoformat(),
            "actor": actor or "anonymous",
            "team_id": team_id or run.request.team_id,
            "run_id": run.run_id,
            "query": run.request.query,
            "domain": run.request.domain,
            "model": run.generation.model,
            "provider": run.generation.provider,
            "overall_reliability": run.summary.overall_reliability,
            "risk_level": run.summary.risk_level,
            "claims_verified": run.summary.claims_verified,
            "claims_failed": run.summary.claims_failed,
            "hallucination": run.summary.hallucination,
        }
        self.write(event)

    def write(self, event: dict[str, Any]) -> None:
        try:
            self.repository.save_event(event)
        except Exception as exc:
            logger.warning("audit_log_write_failed", extra={"error": str(exc)})
