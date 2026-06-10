"""
SuperScope AI Report Generator
==============================
Takes raw scan results and uses an LLM (OpenAI-compatible API) to produce:
  - Persona summary (name, location, interests, profession)
  - Account correlation graph (which accounts link together)
  - Risk assessment (how much data is exposed)
  - Recommendations (what to clean up)

Configuration via environment variables:
  SUPER_OPENAI_BASE_URL   - API endpoint (default: https://api.openai.com/v1)
  SUPER_OPENAI_API_KEY    - API key (default: $OPENAI_API_KEY if set)
  SUPER_OPENAI_MODEL      - Model name (default: gpt-4o)
  SUPER_OPENAI_TIMEOUT    - Request timeout in seconds (default: 60)
"""

import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("superscope.analysis.ai_report")

# ---------------------------------------------------------------------------
# Conditional import: handle both package and standalone use
# ---------------------------------------------------------------------------
try:
    from ..db import SiteDatabase
except ImportError:
    # Fallback when running from within the project directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from superscope.db import SiteDatabase  # type: ignore[no-redef]
except Exception:
    SiteDatabase = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TIMEOUT = 60

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    """Represents the outcome of scanning a single site for a username."""

    site_name: str
    url: str
    status: str  # "found" | "not_found" | "error" | "skipped"
    method: str  # "http" | "browser"
    http_status: Optional[int] = None
    profile_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def found(self) -> bool:
        return self.status == "found"

    @property
    def site_category(self) -> Optional[str]:
        """Look up the site's category from the database (lazy)."""
        if SiteDatabase is None:
            return None
        try:
            db = SiteDatabase()
            site = db.get_by_name(self.site_name)
            return site.get("category") if site else None
        except Exception:
            return None


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

class _LLMClient:
    """Minimal OpenAI-compatible chat completions client (no external deps)."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.timeout = timeout

        if not self.api_key:
            logger.warning(
                "No API key set. Set SUPER_OPENAI_API_KEY or OPENAI_API_KEY."
            )

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Send a chat completion request and return the response text."""
        import urllib.request
        import ssl

        url = f"{self.base_url}/chat/completions"
        body = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "SuperScope/1.0",
            },
            method="POST",
        )

        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(
                req, timeout=self.timeout, context=ctx
            ) as resp:
                raw = resp.read().decode("utf-8")
        except Exception as e:
            logger.error("LLM API call failed: %s", e)
            return None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("LLM response parse error: %s", e)
            return None

        choices = data.get("choices", [])
        if not choices:
            logger.error("LLM response missing choices: %s", data)
            return None

        content = choices[0].get("message", {}).get("content", "")
        return content

    def is_available(self) -> bool:
        """Quick check: API key is set so the client can attempt a call."""
        return bool(self.api_key)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

ANALYSIS_SYSTEM_PROMPT = """\
You are a digital footprint analysis expert. Your task is to analyze a set of \
social media and online platform scan results for a given username, then produce \
a structured JSON report.

## Output format
You MUST respond with a single JSON object containing exactly these keys:

```json
{
  "persona_summary": {
    "possible_name": "string or null",
    "possible_location": "string or null",
    "inferred_interests": ["string"],
    "inferred_profession": "string or null",
    "confidence": "low" | "medium" | "high",
    "bio_snippets": ["string"]
  },
  "account_correlations": {
    "nodes": [
      {
        "id": "site_name",
        "category": "tech|social|media|...",
        "method": "http|browser",
        "status": "found|not_found"
      }
    ],
    "edges": [
      {
        "source": "site_name_a",
        "target": "site_name_b",
        "reason": "same email | cross-linked profile | same display name | same bio keywords"
      }
    ]
  },
  "risk_assessment": {
    "overall_score": 0-100,
    "risk_level": "low" | "medium" | "high" | "critical",
    "data_exposure": {
      "personal_info": ["string"],
      "contact_info": ["string"],
      "professional_info": ["string"],
      "location_data": ["string"],
      "social_graph": ["string"]
    },
    "breakdown_by_category": {
      "social": {"found": 0, "total": 0},
      "tech": {"found": 0, "total": 0},
      ...
    }
  },
  "recommendations": [
    {
      "action": "string",
      "priority": "low" | "medium" | "high" | "critical",
      "site": "string or null",
      "reason": "string"
    }
  ]
}
```

Be thorough but grounded. Only infer information that has supporting evidence in \
the scan data. Use null for uncertain fields rather than guessing.
"""


