import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_hall.api.main import create_app
from ai_hall.pipeline.types import (
    Claim,
    ClaimAnalysis,
    EvidenceItem,
    EvidenceSet,
    Explanation,
    HallucinationFinding,
    HallucinationScore,
    HallucinationType,
    LLMGeneration,
    PipelineRun,
    QueryRequest,
    TextSpan,
    TrustReport,
    VerificationLabel,
    VerificationResult,
    VerificationState,
    VerifierOutput,
)


def _fake_run(
    query: str,
    *,
    answer_override: str | None = None,
    domain: str | None = None,
    team_id: str | None = None,
) -> PipelineRun:
    claim = Claim(claim_id="c1", text="Albert Einstein invented gravity in 1904.", span=TextSpan(start=0, end=10))
    verification = VerificationResult(
        claim_id="c1",
        combined=VerifierOutput(label=VerificationLabel.CONTRADICT, confidence=0.95, rationale="Historical conflict detected."),
        state=VerificationState.FALSE,
        source_urls=["https://example.org/einstein"],
        checked_at="2026-05-02T00:00:00+00:00",
    )
    analysis = ClaimAnalysis(
        claim=claim,
        evidence=EvidenceSet(
            claim_id="c1",
            items=[
                EvidenceItem(
                    evidence_id="e1",
                    title="Einstein article",
                    uri="https://example.org/einstein",
                    snippet="Einstein published special relativity in 1905 and general relativity in 1915.",
                    quality_score=0.91,
                    source_type="web",
                )
            ],
        ),
        verification=verification,
        score=HallucinationScore(
            claim_id="c1",
            p_hallucination=0.95,
            severity="high",
            reasons=["historical conflict"],
            uncertainty=0.05,
        ),
        confidence=95,
        hallucination=HallucinationFinding(
            claim_id="c1",
            hallucination_detected=True,
            type=HallucinationType.MISATTRIBUTION,
            rationale="Historical conflict detected.",
        ),
        explanation=Explanation(
            claim_id="c1",
            failure_mode="CONTRADICTED",
            explanation_text="Gravity was not invented. Einstein developed relativity later.",
            suggested_correction="Einstein developed special relativity in 1905 and general relativity in 1915.",
        ),
    )
    return PipelineRun(
        run_id="run-1",
        request=QueryRequest(query=query, domain=domain, answer_override=answer_override, team_id=team_id),
        generation=LLMGeneration(answer_text=answer_override or "Answer", provider="test", model="test-model", latency_ms=450),
        claims=[claim],
        analyses=[analysis],
        summary=TrustReport(
            hallucination=True,
            hard_gate_passed=False,
            reason="One or more claims are unsupported or contradicted",
            error_type="FACTUAL_ERROR",
            overall_reliability=22,
            claims_verified=0,
            claims_failed=1,
            risk_level="HIGH",
        ),
        corrected_answer="Einstein developed relativity in 1905 and 1915.",
        trace={},
    )


def test_verify_route(monkeypatch):
    import ai_hall.api.routes as routes

    monkeypatch.setattr(routes, "run", _fake_run)
    app = create_app()
    client = TestClient(app)

    response = client.post("/verify", json={"text": "Albert Einstein invented gravity in 1904."})
    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_score"] == 22
    assert payload["risk_level"] == "HIGH"
    assert payload["claims"][0]["status"] == "FALSE"
    assert payload["claims"][0]["hallucination_type"] == "misattribution"


def test_batch_and_export_routes(monkeypatch):
    import ai_hall.api.routes as routes

    monkeypatch.setattr(routes, "run", _fake_run)
    app = create_app()
    client = TestClient(app)

    batch_response = client.post("/batch", json={"queries": [{"query": "One"}, {"query": "Two", "domain": "academic"}]})
    assert batch_response.status_code == 200
    batch_payload = batch_response.json()
    assert batch_payload["aggregate_reliability"] == 22
    assert len(batch_payload["runs"]) == 2

    export_response = client.post("/reports/export", json={"query": "One", "format": "markdown"})
    assert export_response.status_code == 200
    assert "AI Hall Trust Report" in export_response.json()["content"]


def test_analytics_and_audit_routes(monkeypatch, tmp_path):
    import ai_hall.api.routes as routes
    from ai_hall.observability.audit import AuditLogger

    monkeypatch.setattr(routes, "run", _fake_run)
    monkeypatch.setenv("AI_HALL_AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    AuditLogger(path=tmp_path / "audit.jsonl").record_run(_fake_run("seed"))

    app = create_app()
    client = TestClient(app)

    audit_response = client.get("/audit/recent")
    assert audit_response.status_code == 200
    assert "events" in audit_response.json()

    analytics_response = client.get("/analytics/summary")
    assert analytics_response.status_code == 200
    assert "runs" in analytics_response.json()
