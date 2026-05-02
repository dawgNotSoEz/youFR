from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_hall.pipeline.types import ClaimAnalysis
from ai_hall.utils.hashing import stable_hash


DEFAULT_FAILURE_MEMORY_PATH = Path("memory") / "failure_patterns.json"


@dataclass
class FailureMemory:
    path: Path = DEFAULT_FAILURE_MEMORY_PATH

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"patterns": {}, "events": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"patterns": {}, "events": []}

    def record(self, query: str, analyses: list[ClaimAnalysis]) -> list[str]:
        data = self.load()
        patterns = data.setdefault("patterns", {})
        events = data.setdefault("events", [])
        learnings: list[str] = []

        for analysis in analyses:
            if not analysis.hallucination or not analysis.hallucination.hallucination_detected:
                continue
            key = stable_hash(
                {
                    "type": analysis.hallucination.type.value,
                    "claim_type": analysis.claim.claim_type.value,
                    "normalized": (analysis.claim.normalized or analysis.claim.text).lower()[:120],
                }
            )
            current = patterns.get(key, {"count": 0, "type": analysis.hallucination.type.value, "examples": []})
            current["count"] = int(current.get("count", 0)) + 1
            examples = current.setdefault("examples", [])
            examples.append({"query": query, "claim": analysis.claim.text, "at": datetime.now(timezone.utc).isoformat()})
            current["examples"] = examples[-5:]
            patterns[key] = current
            if current["count"] >= 2:
                learnings.append(f"Recurring {current['type']} pattern seen {current['count']} times for similar claims.")

            events.append(
                {
                    "query": query,
                    "claim": analysis.claim.text,
                    "type": analysis.hallucination.type.value,
                    "confidence": analysis.confidence,
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )

        data["events"] = events[-1000:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return learnings

    def summarize(self, limit: int = 10) -> dict[str, Any]:
        data = self.load()
        patterns = sorted(data.get("patterns", {}).values(), key=lambda x: int(x.get("count", 0)), reverse=True)
        return {"patterns": patterns[:limit], "event_count": len(data.get("events", []))}
