from __future__ import annotations

from fastapi import APIRouter, Depends

from ai_hall.analytics import platform_analytics
from ai_hall.app import run
from ai_hall.api.models import BatchRequest, BatchResponse, ExportRequest, ExportResponse, VerifyRequest, VerifyResponse
from ai_hall.api.presenters import to_verify_response
from ai_hall.cache import hybrid_cache
from ai_hall.evaluation.adversarial import AdversarialRun, run_adversarial_suite
from ai_hall.memory.failures import FailureMemory
from ai_hall.observability.audit import AuditLogger
from ai_hall.pipeline.types import PipelineRun, QueryRequest
from ai_hall.reports import export_report
from ai_hall.security import RequestIdentity, get_identity, require_analyst
from ai_hall.storage.audit_repository import AuditRepository


router = APIRouter()


def _run_pipeline(req: QueryRequest, identity: RequestIdentity) -> PipelineRun:
    key = hybrid_cache.key(req.model_dump())
    cached = hybrid_cache.get(key)
    if cached:
        return cached
    result = run(req.query, answer_override=req.answer_override, domain=req.domain, team_id=req.team_id or identity.team_id)
    AuditLogger().record_run(result, actor=identity.subject, team_id=req.team_id or identity.team_id)
    hybrid_cache.set(key, result)
    return result


@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, identity: RequestIdentity = Depends(get_identity)) -> VerifyResponse:
    pipeline_req = QueryRequest(
        query=req.source_prompt or "Verification-only mode",
        answer_override=req.text,
        domain=req.domain,
        team_id=req.team_id,
        user_context=str(req.metadata) if req.metadata else None,
    )
    return to_verify_response(_run_pipeline(pipeline_req, identity))


@router.post("/explain", response_model=PipelineRun)
def explain(req: QueryRequest, identity: RequestIdentity = Depends(get_identity)) -> PipelineRun:
    return _run_pipeline(req, identity)


@router.post("/batch", response_model=BatchResponse)
def batch(req: BatchRequest, identity: RequestIdentity = Depends(get_identity)) -> BatchResponse:
    runs = [explain(item, identity) for item in req.queries]
    aggregate = int(round(sum(r.summary.overall_reliability for r in runs) / max(1, len(runs))))
    high = sum(1 for r in runs if r.summary.risk_level in {"HIGH", "CRITICAL"})
    return BatchResponse(runs=runs, aggregate_reliability=aggregate, high_risk_runs=high)


@router.post("/adversarial", response_model=AdversarialRun)
def adversarial(req: QueryRequest, identity: RequestIdentity = Depends(get_identity)) -> AdversarialRun:
    return run_adversarial_suite(req.query, run, domain=req.domain)


@router.post("/reports/export", response_model=ExportResponse)
def export(req: ExportRequest, identity: RequestIdentity = Depends(get_identity)) -> ExportResponse:
    result = explain(QueryRequest(**req.model_dump(exclude={"format"})), identity)
    return ExportResponse(format=req.format, content=export_report(result, format=req.format))


@router.get("/memory/failures")
def failure_memory(identity: RequestIdentity = Depends(require_analyst)):
    return FailureMemory().summarize()


@router.get("/audit/recent")
def recent_audit_events(limit: int = 20, identity: RequestIdentity = Depends(require_analyst)):
    team_id = identity.team_id if identity.role != "admin" else None
    return {"events": AuditRepository().recent_events(limit=max(1, min(limit, 200)), team_id=team_id)}


@router.get("/analytics/summary")
def analytics_summary(identity: RequestIdentity = Depends(require_analyst)):
    team_id = identity.team_id if identity.role != "admin" else None
    return platform_analytics(team_id=team_id)


@router.get("/teams/{team_id}/analytics")
def team_analytics(team_id: str, identity: RequestIdentity = Depends(require_analyst)):
    if identity.role != "admin" and identity.team_id != team_id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Team scope mismatch")
    return platform_analytics(team_id=team_id)


@router.get("/healthz")
def healthz():
    return {"ok": True, "product": "AI Truth Layer"}

