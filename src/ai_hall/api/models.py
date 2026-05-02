from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ai_hall.pipeline.types import PipelineRun, QueryRequest


class VerifyRequest(BaseModel):
    text: str = Field(min_length=1)
    source_prompt: str | None = None
    domain: str | None = None
    team_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerifiedClaim(BaseModel):
    text: str
    status: Literal["TRUE", "FALSE", "PARTIALLY_TRUE", "INSUFFICIENT_EVIDENCE", "CONFLICTING_EVIDENCE"]
    confidence: int = Field(ge=0, le=100)
    hallucination_type: str
    explanation: str
    suggested_correction: str | None = None
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class VerifyResponse(BaseModel):
    request_id: str
    overall_score: int = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    model_used: str | None = None
    latency_ms: int | None = None
    claims: list[VerifiedClaim] = Field(default_factory=list)
    corrected_text: str | None = None
    trace: dict[str, Any] = Field(default_factory=dict)


class BatchRequest(BaseModel):
    queries: list[QueryRequest] = Field(min_length=1, max_length=50)


class BatchResponse(BaseModel):
    runs: list[PipelineRun]
    aggregate_reliability: int
    high_risk_runs: int


class ExportRequest(QueryRequest):
    format: Literal["json", "markdown"] = "markdown"


class ExportResponse(BaseModel):
    format: Literal["json", "markdown"]
    content: str
