# 🛡️ AI Hall: Enterprise AI Reliability Platform

> **The question every enterprise asks:** _Can we trust this AI answer?_

**AI Hall** is a production-grade AI verification and hallucination detection platform. It generates answers, automatically decomposes them into atomic claims, verifies each claim against real evidence, detects hallucinations, explains findings, and learns from failures—all through a single API.

## 🎯 What It Does

AI Hall takes an AI-generated answer and returns a **trust score** (0-100), **risk level** (LOW/MEDIUM/HIGH/CRITICAL), a list of verified/failed claims with explanations, and optionally a corrected version if hallucinations were detected.

```
Query: "Who invented relativity?"
  ↓
LLM Generation
  ↓
Claim Extraction (e.g., "Einstein formulated relativity in 1905")
  ↓
Evidence Retrieval (Wikipedia, academic sources, etc.)
  ↓
Multi-Verifier Ensemble (LLM + NLI + Local Phi3 + Memory)
  ↓
Hallucination Scoring & Detection
  ↓
Auto-Correction (if needed)
  ↓
Trust Report + Explanation
```

---

## 🏗️ Architecture

### Pipeline Stages (9-Phase Flow)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. GENERATION          │ Cloud LLM (MegaLLM) or Local (Phi-3)    │
├─────────────────────────────────────────────────────────────────┤
│ 2. EXTRACTION          │ Atomic claim decomposition              │
├─────────────────────────────────────────────────────────────────┤
│ 3. RETRIEVAL           │ Hybrid BM25 + Dense embeddings          │
├─────────────────────────────────────────────────────────────────┤
│ 4. RANKING             │ Domain authority, recency, consistency  │
├─────────────────────────────────────────────────────────────────┤
│ 5. VERIFICATION        │ 4-model ensemble consensus              │
├─────────────────────────────────────────────────────────────────┤
│ 6. HALLUCINATION TEST  │ 5 hallucination types detected          │
├─────────────────────────────────────────────────────────────────┤
│ 7. EXPLAINABILITY      │ Evidence-backed reasoning per claim     │
├─────────────────────────────────────────────────────────────────┤
│ 8. FUSION              │ Strong consensus from multi-sources     │
├─────────────────────────────────────────────────────────────────┤
│ 9. MEMORY & DECISION   │ Learned facts + final trust decision    │
└─────────────────────────────────────────────────────────────────┘
```

### Verifier Ensemble

| Verifier | Type | Purpose |
|----------|------|---------|
| **NLI Verifier** | ML Model | Semantic entailment (evidence → claim) |
| **LLM Grounded Judge** | LLM-based | Evidence-aware reasoning via MegaLLM |
| **Local Phi3** | Local Model | Independent signal (Ollama, on-device) |
| **Memory Contradiction** | Rules | Persistent knowledge graph checks |

---

## ⚡ Key Features

- ✅ **Multi-Model Verification** – Consensus-based claim validation (NLI + LLM + Local + Memory)
- ✅ **Atomic Claim Extraction** – Breaks answers into verifiable units
- ✅ **Hybrid Retrieval** – BM25 + dense embeddings for evidence ranking
- ✅ **5 Hallucination Types** – Fabrication, misattribution, overconfidence, contradiction, unsupported extrapolation
- ✅ **Auto-Correction** – Repairs failed claims using evidence snippets (max 2 attempts)
- ✅ **Adversarial Testing** – Built-in ambiguous, trap, and conflicting-fact probes
- ✅ **Batch Processing** – Up to 50 queries per request
- ✅ **Persistent Memory** – Learned facts in `verified_facts.json` + failure patterns in `failure_patterns.json`
- ✅ **Multi-Domain Support** – Medical, legal, finance, academic, general with domain-specific confidence policies
- ✅ **Audit Logging** – Structured JSON audit trail with optional PostgreSQL backend
- ✅ **Caching** – In-memory TTL + optional Redis backing
- ✅ **Dashboard** – Browser-based reliability console at `/`
- ✅ **Cloud Fallback** – Automatic failover to secondary API key

---

## 📊 Current Performance Metrics

| Metric | Value |
|--------|-------|
| Historical runs analyzed | 14 |
| Total claims evaluated | 23 |
| TRUE outcomes | 9 (39.1%) |
| FALSE outcomes | 7 (30.4%) |
| UNCERTAIN outcomes | 7 (30.4%) |
| Hallucination-flagged runs | 6/14 (42.86%) |

📈 **Visual Dashboard:** See [progress_graph.md](progress_graph.md) for pie/bar charts and trend analysis.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Windows PowerShell 5.0+
- Internet access to MegaLLM & Groq APIs
- (Optional) Ollama + Phi-3 for local verification

### Installation

```powershell
# Clone or navigate to project
cd ai-hall

