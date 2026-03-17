# AI Hall Pipeline

A small fact-checking pipeline with this stack:
- **Answer generation:** MegaLLM API (cloud)
- **Claim extraction:** atomic claim extraction
- **Verification:** Groq `llama-3.1-8b-instant`
- **Decisioning:** Aggregator + Detector + Failure Classifier + Explainer

## 1) Prerequisites

- Python 3.11+
- Windows PowerShell (examples below use PowerShell)
- Internet access to:
  - `https://ai.megallm.io`
  - `https://api.groq.com`

## 2) Setup

From project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3) Configure API keys

Edit `configs/api_keys.env`:

```env
MEGA_API_KEY=your_megallm_key
MEGA_FALLBACK_API_KEY=your_secondary_megallm_key
MEGA_API_URL=https://ai.megallm.io/v1/chat/completions
MEGA_MODELS=gpt-5,claude-sonnet-4-5-20250929,openai-gpt-oss-20b
GROQ_API_KEY=your_groq_key
```

Notes:
- `MEGA_API_URL` should match your MegaLLM dashboard/docs endpoint.
- `MEGA_FALLBACK_API_KEY` is optional and is used if the primary key path fails.
- Keep keys private and never commit real keys.

## 4) Run the pipeline

Always use the virtual environment interpreter:

```powershell
c:/Users/param/Documents/Code/ai-hall/.venv/Scripts/python.exe c:/Users/param/Documents/Code/ai-hall/pipeline/main_pipeline.py
```

Or (after activation):

```powershell
python pipeline/main_pipeline.py
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
- low-confidence (`confidence < 0.7`) claims > 50% => hallucination `True`
- Otherwise => hallucination `False`

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
- `services/aggregator/aggregate.py` — scoring aggregation logic
- `services/detector/hallucination.py` — detector wrapper
- `services/classifier/failure_classifier.py` — failure type classifier
- `services/explainer/explain.py` — error explainer
- `models/schemas.py` — shared structured schema(s)
