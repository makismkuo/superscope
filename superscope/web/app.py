"""SuperScope Web UI — FastAPI with http.server fallback.

Usage:
    python -m superscope.web.app
    # or via CLI: superscope web
"""

import html
import json
import os
import sys
import threading
import time
import webbrowser
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Try to import FastAPI / uvicorn; fall back to http.server
# ---------------------------------------------------------------------------
try:
    from fastapi import FastAPI, Query, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

try:
    import uvicorn

    _HAS_UVICORN = True
except ImportError:
    _HAS_UVICORN = False

# ---------------------------------------------------------------------------
# Core imports
# ---------------------------------------------------------------------------
from superscope import __version__


# ---------------------------------------------------------------------------
# HTML template for the web UI
# ---------------------------------------------------------------------------
WEB_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SuperScope — OSINT Username Scanner</title>
<style>
  :root { --primary: #0d9488; --primary-dark: #0f766e; --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --text-dim: #94a3b8; --border: #334155; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; min-height: 100vh; }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
  header { text-align: center; padding: 30px 0; border-bottom: 1px solid var(--border); margin-bottom: 30px; }
  header h1 { font-size: 2.2em; color: var(--primary); }
  header p { color: var(--text-dim); margin-top: 8px; }
  .card { background: var(--card); border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid var(--border); }
  .card h2 { font-size: 1.2em; margin-bottom: 16px; color: var(--primary); }
  label { display: block; margin-bottom: 6px; color: var(--text-dim); font-size: 0.9em; }
  input, select, textarea { width: 100%; padding: 10px 14px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 1em; margin-bottom: 16px; }
  input:focus, select:focus { outline: none; border-color: var(--primary); }
  .btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 24px; border: none; border-radius: 8px; font-size: 1em; cursor: pointer; transition: all 0.2s; font-weight: 500; }
  .btn-primary { background: var(--primary); color: white; }
  .btn-primary:hover { background: var(--primary-dark); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-sm { padding: 6px 14px; font-size: 0.85em; }
  .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
  .btn-outline:hover { border-color: var(--primary); color: var(--primary); }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .form-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
  .checkbox-row { display: flex; gap: 20px; margin-bottom: 16px; flex-wrap: wrap; }
  .checkbox-row label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
  .checkbox-row input[type=checkbox] { width: auto; margin: 0; }
  #progress { display: none; }
  #progress-bar { width: 100%; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; margin: 12px 0; }
  #progress-fill { height: 100%; width: 0; background: var(--primary); transition: width 0.3s; border-radius: 3px; }
  #progress-text { color: var(--text-dim); font-size: 0.9em; }
  #progress-detail { color: var(--text-dim); font-size: 0.85em; margin-top: 4px; }
  #results { display: none; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); }
  th { color: var(--text-dim); font-weight: 500; text-transform: uppercase; font-size: 0.8em; letter-spacing: 0.5px; }
  tr:hover { background: rgba(13, 148, 136, 0.05); }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 500; }
  .badge-found { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
  .badge-not-found { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
  .badge-error { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
  .export-bar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
  #summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }
  .stat-card { background: var(--card); border-radius: 10px; padding: 18px; text-align: center; border: 1px solid var(--border); }
  .stat-card .num { font-size: 2em; font-weight: 700; color: var(--primary); }
  .stat-card .label { font-size: 0.85em; color: var(--text-dim); margin-top: 4px; }
  .stat-card.found .num { color: #22c55e; }
  .stat-card.not-found .num { color: #94a3b8; }
  .stat-card.error .num { color: #ef4444; }
  .ai-section { display: none; }
  .ai-section.show { display: block; }
  #ai-summary { white-space: pre-wrap; line-height: 1.7; }
  .tooltip { position: relative; cursor: help; border-bottom: 1px dotted var(--text-dim); }
  #no-results { text-align: center; padding: 60px 20px; color: var(--text-dim); display: none; }
  #no-results.show { display: block; }
  .graph-container { width: 100%; height: 400px; background: var(--bg); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: var(--text-dim); margin-top: 12px; border: 1px solid var(--border); }
  @media (max-width: 768px) {
    .form-row, .form-row-3 { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🔭 SuperScope</h1>
    <p>Enhanced OSINT Username Scanner v""" + __version__ + """</p>
  </header>

  <div class="card">
    <h2>New Scan</h2>
    <form id="scan-form" onsubmit="return startScan(event)">
      <label for="username">Username</label>
      <input type="text" id="username" placeholder="e.g. johndoe" required>

      <label for="platforms">Platforms (comma-separated, leave empty for all)</label>
      <input type="text" id="platforms" placeholder="e.g. github, twitter, weibo">

      <div class="form-row">
        <div>
          <label for="timeout">Timeout (seconds)</label>
          <input type="number" id="timeout" value="15" min="5" max="120">
        </div>
        <div>
          <label for="proxy">Proxy URL (optional)</label>
          <input type="text" id="proxy" placeholder="socks5://127.0.0.1:9050">
        </div>
      </div>

      <div class="form-row-3">
        <div>
          <label for="country">Country filter</label>
          <input type="text" id="country" placeholder="e.g. cn, global">
        </div>
        <div>
          <label for="tags">Tags filter</label>
          <input type="text" id="tags" placeholder="e.g. social, china">
        </div>
        <div>
          <label for="top">Top platforms</label>
          <input type="number" id="top" placeholder="e.g. 50">
        </div>
      </div>

      <div class="checkbox-row">
        <label><input type="checkbox" id="use-browser"> Use browser engine</label>
        <label><input type="checkbox" id="use-ai"> AI analysis</label>
        <label><input type="checkbox" id="tor-mode"> Tor mode</label>
      </div>

      <button type="submit" class="btn btn-primary" id="scan-btn">🔍 Start Scan</button>
    </form>
  </div>

  <div id="progress">
    <div class="card">
      <h2>Scanning...</h2>
      <div id="progress-bar"><div id="progress-fill"></div></div>
      <div id="progress-text">Initializing...</div>
      <div id="progress-detail"></div>
    </div>
  </div>

  <div id="results">
    <div id="summary-cards"></div>

    <div class="card">
      <h2>Results</h2>
      <div class="export-bar">
        <button class="btn btn-sm btn-outline" onclick="exportJSON()">📥 Export JSON</button>
        <button class="btn btn-sm btn-outline" onclick="exportHTML()">📥 Export HTML</button>
        <button class="btn btn-sm btn-outline" onclick="window.print()">🖨️ Print / PDF</button>
      </div>
      <div id="table-container"></div>
    </div>

    <div class="card ai-section" id="ai-section">
      <h2>🤖 AI Analysis</h2>
      <div id="ai-summary"></div>
      <div id="ai-risk" style="margin-top: 12px;"></div>
    </div>

    <div class="card">
      <h2>Network Graph</h2>
      <div class="graph-container" id="graph-container">
        ⚠️ Relationship graph requires a canvas-capable browser.<br>
        <small style="margin-top: 8px; display: block;">Platforms where the username was found are connected.</small>
      </div>
    </div>

    <div id="no-results">
      <h3>No results yet</h3>
      <p>Run a scan to see results here.</p>
    </div>
  </div>
</div>

<script>
let _scanData = null;

async function startScan(e) {
  e.preventDefault();

  const btn = document.getElementById('scan-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Scanning...';

  document.getElementById('progress').style.display = 'block';
  document.getElementById('results').style.display = 'none';
  document.getElementById('no-results').classList.remove('show');

  const username = document.getElementById('username').value.trim();
  const platforms = document.getElementById('platforms').value.trim();
  const timeout = parseInt(document.getElementById('timeout').value) || 15;
  const proxy = document.getElementById('proxy').value.trim();
  const country = document.getElementById('country').value.trim();
  const tags = document.getElementById('tags').value.trim();
  const top = document.getElementById('top').value.trim();
  const useBrowser = document.getElementById('use-browser').checked;
  const useAI = document.getElementById('use-ai').checked;
  const torMode = document.getElementById('tor-mode').checked;

  const params = new URLSearchParams({ username });
  if (platforms) params.set('platforms', platforms);
  params.set('timeout', String(timeout));
  if (proxy) params.set('proxy', proxy);
  if (country) params.set('country', country);
  if (tags) params.set('tags', tags);
  if (top) params.set('top', top);
  if (useBrowser) params.set('browser', '1');
  if (useAI) params.set('ai', '1');
  if (torMode) params.set('tor', '1');

  try {
    const resp = await fetch('/api/scan?' + params.toString());
    if (!resp.ok) {
      const err = await resp.text();
      throw new Error(err);
    }
    _scanData = await resp.json();
    renderResults(_scanData);
  } catch (err) {
    document.getElementById('progress-text').textContent = '❌ Error: ' + err.message;
    document.getElementById('progress-fill').style.width = '0%';
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 Start Scan';
  }
}

function renderResults(data) {
  document.getElementById('progress').style.display = 'none';
  document.getElementById('results').style.display = 'block';

  const results = data.results || [];
  const found = results.filter(r => r.status === 'found');
  const notFound = results.filter(r => r.status === 'not_found');
  const errors = results.filter(r => r.status === 'error');

  // Summary cards
  document.getElementById('summary-cards').innerHTML = `
    <div class="stat-card found"><div class="num">${found.length}</div><div class="label">Found</div></div>
    <div class="stat-card not-found"><div class="num">${notFound.length}</div><div class="label">Not Found</div></div>
    <div class="stat-card error"><div class="num">${errors.length}</div><div class="label">Errors</div></div>
    <div class="stat-card"><div class="num">${results.length}</div><div class="label">Total Checked</div></div>
  `;

  // Table
  if (results.length === 0) {
    document.getElementById('table-container').innerHTML = '<p style="text-align:center;color:var(--text-dim);padding:40px;">No results returned.</p>';
  } else {
    let table = '<table><thead><tr><th>Platform</th><th>Status</th><th>Name</th><th>Bio</th><th>Location</th><th>URL</th></tr></thead><tbody>';
    for (const r of results) {
      const d = r.data || {};
      const statusBadge = r.status === 'found' ? '<span class="badge badge-found">✓ Found</span>'
        : r.status === 'not_found' ? '<span class="badge badge-not-found">—</span>'
        : '<span class="badge badge-error">✗ ' + htmlEscape(r.error_message || 'Error') + '</span>';
      table += '<tr>';
      table += '<td><strong>' + htmlEscape(r.platform) + '</strong></td>';
      table += '<td>' + statusBadge + '</td>';
      table += '<td>' + htmlEscape(d.name || '') + '</td>';
      table += '<td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + htmlEscape(d.bio || '') + '</td>';
      table += '<td>' + htmlEscape(d.location || '') + '</td>';
      table += '<td>' + (d.url ? '<a href="' + htmlEscape(d.url) + '" target="_blank" style="color:var(--primary);">link</a>' : '') + '</td>';
      table += '</tr>';
    }
    table += '</tbody></table>';
    document.getElementById('table-container').innerHTML = table;
  }

  // AI section
  const aiSection = document.getElementById('ai-section');
  if (data.ai_report) {
    aiSection.classList.add('show');
    document.getElementById('ai-summary').textContent = data.ai_report.summary || 'No summary.';
    const risk = data.ai_report.risk_assessment || 'unknown';
    const riskColor = risk === 'low' ? '#22c55e' : risk === 'medium' ? '#eab308' : '#ef4444';
    document.getElementById('ai-risk').innerHTML = 'Risk Assessment: <span style="color:' + riskColor + ';font-weight:600;">' + risk.toUpperCase() + '</span>';
  } else if (data.ai === false || data.ai === 'false') {
    aiSection.classList.remove('show');
  } else {
    aiSection.classList.remove('show');
  }

  // Graph placeholder with simple ASCII graph
  const graphEl = document.getElementById('graph-container');
  if (found.length > 1) {
    let graphHTML = '<div style="font-family:monospace;font-size:0.85em;padding:20px;text-align:left;line-height:1.8;">';
    graphHTML += '📡 Network Connections<br><br>';
    for (let i = 0; i < Math.min(found.length, 15); i++) {
      const f = found[i];
      graphHTML += '  ● ' + htmlEscape(f.platform);
      if (i < found.length - 1) graphHTML += ' ─── ';
      graphHTML += '<br>';
    }
    if (found.length > 15) graphHTML += '  ⋯ and ' + (found.length - 15) + ' more<br>';
    graphHTML += '<br><small style="color:var(--text-dim);">' + found.length + ' platforms found. ' + (data.correlations ? data.correlations.length + ' correlation groups.' : '') + '</small>';
    graphHTML += '</div>';
    graphEl.innerHTML = graphHTML;
  } else {
    graphEl.innerHTML = '<div style="color:var(--text-dim);text-align:center;">Not enough found platforms to build a relationship graph.</div>';
  }
}

function htmlEscape(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function exportJSON() {
  if (!_scanData) return;
  const blob = new Blob([JSON.stringify(_scanData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'superscope-report.json';
  a.click();
  URL.revokeObjectURL(url);
}

function exportHTML() {
  if (!_scanData) return;
  let html = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>SuperScope Report</title>';
  html += '<style>body{font-family:sans-serif;padding:20px;max-width:1200px;margin:0 auto;}';
  html += 'table{width:100%;border-collapse:collapse;}';
  html += 'th,td{padding:8px 12px;border:1px solid #ddd;text-align:left;}';
  html += 'th{background:#f5f5f5;}.found{color:green;}.not-found{color:gray;}.error{color:red;}</style></head><body>';
  html += '<h1>SuperScope Report</h1>';
  html += '<p>Username: ' + htmlEscape(_scanData.username) + '</p>';
  html += '<p>Scanned at: ' + (_scanData.scanned_at || new Date().toISOString()) + '</p>';
  html += '<table><thead><tr><th>Platform</th><th>Status</th><th>Name</th><th>Bio</th><th>URL</th></tr></thead><tbody>';
  for (const r of (_scanData.results || [])) {
    const d = r.data || {};
    html += '<tr><td>' + htmlEscape(r.platform) + '</td>';
    html += '<td class="' + r.status + '">' + htmlEscape(r.status) + '</td>';
    html += '<td>' + htmlEscape(d.name || '') + '</td>';
    html += '<td>' + htmlEscape(d.bio || '') + '</td>';
    html += '<td>' + htmlEscape(d.url || '') + '</td></tr>';
  }
  html += '</tbody></table>';
  if (_scanData.ai_report) {
    html += '<h2>AI Analysis</h2><p>' + htmlEscape(_scanData.ai_report.summary) + '</p>';
  }
  html += '</body></html>';
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'superscope-report.html';
  a.click();
  URL.revokeObjectURL(url);
}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
if _HAS_FASTAPI:

    app = FastAPI(title="SuperScope", version=__version__)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return WEB_HTML

    @app.get("/api/scan")
    async def api_scan(
        username: str = Query(...),
        platforms: Optional[str] = Query(None),
        timeout: int = Query(15),
        proxy: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        tags: Optional[str] = Query(None),
        top: Optional[int] = Query(None),
        browser: Optional[str] = Query(None),
        ai: Optional[str] = Query(None),
        tor: Optional[str] = Query(None),
    ) -> Dict[str, Any]:
        """Run a scan and return JSON results."""
        return await _run_scan(
            username=username,
            platforms=platforms,
            timeout=timeout,
            proxy=proxy,
            country=country,
            tags=tags,
            top=top,
            use_browser=bool(browser),
            use_ai=bool(ai),
            use_tor=bool(tor),
        )


# ---------------------------------------------------------------------------
# http.server fallback
# ---------------------------------------------------------------------------
def _run_http_server(host: str, port: int, open_browser: bool) -> None:
    """Run a minimal http.server with the SuperScope web UI."""

    class SuperScopeHandler(BaseHTTPRequestHandler):  # type: ignore[name-defined]
        """HTTP request handler for the web UI."""

        def do_GET(self) -> None:
            if self.path == "/" or self.path == "/index.html":
                self._serve_html()
            elif self.path.startswith("/api/scan"):
                self._handle_scan()
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")

        def _serve_html(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WEB_HTML.encode("utf-8"))

        def _handle_scan(self) -> None:
            from urllib.parse import urlparse, parse_qs

            qs = parse_qs(urlparse(self.path).query)
            username = qs.get("username", [""])[0]
            if not username:
                self._send_json({"error": "username is required"}, 400)
                return

            import asyncio

            result = asyncio.run(
                _run_scan(
                    username=username,
                    platforms=qs.get("platforms", [None])[0],
                    timeout=int(qs.get("timeout", ["15"])[0]),
                    proxy=qs.get("proxy", [None])[0],
                    country=qs.get("country", [None])[0],
                    tags=qs.get("tags", [None])[0],
                    top=int(qs.get("top", ["0"])[0]) if qs.get("top", ["0"])[0] else None,
                    use_browser=bool(qs.get("browser", [""])[0]),
                    use_ai=bool(qs.get("ai", [""])[0]),
                    use_tor=bool(qs.get("tor", [""])[0]),
                )
            )
            self._send_json(result)

        def _send_json(self, data: Any, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

    import http.server

    server = http.server.HTTPServer((host, port), SuperScopeHandler)
    print(f"SuperScope Web UI at http://{host}:{port}")

    if open_browser:
        webbrowser.open(f"http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


# ---------------------------------------------------------------------------
# Shared scan runner (used by both FastAPI and http.server)
# ---------------------------------------------------------------------------
async def _run_scan(
    username: str,
    platforms: Optional[str] = None,
    timeout: int = 15,
    proxy: Optional[str] = None,
    country: Optional[str] = None,
    tags: Optional[str] = None,
    top: Optional[int] = None,
    use_browser: bool = False,
    use_ai: bool = False,
    use_tor: bool = False,
) -> Dict[str, Any]:
    """Execute a scan and return serializable results."""
    from superscope.db.sites import SiteDatabase
    from superscope.engine.checker import CheckerEngine, CheckStatus

    db = SiteDatabase()

    # Determine which platforms to scan
    platform_names = None
    if platforms:
        platform_names = [p.strip() for p in platforms.split(",") if p.strip()]

    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    sites = db.filter(names=platform_names, tags=tag_list, country=country, top=top)

    if not sites:
        return {
            "username": username,
            "results": [],
            "ai_report": None,
            "correlations": [],
            "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_platforms": 0,
            "error": "No platforms matched the given filters",
        }

    all_platforms = [s["name"] for s in sites]
    http_platforms = [s["name"] for s in sites if s.get("engine", "http") == "http"]
    browser_platforms = [s["name"] for s in sites if s.get("engine") == "browser"]

    # Build checker engine
    checker = CheckerEngine(timeout=timeout, proxy_url=proxy or None)
    all_results: List[Dict[str, Any]] = []

    # Run HTTP checks
    if http_platforms:
        http_results = await checker.check_many(http_platforms, username)
        for plat, res in http_results.items():
            all_results.append(_serialize_result(res))

    # Run browser checks
    if use_browser and browser_platforms:
        try:
            from superscope.engine.browser import BrowserEngine

            browser_engine = BrowserEngine(
                headless=True,
                proxy_url=proxy or None,
                timeout=timeout * 1000,
            )
            for plat in browser_platforms:
                res = await browser_engine.check(plat, username)
                all_results.append(_serialize_result(res))
            await browser_engine.close()
        except ImportError:
            for plat in browser_platforms:
                all_results.append({
                    "platform": plat,
                    "username": username,
                    "status": "error",
                    "error_message": "Browser engine not installed (pip install superscope[playwright])",
                })

    # Run correlations
    correlations: List[Dict[str, Any]] = []
    try:
        from superscope.analysis.correlator import Correlator
        from superscope.engine.checker import CheckResult

        check_results = [
            _deserialize_result(r) for r in all_results
            if r["status"] == "found"
        ]
        if len(check_results) >= 2:
            correlator = Correlator()
            corr_results = correlator.correlate(check_results)
            correlations = [
                {
                    "platforms": c.platforms,
                    "confidence": c.confidence,
                    "matched_by": c.matched_by,
                    "matched_platforms": c.matched_platforms,
                }
                for c in corr_results
            ]
    except Exception:
        pass

    # AI analysis
    ai_report = None
    if use_ai:
        try:
            from superscope.analysis.ai_report import AiReporter

            reporter = AiReporter()
            if reporter.available:
                report = await reporter.analyze(all_results, correlations, username)
                ai_report = {
                    "summary": report.summary,
                    "risk_assessment": report.risk_assessment,
                    "platform_highlights": report.platform_highlights,
                    "recommendations": report.recommendations,
                }
        except Exception:
            ai_report = {"summary": "AI analysis unavailable", "risk_assessment": "unknown"}

    return {
        "username": username,
        "results": all_results,
        "ai_report": ai_report,
        "correlations": correlations,
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_platforms": len(all_platforms),
    }


def _serialize_result(res: Any) -> Dict[str, Any]:
    """Serialize a CheckResult to a plain dict."""
    if hasattr(res, "platform"):
        data = res.data
        return {
            "platform": res.platform,
            "username": res.username,
            "status": res.status.value if hasattr(res.status, "value") else str(res.status),
            "data": {
                "name": data.name if data else None,
                "avatar_url": data.avatar_url if data else None,
                "bio": data.bio if data else None,
                "email": data.email if data else None,
                "location": data.location if data else None,
                "url": data.url if data else None,
                "followers": data.followers if data else None,
                "following": data.following if data else None,
            } if data else None,
            "error_message": res.error_message,
            "response_time_ms": res.response_time_ms,
            "http_status": res.http_status,
        }
    return dict(res)


def _deserialize_result(d: Dict[str, Any]) -> Any:
    """Deserialize a dict back to a CheckResult."""
    from superscope.engine.checker import CheckResult, CheckStatus, ExtractedData

    data = d.get("data")
    extracted = None
    if data:
        extracted = ExtractedData(
            name=data.get("name"),
            avatar_url=data.get("avatar_url"),
            bio=data.get("bio"),
            email=data.get("email"),
            location=data.get("location"),
            url=data.get("url"),
        )
    return CheckResult(
        platform=d["platform"],
        username=d["username"],
        status=CheckStatus(d["status"]) if "status" in d else CheckStatus.ERROR,
        data=extracted,
        error_message=d.get("error_message"),
    )


# ---------------------------------------------------------------------------
# CLI / standalone entry point
# ---------------------------------------------------------------------------
def run_web_server(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True) -> None:
    """Start the web UI server."""
    if _HAS_FASTAPI and _HAS_UVICORN:
        print(f"Starting SuperScope Web UI at http://{host}:{port}")
        if open_browser:
            webbrowser.open(f"http://{host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="info")
    else:
        _run_http_server(host, port, open_browser)


if __name__ == "__main__":
    import sys

    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    run_web_server(host, port)