# Create virtual environment
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# If blocked, allow script execution for this session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Copy environment template:**
   ```powershell
   cp configs/api_keys.env.example configs/api_keys.env
   ```

2. **Edit `configs/api_keys.env` with your keys:**
   ```env
   MEGA_API_KEY=your_megallm_key
   MEGA_FALLBACK_API_KEY=your_secondary_key
   MEGA_API_URL=https://ai.megallm.io/v1/chat/completions
   GROQ_API_KEY=your_groq_key
   OLLAMA_URL=http://localhost:11434
   ```

### Run Locally

**Command-line mode:**
```powershell
python run_ai_hall.py "Who invented relativity?"
```

**Start API server (FastAPI):**
```powershell
python -m uvicorn src.ai_hall.api.main:app --reload --port 8001
```

Visit `http://localhost:8001` for the dashboard.

---

## 📡 API Routes

All endpoints require Bearer token authentication. The API server runs on `http://127.0.0.1:8001`.

### Core Endpoints

#### 1️⃣ **`POST /verify`** – Verify a single claim or answer text
Verifies text against evidence. Returns claim-level scores, hallucination types, and suggested corrections.

**Request:**
```json
{
  "text": "Albert Einstein formulated the theory of relativity in 1905.",
  "source_prompt": "Who invented relativity?",
  "domain": "academic",
  "team_id": "team-001",
  "metadata": {"user_id": "user-42"}
}
```

**Response:**
```json
{
  "request_id": "req-abc123",
  "overall_score": 92,
  "risk_level": "LOW",
  "model_used": "gpt-5",
  "latency_ms": 2341,
  "claims": [
    {
      "text": "Einstein formulated relativity in 1905",
      "status": "TRUE",
      "confidence": 98,
      "hallucination_type": "none",
      "explanation": "Supported by academic sources and historical records.",
      "supporting_evidence": [
        {
          "text": "Theory of Special Relativity published 1905",
          "source": "Wikipedia: Special Relativity"
        }
      ],
      "source_urls": ["https://en.wikipedia.org/wiki/Special_relativity"]
    }
  ]
}
```

---

#### 2️⃣ **`POST /explain`** – Full pipeline with explanation
Generates an answer, verifies it, and provides detailed explanations. Returns complete `PipelineRun` object.

**Request:**
```json
{
  "query": "What are the side effects of aspirin?",
  "domain": "medical",
  "team_id": "team-001",
  "answer_override": null
}
```

**Response:** *(See PipelineRun schema below)*

---

#### 3️⃣ **`POST /batch`** – Verify multiple queries at once
Process up to 50 queries in a single request. Returns individual results + aggregate reliability.

**Request:**
```json
{
  "queries": [
    {"query": "Is water boiling at 100°C?", "domain": "science"},
    {"query": "Who is the current US President?", "domain": "general"}
  ]
}
```

**Response:**
```json
{
  "runs": [
    { "summary": {...}, "claims": [...] },
    { "summary": {...}, "claims": [...] }
  ],
  "aggregate_reliability": 87,
  "high_risk_runs": 0
}
```

---

#### 4️⃣ **`POST /adversarial`** – Stress-test an answer
Runs the answer through adversarial probes: ambiguous, trap questions, and conflicting facts.

**Request:**
```json
{
  "query": "What is the capital of France?"
}
```

**Response:**
```json
{
  "original_run": {...},
  "adversarial_probes": [
    {
      "probe_type": "ambiguous",
      "probe_query": "Name all capitals in France",
      "run": {...}
    },
    {
      "probe_type": "conflicting_fact",
      "probe_query": "Is London the capital of France?",
      "run": {...}
    }
  ]
}
```

---

#### 5️⃣ **`POST /reports/export`** – Export results in multiple formats
Export verification results as JSON or Markdown.

**Request:**
```json
{
  "query": "What year did WWII end?",
  "format": "markdown"
}
```

**Response:**
```json
{
  "format": "markdown",
  "content": "# Verification Report\n\n## Query\nWhat year did WWII end?\n\n## Summary\n...\n"
}
```

---

#### 6️⃣ **`GET /memory/failures`** – Get hallucination patterns
Retrieve learned failure patterns from `memory/failure_patterns.json`.

