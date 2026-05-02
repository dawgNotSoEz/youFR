# 🏗️ AI Hall: Project Architecture & Design

## Table of Contents
1. [System Overview](#system-overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [Component Breakdown](#component-breakdown)
4. [Data Flow](#data-flow)
5. [Verifier Ensemble](#verifier-ensemble)
6. [Storage & Persistence](#storage--persistence)
7. [API Layer](#api-layer)
8. [Integration Points](#integration-points)

---

## System Overview

**AI Hall** is an enterprise-grade AI verification platform built as a modular verification pipeline. The system is designed to answer the core question: **"Can we trust this AI-generated answer?"**

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                            │
│  (Web Dashboard / REST API / Python/JS SDKs)               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   API LAYER (FastAPI)                       │
│  • Authentication & Authorization                           │
│  • Request/Response Marshalling                             │
│  • Caching Layer (in-memory/Redis)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              ORCHESTRATION LAYER                            │
│  (Pipeline Coordinator - 9 Phases)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──┐ ┌──────▼────┐ ┌────▼──────┐
│Generation│ │ Extraction│ │ Retrieval │
└───────┬──┘ └──────┬────┘ └────┬──────┘
        │           │           │
        └───────────┼───────────┘
                    │
        ┌───────────▼───────────┐
        │   Verification Core   │
        │  (4-Model Ensemble)   │
        └───────────┬───────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌──▼───┐      ┌────▼────┐     ┌──▼──┐
│NLI   │      │LLM Judge│     │Phi3 │
└──┬───┘      └────┬────┘     └──┬──┘
   │               │             │
   └───────────────┼─────────────┘
                   │
        ┌──────────▼──────────┐
        │ Scoring & Detection │
        │ (Hallucination)     │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │  Explainability &   │
        │ Report Generation   │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │ Storage & Memory    │
        │ (Facts + Patterns)  │
        └─────────────────────┘
```

---

## Pipeline Architecture

### 9-Phase Verification Pipeline

#### **Phase 1: Generation**
- **Component:** `src/ai_hall/app.py` → `PassthroughClient`
- **Purpose:** Generate initial LLM response
- **Inputs:** Query string
- **Outputs:** Generated answer text
- **External Dependencies:** MegaLLM API, Ollama (fallback)
- **Key Config:** `MEGA_API_KEY`, `MEGA_MODELS`

```python
llm = PassthroughClient()
answer = llm.generate(QueryRequest(query="..."))
```

---

#### **Phase 2: Claim Extraction**
- **Component:** `src/ai_hall/claims/extractor.py`
- **Purpose:** Decompose answer into atomic, verifiable claims
- **Inputs:** Generated answer text
- **Outputs:** List of `Claim` objects
- **Algorithm:** LLM-based decomposition with constraint checks
- **Key Code:**
  ```python
  claims = extract_claims(answer_text)
  # Returns: [Claim(text="...", confidence=...), ...]
  ```

---

#### **Phase 3: Evidence Retrieval**
- **Component:** `src/ai_hall/retrievers/hybrid.py`
- **Purpose:** Find supporting/contradicting evidence for each claim
- **Inputs:** Individual claims
- **Outputs:** Evidence documents ranked by relevance
- **Retrieval Strategy:**
  - BM25 lexical search (fast, keyword-based)
  - Dense embedding search (semantic similarity)
  - Hybrid fusion (combined ranking)
- **Config:**
  ```python
  config = RetrievalConfig(
      max_evidence=5,
      local_corpus_dir="corpus",
      use_dense=True
  )
  ```

---

#### **Phase 4: Evidence Ranking**
- **Component:** `src/ai_hall/retrievers/ranking.py`
- **Purpose:** Score and rank retrieved evidence
- **Ranking Factors:**
  - Domain authority (Wikipedia > random blog)
  - Recency (newer sources preferred)
  - BM25 score
  - Cross-source consistency
  - Embedding similarity
- **Output:** `EvidenceSet` with scores

---

#### **Phase 5: Verification Ensemble**
- **Component:** `src/ai_hall/verifiers/ensemble.py`
- **Purpose:** Parallel verification via 4-model consensus
- **Verifiers:**
  1. NLI Verifier (entailment model)
  2. LLM Grounded Judge (reasoning)
  3. Local Phi3 (on-device inference)
  4. Memory Contradiction Checker
- **Consensus Rule:**
  ```
  if agreement_count >= 3 AND confidence >= 75%:
      status = TRUE
  elif agreement_count <= 1:
      status = FALSE
  else:
      status = UNCERTAIN
  ```

---

#### **Phase 6: Hallucination Detection**
- **Component:** `src/ai_hall/detection.py`
- **Purpose:** Classify hallucination type if found
- **5 Hallucination Types:**
  1. **Fabrication:** Made-up facts not in evidence
  2. **Misattribution:** Wrong source/author credited
  3. **Overconfidence:** Unsupported certainty
  4. **Contradiction:** Conflicts with known facts
  5. **Unsupported Extrapolation:** Logical leap without basis
- **Scoring:** Combines verifier signals + pattern matching

---

#### **Phase 7: Explainability**
- **Component:** `src/ai_hall/explanations/engine.py`
- **Purpose:** Generate human-readable reasoning per claim
- **Output:** Evidence snippets + reasoning text
- **Example:**
  ```json
  {
    "text": "Einstein formulated relativity in 1905",
    "explanation": "Supported by peer-reviewed sources",
    "supporting_evidence": [
      {"source": "Wikipedia", "snippet": "..."}
    ]
  }
  ```

---

#### **Phase 8: Fusion**
- **Component:** `src/ai_hall/pipeline/orchestrator.py`
- **Purpose:** Multi-source consensus decision
- **Rule:** Strong consensus accepts result when:
  - LLM + Evidence both TRUE
  - High confidence (>75%)
  - Embedding support confirmed
  - Even if local verifier UNCERTAIN

---

#### **Phase 9: Memory & Decision**
- **Component:** `src/ai_hall/memory/failures.py`
- **Purpose:** Learn and persist patterns
- **Outputs:**
  - Store TRUE claims in `verified_facts.json`
  - Record failure patterns in `failure_patterns.json`
  - Log all events in `audit.jsonl`
- **Persistence:**
  ```json
  {
    "verified_facts": {
      "Einstein formulated relativity in 1905": {
        "confidence": 0.98,
        "sources": ["Wikipedia", "Academic DB"],
        "timestamp": "2025-05-02T..."
      }
    }
  }
  ```

---

## Component Breakdown

### Core Pipeline Components

#### `src/ai_hall/app.py`
**Entry point orchestrator**
- Wires all phases together
- Manages state flow through pipeline
- Handles error recovery

```python
def run(query, *, answer_override=None, domain=None, team_id=None):
    # Coordinates all 9 phases
    return run_explain_pipeline(...)
```

#### `src/ai_hall/api/` (API Layer)
- **`routes.py`** – 10 REST endpoints
- **`models.py`** – Pydantic request/response schemas
- **`presenters.py`** – Response formatting
- **`dashboard.py`** – Web UI server
- **`main.py`** – FastAPI app initialization

#### `src/ai_hall/claims/`
- **`extractor.py`** – LLM-based claim decomposition

#### `src/ai_hall/retrievers/`
- **`hybrid.py`** – BM25 + dense embedding retrieval
- **`bm25.py`** – Lexical search implementation
- **`corpus.py`** – Local corpus management
- **`ranking.py`** – Evidence relevance scoring

#### `src/ai_hall/verifiers/`
- **`ensemble.py`** – Orchestrates 4 verifiers
- **`nli.py`** – Natural Language Inference (entailment)
- **`llm_grounded_judge.py`** – LLM-based reasoning
- **`local_phi3.py`** – Ollama Phi3 integration
- **`memory_contradiction.py`** – Historical fact checking
- **`combiner.py`** – Consensus logic

#### `src/ai_hall/scoring/`
- **`model.py`** – Hallucination scoring logic

#### `src/ai_hall/explanations/`
- **`engine.py`** – Explanation generation

#### `src/ai_hall/correction/`
- **`engine.py`** – Auto-correction with re-verification

#### `src/ai_hall/observability/`
- **`audit.py`** – Structured audit logging

#### `src/ai_hall/storage/`
- **`audit_repository.py`** – Persistence layer (JSON/PostgreSQL)

#### `src/ai_hall/cache.py`
- **Hybrid caching** – In-memory + optional Redis

---

## Data Flow

### Request → Response Flow

```
1. API Request
   ├─ POST /explain with QueryRequest
   ├─ Validation & Auth
   └─ Cache lookup

2. Pipeline Execution
   ├─ Phase 1: Generation
   │  └─ Output: answer_text
   ├─ Phase 2: Extraction
   │  └─ Output: List[Claim]
   ├─ Phase 3-4: Retrieval & Ranking
   │  └─ Output: EvidenceSet per claim
   ├─ Phase 5: Verification
   │  └─ Output: VerificationResult[] (per verifier)
   ├─ Phase 6: Hallucination Detection
   │  └─ Output: HallucinationType, score
   ├─ Phase 7: Explainability
   │  └─ Output: Explanation + supporting evidence
   ├─ Phase 8: Fusion
   │  └─ Output: Consensus decision (TRUE/FALSE/UNCERTAIN)
   └─ Phase 9: Memory
      └─ Output: Persisted facts

3. Response Construction
   ├─ Aggregate claim results
   ├─ Calculate overall_reliability (0-100)
   ├─ Determine risk_level (LOW/MEDIUM/HIGH/CRITICAL)
   └─ Format VerifyResponse

4. Return to Client
   └─ JSON serialized response
```

### Data Models

```
QueryRequest
  ├─ query: str
  ├─ answer_override: str | None
  ├─ domain: str | None (medical/legal/finance/academic/general)
  ├─ team_id: str | None
  └─ user_context: str | None

PipelineRun
  ├─ request_id: str (unique)
  ├─ query: str
  ├─ generation: Generation
  │  └─ text: str
  ├─ claims: List[Claim]
  ├─ evidence: EvidenceSet
  ├─ verification_results: List[VerificationResult]
  ├─ summary: Summary
  │  ├─ overall_reliability: int (0-100)
  │  ├─ risk_level: str (LOW/MEDIUM/HIGH/CRITICAL)
  │  ├─ hallucination_detected: bool
  │  └─ claims_verified: int
  └─ traces: dict (debug info)

VerifiedClaim
  ├─ text: str
  ├─ status: str (TRUE/FALSE/PARTIALLY_TRUE/INSUFFICIENT_EVIDENCE/CONFLICTING_EVIDENCE)
  ├─ confidence: int (0-100)
  ├─ hallucination_type: str
  ├─ explanation: str
  ├─ suggested_correction: str | None
  ├─ supporting_evidence: List[Evidence]
  └─ source_urls: List[str]

Evidence
  ├─ text: str (snippet)
  ├─ source: str (Wikipedia, etc)
  ├─ url: str
  ├─ relevance_score: float (0-1)
  ├─ domain_authority: float
  └─ recency_score: float
```

---

## Verifier Ensemble

### 4-Model Consensus Strategy

```
┌─────────────────────────────────────────┐
│           Claim + Evidence              │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┬─────────────────┐
    │            │            │                 │
    ▼            ▼            ▼                 ▼
┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐
│NLI Model │ │LLM Judge │ │ Phi3   │ │Memory Check  │
│          │ │          │ │ Local  │ │(Contradiction)
│Entailment│ │Reasoning │ │ Model  │ │              │
└────┬─────┘ └────┬─────┘ └───┬────┘ └──────┬───────┘
     │            │           │             │
     │ Score:     │ Score:    │ Score:     │ Result:
     │ 0.85       │ 0.92      │ 0.76      │ TRUE/FALSE
     │            │           │            │
     └────────────┼───────────┼────────────┘
                  │
        ┌─────────▼──────────┐
        │ Consensus Engine   │
        │ if agreement >= 3: │
        │   status = TRUE    │
        │ else if <= 1:      │
        │   status = FALSE   │
        │ else:              │
        │   status = UNCERTAIN
        └────────┬───────────┘
                 │
        ┌────────▼──────────┐
        │ Final Verdict     │
        │ + Confidence      │
        └───────────────────┘
```

### Verifier Details

| Verifier | Type | Latency | Accuracy | Cost | Strengths | Weaknesses |
|----------|------|---------|----------|------|-----------|-----------|
| **NLI** | ML Model | ~200ms | High | Free | Fast, reliable entailment | Limited reasoning |
| **LLM Judge** | Cloud API | ~1-2s | Very High | Medium | Sophisticated reasoning | Cost, latency |
| **Phi3 Local** | Local Model | ~500ms | Medium | None | Fast, private | Less accurate |
| **Memory** | Rules | ~10ms | High | Free | Catches contradictions | Limited to known facts |

---

## Storage & Persistence

### Runtime Storage (`memory/`)

#### `verified_facts.json`
Stores TRUE claims for future reference and contradiction checks.

```json
{
  "Einstein formulated relativity in 1905": {
    "confidence": 0.98,
    "sources": ["Wikipedia", "Academic Journal"],
    "timestamp": "2025-05-02T10:30:00Z",
    "domain": "science"
  }
}
```

#### `failure_patterns.json`
Tracks recurring hallucination patterns for analysis and prevention.

```json
{
  "patterns": [
    {
      "type": "date_fabrication",
      "frequency": 5,
      "examples": [
        "Einstein birth year fabricated",
        "WWII end date incorrect"
      ]
    }
  ]
}
```

### Audit Trail (`logs/audit.jsonl`)
Line-delimited JSON log of all verification events.

```jsonl
{"timestamp": "2025-05-02T10:30:00Z", "query": "...", "result": "TRUE", "actor": "user-42"}
{"timestamp": "2025-05-02T10:31:00Z", "query": "...", "result": "FALSE", "actor": "system"}
```

### Optional Persistence (PostgreSQL)

For enterprise deployments:
- Structured audit tables
- Analytics queries
- Team-scoped data partitioning
- Backup/recovery

---

## API Layer

### Authentication
- **Bearer Token** required for all endpoints except `/healthz`
- Token validation via `RequestIdentity` dependency

### Request/Response Pattern
```python
@router.post("/verify", response_model=VerifyResponse)
def verify(
    req: VerifyRequest,
    identity: RequestIdentity = Depends(get_identity)
) -> VerifyResponse:
    # 1. Extract from request
    # 2. Run pipeline
    # 3. Format response
    return VerifyResponse(...)
```

### 10 REST Endpoints

1. **POST /verify** – Verify text claim
2. **POST /explain** – Full pipeline run
3. **POST /batch** – Verify up to 50 queries
4. **POST /adversarial** – Stress testing
5. **POST /reports/export** – Export as JSON/Markdown
6. **GET /memory/failures** – Failure patterns
7. **GET /audit/recent** – Recent events
8. **GET /analytics/summary** – Platform stats
9. **GET /teams/{team_id}/analytics** – Team stats
10. **GET /healthz** – Health check

### Caching Strategy
```python
cache_key = hybrid_cache.key(request.model_dump())
cached_result = hybrid_cache.get(cache_key)
if not cached_result:
    result = run_pipeline(...)
    hybrid_cache.set(cache_key, result, ttl=3600)
return result
```

---

## Integration Points

### External APIs

#### MegaLLM (Generation Phase)
- **Endpoint:** `MEGA_API_URL`
- **Models:** gpt-5, claude-sonnet-4-5-20250929, openai-gpt-oss-20b
- **Fallback:** Secondary API key if primary fails
- **Used in:** Phase 1 (generation), Phase 5 (LLM Judge)

#### Groq API (Optional)
- **Purpose:** Alternative verifier signal
- **Latency:** Ultra-fast inference
- **Config:** `GROQ_API_KEY`

#### Ollama (Local Verification)
- **URL:** `http://localhost:11434`
- **Model:** phi3 (or comparable)
- **Used in:** Phase 5 (Phi3 Local verifier)

#### Wikipedia/Web Search
- **Purpose:** Evidence retrieval
- **Used in:** Phase 3-4 (retrieval and ranking)

### Client SDKs

#### Python SDK (`sdk/python/`)
```python
from ai_truth_layer import AIHallClient

client = AIHallClient(api_url="http://localhost:8001", api_key="...")
result = client.verify("Einstein invented relativity")
print(result.overall_score)
```

#### JavaScript SDK (`sdk/javascript/`)
```typescript
import { AIHallClient } from 'ai-truth-layer';

const client = new AIHallClient({
  apiUrl: 'http://localhost:8001',
  apiKey: '...'
});

const result = await client.verify('...');
```

---

## Environment Variables Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `MEGA_API_KEY` | ✅ | - | MegaLLM primary API key |
| `MEGA_API_URL` | ✅ | - | MegaLLM endpoint URL |
| `MEGA_FALLBACK_API_KEY` | ❌ | - | Secondary API key |
| `GROQ_API_KEY` | ❌ | - | Groq API key |
| `OLLAMA_URL` | ❌ | `http://localhost:11434` | Local Phi3 endpoint |
| `REDIS_URL` | ❌ | - | Redis connection (optional caching) |
| `POSTGRES_URL` | ❌ | - | PostgreSQL connection (audit logging) |
| `LOG_LEVEL` | ❌ | `INFO` | Python logging level |

---

## Deployment Architecture

### Single Container
```
Container
├─ Python 3.11+ environment
├─ FastAPI server (port 8001)
├─ In-memory cache
└─ Local file storage (memory/, logs/)
```

### Distributed (Enterprise)
```
Load Balancer (HTTPS)
  ├─ API Pod 1 (FastAPI)
  ├─ API Pod 2 (FastAPI)
  └─ API Pod 3 (FastAPI)
      ├─ Shared PostgreSQL (audit log)
      ├─ Shared Redis (cache)
      ├─ S3 / GCS (verified facts backup)
      └─ Ollama cluster (Phi3 inference)
```

---

## Error Handling & Resilience

### Fallback Strategy
1. Primary LLM API fails → Use fallback key
2. Fallback fails → Use Ollama/Phi-3 local
3. Local fails → Return UNCERTAIN status with warning

### Retry Policy
- API calls: 3 retries with exponential backoff
- Verifiers: Continue even if one fails (ensemble is robust)
- Evidence retrieval: Use cached results on failure

### Error Responses
```json
{
  "error": "API_KEY_INVALID",
  "detail": "MegaLLM authentication failed",
  "status_code": 401,
  "request_id": "req-abc123"
}
```

---

## Security Considerations

### Authentication
- Bearer token validation on all endpoints (except health check)
- Team-scoped data isolation via `team_id`
- Role-based access control (analyst/admin)

### Data Privacy
- API keys stored in environment (never in code)
- Audit logs exclude sensitive query content (optional)
- PostgreSQL encryption at rest (recommended)

### Rate Limiting
- Future: Token bucket rate limiter
- Per-team quota enforcement

---

## Performance Characteristics

### Latency Breakdown (Per Query)
```
Generation:     1-2s   (MegaLLM API)
Extraction:     200ms  (LLM)
Retrieval:      300ms  (BM25 + dense)
Ranking:        100ms  (scoring)
Verification:   ~2s    (parallel 4 verifiers)
  ├─ NLI:       200ms
  ├─ LLM Judge: 1.5s
  ├─ Phi3:      500ms
  └─ Memory:    10ms
Scoring:        100ms
Explainability: 300ms
─────────────────────────
Total:          ~5-6s per query
```

### Throughput
- **Single instance:** ~10 queries/sec (with caching)
- **Distributed (3 pods):** ~30 queries/sec
- **Batch endpoint:** 50 queries in parallel

---

## Future Roadmap

- [ ] GraphQL API support
- [ ] WebSocket streaming responses
- [ ] Multi-language hallucination detection
- [ ] Custom domain knowledge injection
- [ ] Federated learning for verifier models
- [ ] Real-time performance dashboards
- [ ] Advanced RBAC and SSO integration
