"""
SuperScope Database Updater
===========================
Auto-fetches the latest site list from a remote source (GitHub raw URL),
validates every URL template, deduplicates, and merges with the local database.
"""

import json
import logging
import os
import re
import ssl
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple

from . import SiteDatabase, DEFAULT_DB_PATH

logger = logging.getLogger("superscope.db.updater")

# Default upstream source — the canonical SuperScope sites.json on GitHub
DEFAULT_UPSTREAM_URL = (
    "https://raw.githubusercontent.com/NousResearch/superscope/main/db/sites.json"
)

# Known required keys in each site entry
REQUIRED_SITE_KEYS: Set[str] = {"name", "url_template", "method"}
VALID_METHODS: Set[str] = {"http", "browser"}

# Regex to verify {username} placeholder is present
USERNAME_PLACEHOLDER_RE = re.compile(r"\{username\}")

# Regex to catch obvious injection attempts in name/url fields
_INJECTION_RE = re.compile(r"[<>\"]")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_site_entry(entry: Dict[str, Any], index: int) -> List[str]:
    """Validate a single site entry, returning a list of error messages."""
    errors: List[str] = []
    name = entry.get("name", f"<entry_{index}>")

    # Required keys
    missing = REQUIRED_SITE_KEYS - set(entry.keys())
    if missing:
        errors.append(f"[{name}] Missing required keys: {missing}")
        return errors  # no point checking further

    # Platform-only entries skip URL-level validation
    if entry.get("platform_only"):
        return errors

    # Method
    if entry["method"] not in VALID_METHODS:
        errors.append(
            f"[{name}] Invalid method '{entry['method']}'; "
            f"expected one of {VALID_METHODS}"
        )

    # URL template must contain {username}
    url = entry["url_template"]
    if not USERNAME_PLACEHOLDER_RE.search(url):
        errors.append(
            f"[{name}] url_template '{url}' missing '{{username}}' placeholder"
        )

    # URL must start with http:// or https://
    if not url.startswith(("http://", "https://")):
        errors.append(f"[{name}] url_template must start with http:// or https://")

    # Detect possible injection attempts in name or url_template
    for field in ("name", "url_template"):
        val = str(entry.get(field, ""))
        if _INJECTION_RE.search(val):
            errors.append(f"[{name}] Suspicious characters in '{field}': '{val}'")

    # Tags should be a non-empty list of strings
    tags = entry.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        errors.append(f"[{name}] 'tags' must be a list of strings")

    # Country should be a short string (2-letter code or similar)
    country = entry.get("country", "")
    if not isinstance(country, str) or not country.strip():
        errors.append(f"[{name}] 'country' is missing or empty")

    return errors


def validate_sites(sites: List[Dict[str, Any]]) -> List[str]:
    """Validate a list of site entries. Returns list of all error messages."""
    all_errors: List[str] = []
    for i, entry in enumerate(sites):
        all_errors.extend(_validate_site_entry(entry, i))
    return all_errors


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def _site_key(site: Dict[str, Any]) -> str:
    """Return a canonical key for a site (lowercase name for dedup)."""
    return site.get("name", "").strip().lower()


