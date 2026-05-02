from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ai_hall.config import get_settings


router = APIRouter()


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Hall Reliability Console</title>
  <style>
    :root { color-scheme: light; font-family: Inter, Segoe UI, Arial, sans-serif; }
    body { margin: 0; background: #f5f7f8; color: #172026; }
    header { background: #172026; color: white; padding: 18px 28px; display: flex; align-items: center; justify-content: space-between; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px; display: grid; gap: 18px; }
    section, form { background: white; border: 1px solid #d9e0e4; border-radius: 8px; padding: 18px; }
    textarea { width: 100%; min-height: 110px; resize: vertical; border: 1px solid #aebbc3; border-radius: 6px; padding: 12px; font: inherit; box-sizing: border-box; }
    select, button { height: 38px; border-radius: 6px; border: 1px solid #8fa0aa; background: white; padding: 0 12px; font: inherit; }
    button { background: #0f6b5f; color: white; border-color: #0f6b5f; cursor: pointer; }
    .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 12px; }
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
    .metric { border-left: 4px solid #0f6b5f; background: #f8fbfb; padding: 12px; border-radius: 6px; }
    .metric strong { display: block; font-size: 28px; line-height: 1.1; }
    .claim { border-top: 1px solid #e1e7ea; padding: 14px 0; }
    .claim:first-child { border-top: 0; }
    .badge { display: inline-block; border-radius: 999px; padding: 3px 8px; background: #e8eef1; font-size: 12px; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #101820; color: #eef7f6; padding: 14px; border-radius: 6px; }
  </style>
</head>
<body>
  <header>
    <strong>AI Hall Reliability Console</strong>
    <span>Evidence, risk, and explainability</span>
  </header>
  <main>
    <form id="form">
      <textarea id="query">Who invented relativity?</textarea>
      <div class="row">
        <select id="domain">
          <option value="">General</option>
          <option>medical</option>
          <option>legal</option>
          <option>finance</option>
          <option>academic</option>
        </select>
        <button type="submit">Verify</button>
      </div>
    </form>
    <section>
      <div class="metrics" id="metrics"></div>
      <div id="claims"></div>
    </section>
    <section><pre id="raw">Run a verification to see the full trust artifact.</pre></section>
  </main>
  <script>
    const form = document.querySelector('#form');
    const metrics = document.querySelector('#metrics');
    const claims = document.querySelector('#claims');
    const raw = document.querySelector('#raw');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      raw.textContent = 'Verifying...';
      const res = await fetch('/explain', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: document.querySelector('#query').value, domain: document.querySelector('#domain').value || null})
      });
      const data = await res.json();
      metrics.innerHTML = [
        ['Reliability', `${data.summary.overall_reliability}/100`],
        ['Risk', data.summary.risk_level],
        ['Verified', data.summary.claims_verified],
        ['Failed', data.summary.claims_failed]
      ].map(([k,v]) => `<div class="metric"><span>${k}</span><strong>${v}</strong></div>`).join('');
      claims.innerHTML = data.analyses.map(a => `<div class="claim"><span class="badge">${a.verification.state}</span> <span class="badge">${a.hallucination?.type || 'none'}</span><p>${a.claim.text}</p><p>${a.explanation?.explanation_text || ''}</p></div>`).join('');
      raw.textContent = JSON.stringify(data, null, 2);
    });
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> HTMLResponse:
    if not get_settings().dashboard_enabled:
        return HTMLResponse("Dashboard disabled", status_code=404)
    return HTMLResponse(HTML)
