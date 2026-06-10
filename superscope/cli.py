"""SuperScope CLI — Click-based command-line interface.

Commands:
    scan        Scan a username across supported platforms
    web         Launch the web UI
    db-update   Update platform definitions from remote registry
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import click
import rich.box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from superscope import __version__

console = Console()


# ===================================================================
# Main group
# ===================================================================

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="superscope")
def main() -> None:
    """SuperScope — Enhanced OSINT username scanner.

    Scan usernames across 200+ platforms, correlate results, and
    generate intelligence reports. Supports Chinese platforms like
    Weibo, Zhihu, Xiaohongshu, and more.
    """


# ===================================================================
# scan command
# ===================================================================

@main.command()
@click.argument("usernames", nargs=-1, required=True)
@click.option(
    "-p", "--platforms",
    default=None,
    help="Comma-separated list of platforms to scan (default: all).",
)
@click.option(
    "--tags",
    default=None,
    help="Comma-separated tags to filter platforms (e.g. 'social,china').",
)
@click.option(
    "--country",
    default=None,
    help="Country code to filter platforms (e.g. 'cn', 'global').",
)
@click.option(
    "--top",
    type=int,
    default=None,
    help="Only check top N platforms by rank.",
)
@click.option(
    "-t", "--timeout",
    type=int,
    default=15,
    show_default=True,
    help="Request timeout in seconds.",
)
@click.option(
    "-r", "--retries",
    type=int,
    default=3,
    show_default=True,
    help="Number of retries per platform on failure.",
)
@click.option(
    "--proxy",
    default=None,
    help="Proxy URL (e.g. socks5://127.0.0.1:9050, http://proxy:8080).",
)
@click.option(
    "--tor/--no-tor",
    default=False,
    help="Auto-detect and route through Tor SOCKS5 proxy.",
)
@click.option(
    "-o", "--output",
    default=None,
    type=click.Path(),
    help="Output file path (auto-format from extension: .json, .html, .txt).",
)
@click.option(
    "--format",
    type=click.Choice(["json", "table", "html", "txt", "graph"]),
    default=None,
    help="Output format (default: auto-detect from --output extension, else table).",
)
@click.option(
    "--browser/--no-browser",
    default=False,
    help="Use Playwright browser engine for JS-heavy platforms (Weibo, Zhihu, etc.).",
)
@click.option(
    "--ai/--no-ai",
    default=False,
    help="Run AI-powered analysis on results (requires OPENAI_API_KEY).",
)
@click.option(
    "-v", "--verbose",
    count=True,
    help="Increase verbosity (-v, -vv).",
)
@click.option(
    "--id-type",
    type=click.Choice(["username", "email", "steam_id", "phone"]),
    default="username",
    show_default=True,
    help="Type of identifier to search by.",
)
def scan(
    usernames: Sequence[str],
    platforms: Optional[str],
    tags: Optional[str],
    country: Optional[str],
    top: Optional[int],
    timeout: int,
    retries: int,
    proxy: Optional[str],
    tor: bool,
    output: Optional[str],
    format: Optional[str],
    browser: bool,
    ai: bool,
    verbose: int,
    id_type: str,
) -> None:
    """Scan USERNAME(S) across supported platforms for associated accounts.

    Accepts one or more usernames. Results are correlated across
    platforms and saved to the specified output file.
    """
    # Banner
    console.print(f"[bold teal]SuperScope[/] v{__version__} — [dim]Enhanced OSINT Username Scanner[/]")
    console.print()

    # Resolve format
    out_format = format
    if out_format is None and output:
        ext = Path(output).suffix.lower()
        ext_map = {".json": "json", ".html": "html", ".htm": "html", ".txt": "txt"}
        out_format = ext_map.get(ext, "table")
    if out_format is None:
        out_format = "table"

    tag_list: Optional[List[str]] = (
        [t.strip() for t in tags.split(",")] if tags else None
    )
    platform_list: Optional[List[str]] = (
        [p.strip() for p in platforms.split(",")] if platforms else None
    )

    # Resolve proxy
    proxy_url: Optional[str] = proxy
    if tor:
        proxy_url = "socks5://127.0.0.1:9050"
        console.print("[dim]🧅 Tor mode enabled[/]")

    # Run scans for each username
    all_scan_data: List[Dict[str, Any]] = []

    for idx, username in enumerate(usernames):
        if len(usernames) > 1:
            console.print(f"\n[bold]Scan {idx + 1}/{len(usernames)}:[/] [cyan]{username}[/]")

        scan_data = _run_scan_sync(
            username=username,
            platforms=platform_list,
            tags=tag_list,
            country=country,
            top=top,
            timeout=timeout,
            retries=retries,
            proxy_url=proxy_url,
            use_browser=browser,
            use_ai=ai,
            verbose=verbose,
            id_type=id_type,
        )
        all_scan_data.append(scan_data)

        _display_results(scan_data, out_format, verbose)

    # Save output
    if output:
        _save_output(all_scan_data if len(all_scan_data) > 1 else all_scan_data[0], output, out_format)

    # Summary for multiple usernames
    if len(usernames) > 1:
        console.print(f"\n[bold teal]Summary:[/] Scanned {len(usernames)} username(s)")


def _run_scan_sync(
    username: str,
    platforms: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    country: Optional[str] = None,
    top: Optional[int] = None,
    timeout: int = 15,
    retries: int = 3,
    proxy_url: Optional[str] = None,
    use_browser: bool = False,
    use_ai: bool = False,
    verbose: int = 0,
    id_type: str = "username",
) -> Dict[str, Any]:
    """Synchronous wrapper around the async scan logic."""
    return asyncio.run(
        _run_scan_async(
            username=username,
            platforms=platforms,
            tags=tags,
            country=country,
            top=top,
            timeout=timeout,
            retries=retries,
            proxy_url=proxy_url,
            use_browser=use_browser,
            use_ai=use_ai,
            verbose=verbose,
            id_type=id_type,
        )
    )


async def _run_scan_async(
    username: str,
    platforms: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    country: Optional[str] = None,
    top: Optional[int] = None,
    timeout: int = 15,
    retries: int = 3,
    proxy_url: Optional[str] = None,
    use_browser: bool = False,
    use_ai: bool = False,
    verbose: int = 0,
    id_type: str = "username",
) -> Dict[str, Any]:
    """Execute the full scan pipeline: filter sites, run checks, correlate, analyze."""
    from superscope.db.sites import SiteDatabase
    from superscope.engine.checker import CheckerEngine, CheckStatus

    db = SiteDatabase()
    sites = db.filter(names=platforms, tags=tags, country=country, top=top)

    # Filter sites by id_type: only include platforms that support the given type
    # Platforms without explicit id_types default to supporting "username"
    sites = [
        s for s in sites
        if id_type in s.get("id_types", ["username"])
    ]

    if not sites:
        console.print("[yellow]Warning:[/] No platforms matched the given filters.")
        return {
            "username": username,
            "results": [],
            "ai_report": None,
            "correlations": [],
            "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_platforms": 0,
        }

    http_platforms = [s["name"] for s in sites if s.get("engine", "http") == "http"]
    browser_platforms = [s["name"] for s in sites if s.get("engine") == "browser"]

    if verbose:
        console.print(f"  Platforms: {len(sites)} total ({len(http_platforms)} HTTP, {len(browser_platforms)} browser)")
        console.print(f"  Timeout: {timeout}s, Retries: {retries}")

    # Progress bar
    total_checks = len(http_platforms) + (len(browser_platforms) if use_browser else 0)
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )
    task = progress.add_task(f"[cyan]Scanning '{username}'...", total=total_checks)

    all_results: List[Dict[str, Any]] = []

    with progress:
        # HTTP checks
        if http_platforms:
            checker = CheckerEngine(
                timeout=timeout,
                retries=retries,
                proxy_url=proxy_url,
            )
            checker.register_http_defaults_from_db(db, id_type=id_type)
            http_results = await checker.check_many(http_platforms, username)
            for plat, res in http_results.items():
                serialized = _serialize_result(res)
                all_results.append(serialized)
                progress.advance(task)
                status_char = (
                    "[green]✓[/]" if res.status == CheckStatus.FOUND
                    else "[dim]—[/]" if res.status == CheckStatus.NOT_FOUND
                    else "[red]✗[/]"
                )
                if verbose:
                    console.print(f"    {status_char} {plat:<20} {res.status.value}")

        # Browser checks
        if use_browser and browser_platforms:
            try:
                from superscope.engine.browser import BrowserEngine

                browser_engine = BrowserEngine(
                    headless=True,
                    proxy_url=proxy_url,
                    timeout=timeout * 1000,
                )
                for plat in browser_platforms:
                    res = await browser_engine.check(plat, username)
                    serialized = _serialize_result(res)
                    all_results.append(serialized)
                    progress.advance(task)
                    if verbose:
                        console.print(f"    {'[green]✓[/]' if res.status == CheckStatus.FOUND else '[dim]—[/]'} {plat:<20} {res.status.value}")
                await browser_engine.close()
            except ImportError:
                for plat in browser_platforms:
                    all_results.append({
                        "platform": plat,
                        "username": username,
                        "status": "error",
                        "error_message": "Playwright not installed (pip install superscope[playwright])",
                    })
                    progress.advance(task)
                    if verbose:
                        console.print(f"    [red]✗[/] {plat:<20} Playwright not installed")

    # Correlate
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
    except Exception as exc:
        if verbose:
            console.print(f"[dim]Correlation skipped: {exc}[/]")

    # AI analysis
    ai_report: Optional[Dict[str, Any]] = None
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
                if verbose:
                    console.print(f"[dim]AI analysis complete: risk {report.risk_assessment}[/]")
            else:
                ai_report = {
                    "summary": "AI analysis unavailable — set OPENAI_API_KEY environment variable.",
                    "risk_assessment": "unknown",
                }
        except Exception as exc:
            if verbose:
                console.print(f"[dim]AI analysis error: {exc}[/]")

    return {
        "username": username,
        "results": all_results,
        "ai_report": ai_report,
        "correlations": correlations,
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_platforms": len(http_platforms) + len(browser_platforms),
    }


def _display_results(
    scan_data: Dict[str, Any],
    out_format: str,
    verbose: int,
) -> None:
    """Display scan results in the chosen format."""
    results = scan_data.get("results", [])
    username = scan_data.get("username", "?")
    found = [r for r in results if r["status"] == "found"]
    not_found = [r for r in results if r["status"] == "not_found"]
    errors = [r for r in results if r["status"] == "error"]

    console.print()
    console.print(f"[bold]Results for[/] [cyan]{username}[/]")
    console.print(f"  [green]Found:[/] {len(found)}  [dim]Not found:[/] {len(not_found)}  [red]Errors:[/] {len(errors)}")

    if out_format == "table" or out_format == "txt":
        table = Table(title=f"Scan Results: {username}", box=rich.box.SIMPLE)
        table.add_column("Platform", style="cyan", no_wrap=True, width=15)
        table.add_column("Status", no_wrap=True, width=12)
        table.add_column("URL", style="blue", max_width=80)

        for r in results:
            d = r.get("data") or {}
            status_str = {
                "found": "[green]✓ Found[/]",
                "not_found": "[dim]—[/]",
                "error": f"[red]✗ {r.get('error_message', 'Error')}[/]",
            }.get(r["status"], r["status"])

            table.add_row(
                r["platform"],
                status_str,
                d.get("url", "") or "",
            )

        console.print(table)

        # Correlations
        correlations = scan_data.get("correlations", [])
        if correlations:
            console.print(f"\n[bold]Cross-Platform Correlations:[/] {len(correlations)} group(s)")
            for c in correlations:
                console.print(
                    f"  [teal]{' ↔ '.join(c['platforms'][:5])}[/] "
                    f"[dim](confidence: {c['confidence']}, matched by: {', '.join(c['matched_by'])})[/]"
                )

        # AI report
        ai_report = scan_data.get("ai_report")
        if ai_report:
            console.print(f"\n[bold]🤖 AI Analysis[/]")
            console.print(Panel(ai_report.get("summary", ""), title="Summary", border_style="teal"))
            risk = ai_report.get("risk_assessment", "unknown")
            risk_style = {"low": "green", "medium": "yellow", "high": "red"}.get(risk, "white")
            console.print(f"  Risk Assessment: [{risk_style}]{risk.upper()}[/]")
            recs = ai_report.get("recommendations", [])
            if recs:
                console.print("  Recommendations:")
                for rec in recs[:5]:
                    console.print(f"    • {rec}")

    elif out_format == "json":
        # JSON is displayed to stdout only if no output file specified
        pass
    elif out_format == "graph":
        _display_graph(results)

    console.print()


def _display_graph(results: List[Dict[str, Any]]) -> None:
    """Display a simple ASCII relationship graph."""
    found = [r for r in results if r["status"] == "found"]
    if len(found) < 2:
        console.print("[dim]Need at least 2 found platforms for a graph.[/]")
        return

    console.print("[bold]Platform Relationship Graph[/]")
    console.print("  " + " ─── ".join(r["platform"] for r in found[:8]))
    if len(found) > 8:
        console.print(f"  … and {len(found) - 8} more")
    console.print()


def _save_output(
    data: Any,
    output_path: str,
    fmt: str,
) -> None:
    """Save results to a file in the specified format."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Results saved to:[/] {path.resolve()}")

    elif fmt == "html":
        html = _generate_html_report(data)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        console.print(f"[green]HTML report saved to:[/] {path.resolve()}")

    elif fmt == "txt":
        with open(path, "w", encoding="utf-8") as f:
            f.write(_generate_txt_report(data))
        console.print(f"[green]Text report saved to:[/] {path.resolve()}")

    else:
        console.print(f"[yellow]Unsupported output format: {fmt}[/]")


