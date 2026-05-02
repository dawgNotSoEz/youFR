from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_hall.config import get_settings


@dataclass
class AuditRepository:
    path: Path | None = None
    database_url: str | None = None

    def __post_init__(self) -> None:
        settings = get_settings()
        if self.path is None:
            self.path = settings.audit_log_path
        if self.database_url is None:
            self.database_url = settings.database_url
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save_event(self, event: dict[str, Any]) -> None:
        if self.database_url and self._save_postgres(event):
            return
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")

    def recent_events(self, limit: int = 50, *, team_id: str | None = None) -> list[dict[str, Any]]:
        if self.database_url:
            events = self._recent_postgres(limit, team_id=team_id)
            if events is not None:
                return events
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        events: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        filtered = [event for event in reversed(events) if team_id is None or event.get("team_id") == team_id]
        return filtered

    def analytics_summary(self, *, team_id: str | None = None) -> dict[str, Any]:
        events = self.recent_events(limit=500, team_id=team_id)
        total = len(events)
        if total == 0:
            return {
                "total_runs": 0,
                "average_reliability": 0,
                "risk_distribution": {},
                "team_id": team_id,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        avg_reliability = int(round(sum(int(event.get("overall_reliability", 0)) for event in events) / total))
        risk_distribution: dict[str, int] = {}
        for event in events:
            risk = str(event.get("risk_level", "UNKNOWN"))
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1

        return {
            "total_runs": total,
            "average_reliability": avg_reliability,
            "risk_distribution": risk_distribution,
            "team_id": team_id,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def _save_postgres(self, event: dict[str, Any]) -> bool:
        try:
            import psycopg

            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        create table if not exists ai_hall_audit_events (
                            id bigserial primary key,
                            created_at timestamptz not null default now(),
                            event jsonb not null
                        )
                        """
                    )
                    cur.execute("insert into ai_hall_audit_events (event) values (%s)", (json.dumps(event),))
                conn.commit()
            return True
        except Exception:
            return False

    def _recent_postgres(self, limit: int, *, team_id: str | None = None) -> list[dict[str, Any]] | None:
        try:
            import psycopg

            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    if team_id:
                        cur.execute(
                            """
                            select event
                            from ai_hall_audit_events
                            where event->>'team_id' = %s
                            order by created_at desc, id desc
                            limit %s
                            """,
                            (team_id, limit),
                        )
                    else:
                        cur.execute(
                            """
                            select event
                            from ai_hall_audit_events
                            order by created_at desc, id desc
                            limit %s
                            """,
                            (limit,),
                        )
                    rows = cur.fetchall()
            return [row[0] if isinstance(row[0], dict) else json.loads(row[0]) for row in rows]
        except Exception:
            return None
