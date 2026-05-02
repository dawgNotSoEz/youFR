from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass
class AITruthLayerClient:
    base_url: str
    api_key: str | None = None
    timeout_seconds: float = 10.0
    session: requests.Session = field(default_factory=requests.Session)

    def verify(
        self,
        text: str,
        *,
        source_prompt: str | None = None,
        domain: str | None = None,
        team_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        response = self.session.post(
            f"{self.base_url.rstrip('/')}/verify",
            json={
                "text": text,
                "source_prompt": source_prompt,
                "domain": domain,
                "team_id": team_id,
                "metadata": metadata or {},
            },
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()


TruthLayerClient = AITruthLayerClient
Validator = AITruthLayerClient