def _generate_html_report(data: Dict[str, Any]) -> str:
    """Generate a standalone HTML report from scan data."""
    username = data.get("username", "unknown")
    results = data.get("results", [])
    found = [r for r in results if r["status"] == "found"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SuperScope Report — {username}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f8fafc; color: #1e293b; }}
  h1 {{ color: #0d9488; border-bottom: 2px solid #0d9488; padding-bottom: 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
  th {{ background: #f1f5f9; font-weight: 600; text-transform: uppercase; font-size: 0.85em; letter-spacing: 0.5px; color: #64748b; }}
  tr:hover {{ background: #f1f5f9; }}
  .found {{ color: #16a34a; font-weight: 500; }}
  .not-found {{ color: #94a3b8; }}
  .error {{ color: #dc2626; }}
  .summary {{ display: flex; gap: 16px; margin: 20px 0; }}
  .stat {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 24px; text-align: center; flex: 1; }}
  .stat .num {{ font-size: 2em; font-weight: 700; color: #0d9488; }}
  .stat .label {{ color: #64748b; font-size: 0.85em; }}
  .ai-box {{ background: #f0fdfa; border: 1px solid #99f6e4; border-radius: 8px; padding: 20px; margin: 20px 0; }}
  a {{ color: #0d9488; }}
</style>
</head>
<body>
<h1>🔭 SuperScope Report</h1>
<p><strong>Username:</strong> {username} | <strong>Scanned at:</strong> {data.get('scanned_at', 'N/A')}</p>
<div class="summary">
  <div class="stat"><div class="num">{len(found)}</div><div class="label">Found</div></div>
  <div class="stat"><div class="num">{len(results) - len([r for r in results if r['status'] == 'found'])}</div><div class="label">Not Found / Error</div></div>
  <div class="stat"><div class="num">{len(results)}</div><div class="label">Total Checked</div></div>
</div>
<table>
<thead><tr><th>Platform</th><th>Status</th><th>Name</th><th>Bio</th><th>URL</th></tr></thead>
<tbody>
"""
    for r in results:
        d = r.get("data") or {}
        html += f"""<tr>
  <td><strong>{r['platform']}</strong></td>
  <td class="{r['status']}">{r['status']}</td>
  <td>{_html_escape(d.get('name', ''))}</td>
  <td>{_html_escape((d.get('bio', '') or '')[:120])}</td>
  <td>{'<a href="' + _html_escape(d.get('url', '')) + '" target="_blank">link</a>' if d.get('url') else ''}</td>
</tr>
"""
    html += "</tbody></table>"

    ai_report = data.get("ai_report")
    if ai_report:
        html += f"""<div class="ai-box">
  <h2>🤖 AI Analysis</h2>
  <p>{_html_escape(ai_report.get('summary', ''))}</p>
  <p><strong>Risk Assessment:</strong> {ai_report.get('risk_assessment', 'unknown')}</p>
</div>
"""
    html += '<p style="color:#94a3b8;font-size:0.85em;margin-top:40px;">Generated by SuperScope v' + __version__ + '</p>'
    html += "</body></html>"
    return html


def _generate_txt_report(data: Dict[str, Any]) -> str:
    """Generate a plain-text report."""
    lines = [
        "=" * 60,
        "SuperScope Report",
        "=" * 60,
        f"Username: {data.get('username', '?')}",
        f"Scanned at: {data.get('scanned_at', 'N/A')}",
        "",
    ]
    results = data.get("results", [])
    found = [r for r in results if r["status"] == "found"]
    not_found = [r for r in results if r["status"] == "not_found"]
    errors = [r for r in results if r["status"] == "error"]

    lines.append(f"Found: {len(found)}  Not Found: {len(not_found)}  Errors: {len(errors)}")
    lines.append("")

    if found:
        lines.append("--- Profiles Found ---")
        for r in found:
            d = r.get("data") or {}
            lines.append(f"  {r['platform']:20s} | {d.get('name', ''):30s} | {d.get('url', '')}")
        lines.append("")

    if errors:
        lines.append("--- Errors ---")
        for r in errors:
            lines.append(f"  {r['platform']:20s} | {r.get('error_message', '')}")
        lines.append("")

    ai_report = data.get("ai_report")
    if ai_report:
        lines.append("--- AI Analysis ---")
        lines.append(f"  {ai_report.get('summary', '')}")
        lines.append(f"  Risk: {ai_report.get('risk_assessment', 'unknown')}")
        lines.append("")

    return "\n".join(lines)


# ===================================================================
# web command
# ===================================================================

@main.command()
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host address to bind the web UI.",
)
@click.option(
    "--port",
    type=int,
    default=8080,
    show_default=True,
    help="Port to serve the web UI on.",
)
@click.option(
    "--open-browser/--no-open-browser",
    default=True,
    help="Open browser automatically after startup.",
)
def web(host: str, port: int, open_browser: bool) -> None:
    """Launch the SuperScope web UI."""
    console.print("[bold teal]SuperScope Web UI[/]")
    console.print(f"  Serving at [underline]http://{host}:{port}[/]")
    console.print()

    from superscope.web.app import run_web_server
    run_web_server(host=host, port=port, open_browser=open_browser)


# ===================================================================
# db-update command
# ===================================================================

@main.command()
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force re-download of all platform definitions.",
)
@click.option(
    "--upstream",
    default=None,
    help="Custom upstream URL for platform definitions.",
)
def db_update(force: bool, upstream: Optional[str] = None) -> None:
    """Update platform definitions from the remote registry."""
    console.print("[bold teal]Updating platform database...[/]")
    console.print()

    from superscope.db.updater import DbUpdater

    updater = DbUpdater(upstream=upstream)

    async def _do_update() -> Dict[str, Any]:
        result = await updater.update(force=force)
        return result

    try:
        stats = asyncio.run(_do_update())
        console.print(f"[green]✓[/] Update complete!")
        console.print(f"  Total platforms: [bold]{stats.get('total', '?')}[/]")
        console.print(f"  New: [green]+{stats.get('added', 0)}[/]")
        console.print(f"  Updated: [blue]{stats.get('updated', 0)}[/]")
    except RuntimeError as exc:
        console.print(f"[red]✗ Update failed:[/] {exc}")
    except Exception as exc:
        console.print(f"[red]✗ Unexpected error:[/] {exc}")


# ===================================================================
# Helpers
# ===================================================================

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


def _html_escape(s: str) -> str:
    """Escape text for safe HTML inclusion."""
    if not s:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    main()