def merge_site_lists(
    local_sites: List[Dict[str, Any]],
    remote_sites: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Merge remote sites into local, preferring remote for same-name entries.

    Args:
        local_sites: Existing local site entries.
        remote_sites: Fresh remote entries (upstream).

    Returns:
        (merged_list, added_count, updated_count)
    """
    local_map: Dict[str, Dict[str, Any]] = {
        _site_key(s): s for s in local_sites
    }
    remote_map: Dict[str, Dict[str, Any]] = {
        _site_key(s): s for s in remote_sites
    }

    added = 0
    updated = 0

    for key, remote_entry in remote_map.items():
        if key not in local_map:
            local_map[key] = deepcopy(remote_entry)
            added += 1
        else:
            # Update existing entry with remote (newer) data
            local_map[key] = deepcopy(remote_entry)
            updated += 1

    merged = list(local_map.values())
    return merged, added, updated


# ---------------------------------------------------------------------------
# DbUpdater class
# ---------------------------------------------------------------------------

class DbUpdater:
    """Fetches latest site list from upstream, validates, and merges locally."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        upstream_url: Optional[str] = None,
        timeout: int = 30,
    ):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.upstream_url = upstream_url or DEFAULT_UPSTREAM_URL
        self.timeout = timeout
        self._last_fetch_errors: List[str] = []

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch_remote(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch the latest sites.json from the upstream URL.

        Returns:
            Parsed list of sites, or None on failure.
        """
        logger.info("Fetching remote sites from %s", self.upstream_url)

        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            self.upstream_url,
            headers={
                "User-Agent": "SuperScope/1.0 (site-database-updater)",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            logger.error("HTTP error fetching remote sites: %s %s", e.code, e.reason)
            self._last_fetch_errors.append(f"HTTP {e.code}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error("URL error fetching remote sites: %s", e.reason)
            self._last_fetch_errors.append(f"URL error: {e.reason}")
            return None
        except (ssl.SSLError, OSError, ValueError) as e:
            logger.error("Network error fetching remote sites: %s", e)
            self._last_fetch_errors.append(f"Network error: {e}")
            return None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON from remote: %s", e)
            self._last_fetch_errors.append(f"JSON parse error: {e}")
            return None

        if not isinstance(data, list):
            msg = f"Remote data is not a list (got {type(data).__name__})"
            logger.error(msg)
            self._last_fetch_errors.append(msg)
            return None

        return data

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def validate(self, sites: List[Dict[str, Any]]) -> bool:
        """Validate a list of sites. Logs errors, returns True if valid."""
        errors = validate_sites(sites)
        self._last_fetch_errors.extend(errors)
        if errors:
            logger.warning("Validation found %d issue(s)", len(errors))
            for err in errors:
                logger.warning("  - %s", err)
            return False
        logger.info("Validation passed: %d sites OK", len(sites))
        return True

    # ------------------------------------------------------------------
    # Load local
    # ------------------------------------------------------------------

    def load_local(self) -> List[Dict[str, Any]]:
        """Load the local sites.json, returning an empty list if absent."""
        if not os.path.isfile(self.db_path):
            logger.info("No local database found at %s; starting fresh", self.db_path)
            return []
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read local database: %s; starting fresh", e)
            return []

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, sites: List[Dict[str, Any]]) -> bool:
        """Atomically write the site list to disk."""
        tmp_path = self.db_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(sites, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, self.db_path)
            logger.info("Saved %d sites to %s", len(sites), self.db_path)
            return True
        except OSError as e:
            logger.error("Failed to save database: %s", e)
            self._last_fetch_errors.append(f"Save error: {e}")
            return False

    # ------------------------------------------------------------------
    # Full run: fetch → validate → merge → save
    # ------------------------------------------------------------------

    def update(
        self,
        dry_run: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Run the full update pipeline.

        Args:
            dry_run: If True, don't write the merged result to disk.
            force: If True, skip validation errors and still merge.

        Returns:
            Dict with keys: success, total, added, updated, errors, fetched, dry_run
        """
        self._last_fetch_errors = []
        result: Dict[str, Any] = {
            "success": False,
            "total": 0,
            "added": 0,
            "updated": 0,
            "errors": [],
            "fetched": False,
            "dry_run": dry_run,
        }

        # 1. Fetch remote
        remote = self.fetch_remote()
        if remote is None:
            result["errors"] = self._last_fetch_errors[:]
            return result
        result["fetched"] = True

        # 2. Validate remote
        valid = self.validate(remote)
        if not valid and not force:
            result["errors"] = self._last_fetch_errors[:]
            return result

        # 3. Load local
        local = self.load_local()

        # 4. Merge
        merged, added, updated = merge_site_lists(local, remote)
        result["total"] = len(merged)
        result["added"] = added
        result["updated"] = updated

        # 5. Validate merged result
        merge_errors = validate_sites(merged)
        if merge_errors and not force:
            result["errors"] = merge_errors[:]
            return result

        # 6. Save
        if not dry_run:
            if not self.save(merged):
                result["errors"] = self._last_fetch_errors[:]
                return result

        result["success"] = True
        result["errors"] = self._last_fetch_errors[:]
        return result

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def last_errors(self) -> List[str]:
        """Return errors from the last update run."""
        return self._last_fetch_errors[:]

    def __repr__(self) -> str:
        return (
            f"<DbUpdater db_path={self.db_path!r} "
            f"upstream={self.upstream_url!r}>"
        )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def run_update(
    db_path: Optional[str] = None,
    upstream_url: Optional[str] = None,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """One-shot convenience: create an updater and run it."""
    updater = DbUpdater(db_path=db_path, upstream_url=upstream_url)
    return updater.update(dry_run=dry_run, force=force)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    res = run_update(dry_run=True)
    print(json.dumps(res, indent=2, ensure_ascii=False))