**Response:**
```json
{
  "total_failures": 7,
  "patterns": [
    {
      "type": "fabrication",
      "frequency": 3,
      "examples": ["Date fabrication in STEM", "Author misattribution"]
    }
  ]
}
```

---

#### 7️⃣ **`GET /audit/recent`** – View audit log
Retrieve recent verification events (paginated, limit 1-200).

**Query Parameters:** `limit=20`

**Response:**
```json
{
  "events": [
    {
      "timestamp": "2025-05-02T14:22:15Z",
      "actor": "user-42",
      "team_id": "team-001",
      "query": "Who invented the telephone?",
      "overall_score": 89,
      "risk_level": "LOW"
    }
  ]
}
```

---

#### 8️⃣ **`GET /analytics/summary`** – Platform-wide analytics
Aggregate stats: total queries, hallucination rate, domain breakdown.

**Response:**
```json
{
  "total_queries": 156,
  "hallucination_rate": 0.234,
  "avg_reliability_score": 84.2,
  "by_domain": {
    "medical": {"count": 42, "hallucination_rate": 0.19},
    "legal": {"count": 38, "hallucination_rate": 0.21},
    "finance": {"count": 76, "hallucination_rate": 0.28}
  }
}
```

---

#### 9️⃣ **`GET /teams/{team_id}/analytics`** – Team-scoped analytics
Same as above but filtered by team.

**Response:** *(Same structure as /analytics/summary)*

---

#### 🔟 **`GET /healthz`** – Health check
Simple liveness probe.

**Response:**
```json
{
  "ok": true,
  "product": "AI Truth Layer"
}
```

---

## 📋 Core Data Models

### `PipelineRun`
Complete verification result for a single query.

```json
{
  "request_id": "req-abc123",
  "query": "...",
  "generation": {...},
  "claims": [...],
  "evidence": {...},
  "verification_results": [...],
  "summary": {
    "overall_reliability": 87,
    "risk_level": "LOW",
    "hallucination_detected": false,
    "total_claims": 4,
    "claims_verified": 3,
    "claims_failed": 1
  },
  "traces": {...}
}
```

### `VerifiedClaim`
Individual claim verification.

```json
{
  "text": "Einstein published Special Relativity in 1905",
  "status": "TRUE",
  "confidence": 98,
  "hallucination_type": "none",
  "explanation": "Supported by peer-reviewed sources",
  "suggested_correction": null,
  "supporting_evidence": [...],
  "source_urls": [...]
}
```

---

## 🔐 Authentication

All endpoints (except `/healthz`) require Bearer token:

```powershell
$headers = @{
  "Authorization" = "Bearer YOUR_TOKEN"
  "Content-Type" = "application/json"
}

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8001/explain" `
  -Method Post `
  -Headers $headers `
  -Body (@{query="..."} | ConvertTo-Json)
```

---

## 🧠 How Verification Works

### The 4-Model Ensemble

1. **NLI Verifier** → Semantic entailment score
2. **LLM Grounded Judge** → Reasoning-based judgment
3. **Local Phi3** → Independent on-device check
4. **Memory Verifier** → Historical contradiction lookup

**Consensus Rule:**  
- ✅ **TRUE** if 3+ models agree AND confidence ≥ 75%
- ❌ **FALSE** if 3+ models disagree OR contradiction detected
- ⚠️ **UNCERTAIN** otherwise

### Hallucination Types Detected

| Type | Description | Example |
|------|-------------|---------|
| **Fabrication** | Made-up facts not in sources | Inventing a date or statistic |
| **Misattribution** | Wrong author/creator | Crediting Newton to Einstein |
| **Overconfidence** | Unsupported certainty | "Definitely happened" without evidence |
| **Contradiction** | Conflicts with stored facts | Saying WWII ended 1944 when it's 1945 |
| **Unsupported Extrapolation** | Logical leap without basis | "X exists, so Y must exist" |

---

## 📁 Project Structure

```
ai-hall/
├── src/ai_hall/                    # Core application
│   ├── api/                        # FastAPI routes & models
│   ├── claims/                     # Claim extraction
│   ├── correction/                 # Auto-correction engine
│   ├── explanations/               # Explanation generation
│   ├── llm/                        # LLM client interfaces
│   ├── memory/                     # Failure tracking
│   ├── observability/              # Audit logging
│   ├── pipeline/                   # Orchestration logic
│   ├── retrievers/                 # Evidence retrieval (BM25 + dense)
│   ├── scoring/                    # Hallucination scoring
│   ├── storage/                    # Audit repository
│   └── verifiers/                  # Verification ensemble
├── services/                       # Legacy/utility services
├── sdk/                            # Client SDKs (Python, JavaScript)
├── tests/                          # Unit & integration tests
├── memory/                         # Persistent facts & failure patterns
├── logs/                           # Audit logs
├── configs/                        # API key configuration
└── run_ai_hall.py                  # CLI entry point
```

---

## 🔧 Environment Variables

| Variable | Required | Example |
|----------|----------|---------|
| `MEGA_API_KEY` | ✅ | `sk-mega-...` |
| `MEGA_API_URL` | ✅ | `https://ai.megallm.io/v1/chat/completions` |
| `GROQ_API_KEY` | ✅ | `gsk-...` |
| `OLLAMA_URL` | ❌ | `http://localhost:11434` |
| `MEGA_FALLBACK_API_KEY` | ❌ | `sk-mega-...` |
| `REDIS_URL` | ❌ | `redis://localhost:6379` |
| `POSTGRES_URL` | ❌ | `postgresql://user:pass@localhost/ai_hall` |
| `LOG_LEVEL` | ❌ | `DEBUG`, `INFO`, `WARNING` |

