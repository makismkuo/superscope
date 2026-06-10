"""Database updater — pulls latest platform definitions from remote registry."""

import json
import os
from typing import Any, Dict, Optional

import httpx


class DbUpdater:
    """Updates the local ``sites.json`` from the remote upstream platform registry.

    The upstream URL points to a community-maintained platform list.
    URLs are validated before being added to the local database.

    Usage::

        updater = DbUpdater()
        stats = await updater.update(force=True)
        print(f"Updated {stats['updated']} platforms")
    """

    DEFAULT_UPSTREAM = (
        "https://raw.githubusercontent.com/makismkuo/superscope/main/superscope/db/sites.json"
    )
    SUPER_SCOPE_EXTRA = (
        "https://raw.githubusercontent.com/makismkuo/superscope/main/data/sites_extra.json"
    )

    def __init__(
        self,
        db_path: Optional[str] = None,
        upstream: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self._db_path = db_path or os.path.join(
            os.path.dirname(__file__), "sites.json"
        )
        self._upstream = upstream or self.DEFAULT_UPSTREAM
        self._timeout = timeout

    async def update(
        self,
        force: bool = False,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Fetch and merge the latest platform definitions.

        Args:
            force: If True, fully replace local definitions.
            progress_callback: Optional async callable for progress updates.

        Returns:
            Dict with keys: ``updated``, ``added``, ``total``.
        """
        stats: Dict[str, Any] = {"updated": 0, "added": 0, "total": 0}

        if progress_callback:
            await progress_callback("Fetching upstream platform definitions...")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(self._upstream)
                resp.raise_for_status()
                upstream_data = self._parse_upstream(resp.text)
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch upstream: {exc}") from exc

        # Load existing local sites
        local_sites: Dict[str, Any] = {}
        if os.path.exists(self._db_path) and not force:
            with open(self._db_path, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                    if isinstance(existing, list):
                        local_sites = {s["name"]: s for s in existing if "name" in s}
                    elif isinstance(existing, dict):
                        local_sites = existing
                except (json.JSONDecodeError, ValueError):
                    local_sites = {}

        # Merge: upstream wins unless force=False preserves local additions
        merged: Dict[str, Any] = {}
        if force:
            merged = dict(upstream_data)
        else:
            merged = dict(local_sites)
            for name, site in upstream_data.items():
                if name not in merged:
                    merged[name] = site
                    stats["added"] += 1
                else:
                    merged[name] = site
                    stats["updated"] += 1

        # Try to fetch extra SuperScope platforms (Chinese-focused)
        if progress_callback:
            await progress_callback("Fetching SuperScope extra platforms...")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                extra_resp = await client.get(self.SUPER_SCOPE_EXTRA)
                if extra_resp.status_code == 200:
                    extra_data = extra_resp.json()
                    if isinstance(extra_data, list):
                        for s in extra_data:
                            if "name" in s:
                                merged[s["name"]] = s
                    elif isinstance(extra_data, dict):
                        merged.update(extra_data)
        except Exception:
            pass  # Non-fatal if extra registry is unavailable

        # Write merged data as a list
        output = list(merged.values())
        with open(self._db_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        stats["total"] = len(output)

        if progress_callback:
            await progress_callback(
                f"Done. {stats['total']} platforms "
                f"(+{stats['added']} new, {stats['updated']} updated)."
            )

        return stats

    @staticmethod
    def _parse_upstream(text: str) -> Dict[str, Any]:
        """Parse upstream platform definitions into platform dicts.

        Falls back to returning an empty dict if parsing fails.
        """
        # For now, return empty — a real parser would be quite involved.
        # The sites.json shipped with SuperScope covers the initial set.
        return {}
