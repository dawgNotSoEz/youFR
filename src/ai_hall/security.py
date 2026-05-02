from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from ai_hall.config import get_settings


@dataclass(frozen=True)
class RequestIdentity:
    subject: str
    role: str = "admin"
    team_id: str | None = None


def _parse_key_entries() -> dict[str, RequestIdentity]:
    settings = get_settings()
    identities: dict[str, RequestIdentity] = {}
    for raw in settings.api_keys:
        parts = [part.strip() for part in raw.split(":")]
        key = parts[0]
        role = parts[1] if len(parts) > 1 and parts[1] else "admin"
        team_id = parts[2] if len(parts) > 2 and parts[2] else None
        identities[key] = RequestIdentity(subject=key[-6:] if len(key) >= 6 else key, role=role, team_id=team_id)
    return identities


def get_identity(x_api_key: str | None = Header(default=None)) -> RequestIdentity:
    settings = get_settings()
    known = _parse_key_entries()
    if not settings.require_auth and not known:
        return RequestIdentity(subject="anonymous", role="admin")
    if x_api_key and x_api_key in known:
        return known[x_api_key]
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid X-API-Key header required")


def require_analyst(identity: RequestIdentity = Depends(get_identity)) -> RequestIdentity:
    if identity.role not in {"admin", "analyst"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Analyst or admin role required")
    return identity