---

## 📈 Example: Full Verification Flow

```powershell
# 1. Start the server
python -m uvicorn src.ai_hall.api.main:app --reload --port 8001

# 2. Verify a claim
$body = @{
    query = "Did Einstein win the Nobel Prize?"
    domain = "academic"
} | ConvertTo-Json

$response = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8001/explain" `
  -Method Post `
  -Headers @{"Authorization"="Bearer token"} `
  -ContentType "application/json" `
  -Body $body

# 3. Inspect results
$response.summary
$response.claims | ForEach-Object { Write-Host "$($_.text): $($_.status)" }
```

---

Or (after activation):

```powershell
python pipeline/main_pipeline.py
```

## 4b) Run the new production pipeline (typed + API-ready)

Run once (prints a full JSON artifact):

```powershell
python .\run_ai_hall.py "Who invented relativity?"
```

Run the API server:

```powershell
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn ai_hall.api.main:app --app-dir .\src --host 0.0.0.0 --port 8000
```

Optional enterprise environment variables:

```env
AI_HALL_API_KEYS=admin-secret:admin,research-key:analyst:research,viewer-key:viewer:research
AI_HALL_REQUIRE_AUTH=true
AI_HALL_REDIS_URL=redis://localhost:6379/0
AI_HALL_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_hall
```

Then call:

```powershell
curl -X POST http://localhost:8000/explain -H "Content-Type: application/json" -d "{ \"query\": \"Who invented relativity?\" }"
```

Use a domain-specific verification mode:

```powershell
curl -X POST http://localhost:8000/explain -H "Content-Type: application/json" -d "{ \"query\": \"Is aspirin safe for everyone?\", \"domain\": \"medical\" }"
```

Run adversarial probes:

```powershell
curl -X POST http://localhost:8000/adversarial -H "Content-Type: application/json" -d "{ \"query\": \"Who invented relativity?\", \"domain\": \"academic\" }"
```

Run batch verification:

```powershell
curl -X POST http://localhost:8000/batch -H "Content-Type: application/json" -d "{ \"queries\": [{ \"query\": \"Who invented relativity?\" }, { \"query\": \"When was penicillin discovered?\", \"domain\": \"academic\" }] }"
```

Export a report:

```powershell
curl -X POST http://localhost:8000/reports/export -H "Content-Type: application/json" -d "{ \"query\": \"Who invented relativity?\", \"format\": \"markdown\" }"
```

Inspect learned failure patterns:

```powershell
curl http://localhost:8000/memory/failures
```

Inspect analytics and recent audit events:

```powershell
curl http://localhost:8000/analytics/summary
curl http://localhost:8000/audit/recent
curl http://localhost:8000/teams/research/analytics
```

## 5) What output to expect

The script prints:
- `LLM Call Info` (provider/model/usage)
- `LLM Tokens Used`
- Generated answer
- Extracted claims
- Structured verification object for each claim (`claim/status/confidence/reason`)
- Final summary object (`hallucination/reason/notes/error_type/explanation/metrics`)
- Explicit console blocks: `--- ERROR TYPE ---` and `--- EXPLANATION ---`

A healthy run should show:
- `provider: megallm` for answer generation
- verification outputs returned by Groq
- V1 and V2 are fused per claim before final hallucination decision

