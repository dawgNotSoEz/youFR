from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class VerificationLabel(str, Enum):
    ENTAIL = "ENTAIL"
    CONTRADICT = "CONTRADICT"
    UNKNOWN = "UNKNOWN"


class VerificationState(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    PARTIALLY_TRUE = "PARTIALLY_TRUE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class HallucinationType(str, Enum):
    NONE = "none"
    FABRICATION = "fabrication"
    MISATTRIBUTION = "misattribution"
    OVERCONFIDENCE = "overconfidence"
    CONTRADICTION = "contradiction"
    UNSUPPORTED_EXTRAPOLATION = "unsupported_extrapolation"


class ClaimType(str, Enum):
    FACTUAL = "FACTUAL"
    NUMERIC = "NUMERIC"
    QUOTE = "QUOTE"
    DEFINITION = "DEFINITION"
    COMPARISON = "COMPARISON"
    CAUSAL = "CAUSAL"
    PROCEDURAL = "PROCEDURAL"
    OTHER = "OTHER"


class QueryRequest(BaseModel):
    query: str
    user_context: str | None = None
    domain: str | None = None
    answer_override: str | None = None
    team_id: str | None = None


class LLMUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMGeneration(BaseModel):
    answer_text: str
    provider: str | None = None
    model: str | None = None
    prompt_id: str | None = None
    latency_ms: int | None = None
    usage: LLMUsage | None = None
    raw: dict[str, Any] | None = None


class TextSpan(BaseModel):
    start: int
    end: int


class Claim(BaseModel):
    claim_id: str
    text: str
    span: TextSpan | None = None
    claim_type: ClaimType = ClaimType.FACTUAL
    entities: list[str] = Field(default_factory=list)
    normalized: str | None = None
    source_sentence_id: str | None = None


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: Literal["local", "wiki", "web", "custom"] = "local"
    uri: str | None = None
    title: str | None = None
    snippet: str
    span: TextSpan | None = None
    retrieved_at: str | None = None
    score: float = 0.0
    credibility: float = 0.5
    quality_score: float = 0.0
    rank_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSet(BaseModel):
    claim_id: str
    items: list[EvidenceItem] = Field(default_factory=list)


class VerifierOutput(BaseModel):
    label: VerificationLabel
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str | None = None
    cited_evidence_ids: list[str] = Field(default_factory=list)
    failure_mode: str | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    claim_id: str
    outputs: dict[str, VerifierOutput] = Field(default_factory=dict)  # by verifier name
    combined: VerifierOutput
    state: VerificationState = VerificationState.INSUFFICIENT_EVIDENCE
    source_urls: list[str] = Field(default_factory=list)
    checked_at: str | None = None


class HallucinationScore(BaseModel):
    claim_id: str
    p_hallucination: float = Field(ge=0.0, le=1.0)
    severity: Literal["low", "medium", "high"] = "medium"
    reasons: list[str] = Field(default_factory=list)
    uncertainty: float = Field(ge=0.0, le=1.0, default=0.5)


class Explanation(BaseModel):
    claim_id: str
    failure_mode: str
    explanation_text: str
    citations: list[str] = Field(default_factory=list)  # evidence ids
    suggested_correction: str | None = None
    confidence_reasoning: str | None = None


class HallucinationFinding(BaseModel):
    claim_id: str
    hallucination_detected: bool
    type: HallucinationType = HallucinationType.NONE
    rationale: str
    signals: list[str] = Field(default_factory=list)


class Correction(BaseModel):
    claim_id: str
    corrected_text: str
    citations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.6)


class ClaimAnalysis(BaseModel):
    claim: Claim
    evidence: EvidenceSet
    verification: VerificationResult
    score: HallucinationScore
    confidence: int = Field(ge=0, le=100, default=0)
    hallucination: HallucinationFinding | None = None
    explanation: Explanation | None = None
    correction: Correction | None = None


class TrustReport(BaseModel):
    hallucination: bool
    hard_gate_passed: bool
    reason: str
    error_type: str | None = None
    overall_reliability: int = Field(ge=0, le=100, default=0)
    claims_verified: int = 0
    claims_failed: int = 0
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    metrics: dict[str, Any] = Field(default_factory=dict)
    learnings: list[str] = Field(default_factory=list)


class PipelineRun(BaseModel):
    run_id: str
    request: QueryRequest
    generation: LLMGeneration
    claims: list[Claim]
    analyses: list[ClaimAnalysis]
    corrected_answer: str | None = None
    summary: TrustReport
    trace: dict[str, Any] = Field(default_factory=dict)