def _build_scan_context(results: List[ScanResult]) -> str:
    """Format scan results into a compact context block for the LLM."""
    lines = []
    for r in sorted(results, key=lambda x: x.site_name.lower()):
        status_icon = "✓" if r.found else "✗" if r.status == "not_found" else "⚠"
        lines.append(
            f"- [{status_icon}] {r.site_name} ({r.method}) → {r.status}"
        )
        if r.found and r.profile_data:
            snippet = json.dumps(r.profile_data, ensure_ascii=False)
            # Truncate very long profile data
            if len(snippet) > 500:
                snippet = snippet[:500] + "..."
            lines.append(f"  data: {snippet}")
        if r.error:
            lines.append(f"  error: {r.error}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# AiReporter
# ---------------------------------------------------------------------------

class AiReporter:
    """Analyzes scan results using an LLM and produces structured reports."""

    def __init__(
        self,
        username: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.username = username
        self._client = _LLMClient(
            base_url=base_url or os.environ.get(
                "SUPER_OPENAI_BASE_URL", DEFAULT_BASE_URL
            ),
            api_key=api_key or os.environ.get(
                "SUPER_OPENAI_API_KEY",
                os.environ.get("OPENAI_API_KEY", ""),
            ),
            model=model or os.environ.get(
                "SUPER_OPENAI_MODEL", DEFAULT_MODEL
            ),
            timeout=timeout or int(
                os.environ.get("SUPER_OPENAI_TIMEOUT", str(DEFAULT_TIMEOUT))
            ),
        )
        self._last_raw_response: Optional[str] = None
        self._last_parsed: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, results: List[ScanResult]) -> Dict[str, Any]:
        """Run the full analysis pipeline: format → LLM call → parse → enrich.

        Returns:
            Dict with keys: persona_summary, account_correlations,
            risk_assessment, recommendations, meta.
        """
        if not results:
            return self._empty_report("No scan results to analyze.")

        if not self._client.is_available():
            return self._empty_report(
                "LLM is not configured (no API key). "
                "Set SUPER_OPENAI_API_KEY or OPENAI_API_KEY."
            )

        # Build the prompt
        context = _build_scan_context(results)
        user_prompt = (
            f"## Username\n{self.username}\n\n"
            f"## Scan Results ({len(results)} sites)\n{context}\n\n"
            "Produce the JSON report as specified. Only use data present "
            "in the scan results above."
        )

        messages = [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # Call LLM
        logger.info(
            "Sending %d results for username '%s' to LLM (%s)...",
            len(results), self.username, self._client.model,
        )
        raw = self._client.chat(messages)
        self._last_raw_response = raw

        if raw is None:
            return self._empty_report("LLM call failed — check your API key and endpoint.")

        # Parse JSON from response (handle markdown-fenced JSON)
        parsed = self._parse_json_response(raw)
        if parsed is None:
            logger.error("Failed to parse LLM response:\n%s", raw)
            return self._empty_report("Could not parse LLM response as JSON.")

        self._last_parsed = parsed

        # Enrich with metadata
        meta = {
            "username": self.username,
            "sites_scanned": len(results),
            "sites_found": sum(1 for r in results if r.found),
            "model": self._client.model,
            "timestamp": time.time(),
        }

        report = {
            "persona_summary": parsed.get("persona_summary", {}),
            "account_correlations": parsed.get("account_correlations", {}),
            "risk_assessment": parsed.get("risk_assessment", {}),
            "recommendations": parsed.get("recommendations", []),
            "meta": meta,
        }
        return report

    # ------------------------------------------------------------------
    # Individual report sections (re-parses cached result)
    # ------------------------------------------------------------------

    def get_persona_summary(
        self, results: List[ScanResult]
    ) -> Dict[str, Any]:
        """Return only the persona summary section."""
        report = self.analyze(results)
        return report.get("persona_summary", {})

    def get_risk_assessment(
        self, results: List[ScanResult]
    ) -> Dict[str, Any]:
        """Return only the risk assessment section."""
        report = self.analyze(results)
        return report.get("risk_assessment", {})

    def get_recommendations(
        self, results: List[ScanResult]
    ) -> List[Dict[str, Any]]:
        """Return only the recommendations list."""
        report = self.analyze(results)
        return report.get("recommendations", [])

    # ------------------------------------------------------------------
    # Fallback: local heuristic analysis (no LLM needed)
    # ------------------------------------------------------------------

    def local_analysis(self, results: List[ScanResult]) -> Dict[str, Any]:
        """Generate a basic analysis using heuristics when no LLM is available.

        This is a fallback that produces a simplified report without any
        external API call.
        """
        found = [r for r in results if r.found]
        not_found = [r for r in results if r.status == "not_found"]
        errors = [r for r in results if r.status == "error"]

        cat_counts: Dict[str, Dict[str, int]] = {}
        for r in results:
            cat = r.site_category or "unknown"
            if cat not in cat_counts:
                cat_counts[cat] = {"found": 0, "total": 0}
            cat_counts[cat]["total"] += 1
            if r.found:
                cat_counts[cat]["found"] += 1

        found_ratio = len(found) / max(len(results), 1)
        if found_ratio >= 0.5:
            risk_level = "high"
            score = min(80 + int(found_ratio * 20), 100)
        elif found_ratio >= 0.25:
            risk_level = "medium"
            score = 40 + int(found_ratio * 40)
        else:
            risk_level = "low"
            score = int(found_ratio * 40)

        # Cross-link detection (heuristic: same username across sites)
        edges = []
        found_names = [r.site_name for r in found]
        for i in range(len(found_names)):
            for j in range(i + 1, len(found_names)):
                edges.append({
                    "source": found_names[i],
                    "target": found_names[j],
                    "reason": "same username across multiple platforms",
                })

        report = {
            "persona_summary": {
                "possible_name": None,
                "possible_location": None,
                "inferred_interests": [],
                "inferred_profession": None,
                "confidence": "low",
                "bio_snippets": [
                    r.profile_data.get("bio", "")
                    for r in found
                    if r.profile_data.get("bio")
                ],
                "_note": "Local heuristic analysis (no LLM configured)",
            },
            "account_correlations": {
                "nodes": [
                    {
                        "id": r.site_name,
                        "category": r.site_category or "unknown",
                        "method": r.method,
                        "status": r.status,
                    }
                    for r in results
                ],
                "edges": edges,
                "total_found": len(found),
            },
            "risk_assessment": {
                "overall_score": score,
                "risk_level": risk_level,
                "data_exposure": {
                    "personal_info": [],
                    "contact_info": [],
                    "professional_info": [],
                    "location_data": [],
                    "social_graph": [
                        f"Active on {len(found)} platforms"
                    ],
                },
                "breakdown_by_category": cat_counts,
            },
            "recommendations": [
                {
                    "action": f"Review {r.site_name} profile visibility",
                    "priority": "medium",
                    "site": r.site_name,
                    "reason": "Account found — check privacy settings",
                }
                for r in found[:10]
            ] + [
                {
                    "action": "Set up SUPER_OPENAI_API_KEY for AI-powered analysis",
                    "priority": "low",
                    "site": None,
                    "reason": "LLM not configured — install API key for richer reports",
                }
            ],
            "meta": {
                "username": self.username,
                "sites_scanned": len(results),
                "sites_found": len(found),
                "sites_with_errors": len(errors),
                "analysis_type": "local_heuristic",
                "timestamp": time.time(),
            },
        }
        return report

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def last_raw_response(self) -> Optional[str]:
        return self._last_raw_response

    @property
    def last_parsed(self) -> Optional[Dict[str, Any]]:
        return self._last_parsed

    @property
    def can_use_llm(self) -> bool:
        return self._client.is_available()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_json_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Extract a JSON object from the LLM response text.

        Handles:
          - Raw JSON (plain text)
          - Markdown-fenced JSON (```json ... ``` or ``` ... ```)
          - Text with embedded JSON
        """
        # Try direct parse first
        raw_stripped = raw.strip()
        try:
            return json.loads(raw_stripped)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code fence
        for pattern in (
            r"```json\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
            r"```json(.*?)```",
            r"```(.*?)```",
        ):
            match = re.search(pattern, raw_stripped, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

        # Try to find the first { ... } block with balanced braces
        brace_start = raw_stripped.find("{")
        if brace_start >= 0:
            depth = 0
            for i in range(brace_start, len(raw_stripped)):
                ch = raw_stripped[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = raw_stripped[brace_start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
        return None

    def _empty_report(self, reason: str) -> Dict[str, Any]:
        """Return a minimal report indicating why analysis wasn't performed."""
        return {
            "persona_summary": {
                "possible_name": None,
                "possible_location": None,
                "inferred_interests": [],
                "inferred_profession": None,
                "confidence": "low",
                "bio_snippets": [],
            },
            "account_correlations": {
                "nodes": [],
                "edges": [],
            },
            "risk_assessment": {
                "overall_score": 0,
                "risk_level": "unknown",
                "data_exposure": {},
                "breakdown_by_category": {},
            },
            "recommendations": [
                {
                    "action": reason,
                    "priority": "medium",
                    "site": None,
                    "reason": "Analysis skipped",
                }
            ],
            "meta": {
                "username": self.username,
                "sites_scanned": 0,
                "sites_found": 0,
                "error": reason,
                "timestamp": time.time(),
            },
        }

    def __repr__(self) -> str:
        return (
            f"<AiReporter username={self.username!r} "
            f"model={self._client.model!r} "
            f"configured={self.can_use_llm}>"
        )