## 6) How to check what is happening

Use these checks every run:

1. **Provider and model check**
  - Look at `LLM Call Info`.
  - Expect `provider: megallm` and one model from `MEGA_MODELS`.
  - If key failover happens, you will see a warning: `Switching MegaLLM from primary key to fallback...`.

2. **Token usage check**
  - Look at `LLM Tokens Used` in terminal output.
  - Also inspect `LLM Call Info["usage"]` for token breakdown.

3. **Verification schema check**
  - Each claim should print as:
    - `status: TRUE | FALSE | UNCERTAIN`
    - `confidence: 0.0..1.0`
    - `reason: ...`

4. **Final decision check**
  - Final output includes:
    - `hallucination`
    - `reason`
    - `notes`
    - `error_type`
    - `explanation`
    - `metrics`

Decision rules:
- Any `FALSE` claim => hallucination `True`
- `UNCERTAIN` claims > 50% => hallucination `True`
- Otherwise => hallucination `False`

Hard-gate rules:
- If any fused claim is not `TRUE`, output is blocked from final return.
- Pipeline runs correction + re-verification for up to 2 attempts.
- If attempts are exhausted, pipeline returns the best corrected fallback answer (never empty) and logs a safety warning when unresolved `UNCERTAIN` statuses remain.

Memory consistency rules:
- Verified claims are persisted in `memory/verified_facts.json` after a fully `TRUE` run.
- New claims are checked against previous verified facts before verification.
- If contradiction is detected, the claim is marked `FALSE` immediately.

Verified memory rules:
- Runtime memory store (`services/memory/memory_store.py`) keeps only claims whose fused status is `TRUE`.
- `FALSE` and `UNCERTAIN` claims are never stored.
- Last 5 verified memory items are injected into answer generation context.

## 7) Troubleshooting

### MegaLLM TLS / SSL handshake failure
If you see `SSLEOFError` or `MegaLLM TLS handshake failed`:
1. Confirm `MEGA_API_URL` is exactly correct in `configs/api_keys.env`.
2. Test DNS/port:
   ```powershell
   Resolve-DnsName ai.megallm.io
   Test-NetConnection ai.megallm.io -Port 443
   ```
3. Retry on a different network/VPN if your current network filters TLS.

### Wrong provider used
Check `LLM Call Info` in output:
- generation must show `provider: megallm`
- verification is handled in `services/verifier/groq_verifier.py`

### Models unavailable
If Mega returns model unavailable errors:
1. Keep `MEGA_MODELS` set to working models in `configs/api_keys.env`.
2. If needed, test available models quickly via the Mega models endpoint.

## 8) Project entry points

- `pipeline/main_pipeline.py` — main orchestration
- `services/llm_generator/generate.py` — MegaLLM generation
- `services/llm_generator/client.py` — MegaLLM HTTP client
- `services/llm_generator/fallback.py` — model fallback helpers
- `services/claim_extractor/extractor.py` — claim extraction
- `services/verifier/groq_verifier.py` — Groq verification
- `services/verifier/local_verifier.py` — local Phi-3 verification
- `services/verifier/memory_consistency.py` — verified-fact storage and contradiction checks
- `services/memory/memory_store.py` — runtime verified-claim memory store used by generation
- `services/corrector/correct.py` — correction engine used between verification attempts
- `services/aggregator/aggregate.py` — scoring aggregation logic
- `services/detector/hallucination.py` — detector wrapper
- `services/classifier/failure_classifier.py` — failure type classifier
- `services/explainer/explain.py` — error explainer
- `models/schemas.py` — shared structured schema(s)
- `src/ai_hall/pipeline/orchestrator.py` — typed production pipeline
- `src/ai_hall/api/main.py` — FastAPI app
- `src/ai_hall/api/routes.py` — `/explain`, `/batch`, `/adversarial`, export, analytics, and audit routes
- `src/ai_hall/api/dashboard.py` — browser-based reliability console
- `src/ai_hall/retrievers/ranking.py` — real-time evidence/source ranking
- `src/ai_hall/detection.py` — hallucination type classifier
- `src/ai_hall/domains.py` — domain-specific confidence policies
- `src/ai_hall/memory/failures.py` — recurring failure memory
- `src/ai_hall/evaluation/adversarial.py` — adversarial probe generation
- `src/ai_hall/storage/audit_repository.py` — audit persistence with file/PostgreSQL fallback
- `src/ai_hall/cache.py` — in-memory and Redis-backed cache layer
