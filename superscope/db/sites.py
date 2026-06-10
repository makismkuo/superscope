"""Site database — loads platform definitions from sites.json."""

import json
import os
from typing import Any, Dict, List, Optional, Sequence


class SiteDatabase:
    """Loads, queries, and filters platform definitions.

    Platforms are stored in ``sites.json`` (adjacent to this module)
    and contain URL templates, check methods, tags, and country info.

    Usage::

        db = SiteDatabase()
        all_sites = db.get_all()
        china_sites = db.filter(tags=["china"])
        github = db.get("github")
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or os.path.join(os.path.dirname(__file__), "sites.json")
        self._sites: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """Load platform definitions from the JSON file."""
        if not os.path.exists(self._path):
            self._sites = {}
            return
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            self._sites = {s["name"]: s for s in data if "name" in s}
        elif isinstance(data, dict):
            self._sites = data
        else:
            self._sites = {}

    def reload(self) -> None:
        """Reload platforms from disk."""
        self.load()

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a single platform definition by name."""
        return self._sites.get(name)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all platform definitions."""
        return list(self._sites.values())

    def list_names(self) -> List[str]:
        """Return all platform names/identifiers."""
        return list(self._sites.keys())

    def filter(
        self,
        names: Optional[Sequence[str]] = None,
        tags: Optional[Sequence[str]] = None,
        country: Optional[str] = None,
        top: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Filter platforms by name, tags, country, or top-N.

        Args:
            names: Only include these platform names (if given).
            tags: Only include platforms with ALL these tags.
            country: Only include platforms from this country code.
            top: Only include this many platforms (sorted by rank).

        Returns:
            Filtered list of platform definitions.
        """
        sites = list(self._sites.values())

        if names:
            name_set = set(n.lower() for n in names)
            sites = [s for s in sites if s.get("name", "").lower() in name_set]

        if tags:
            for tag in tags:
                sites = [s for s in sites if tag in s.get("tags", [])]

        if country:
            sites = [
                s for s in sites
                if s.get("country", "").lower() == country.lower()
            ]

        if top is not None and top > 0:
            sites = sorted(
                sites,
                key=lambda s: s.get("rank", 999),
            )[:top]

        return sites

    @property
    def count(self) -> int:
        """Number of loaded platforms."""
        return len(self._sites)

    def get_browser_platforms(self) -> List[str]:
        """Return platform names that require a browser engine."""
        return [
            s["name"] for s in self._sites.values()
            if s.get("engine") == "browser"
        ]

    def get_http_platforms(self) -> List[str]:
        """Return platform names that use the HTTP checker engine."""
        return [
            s["name"] for s in self._sites.values()
            if s.get("engine", "http") == "http"
        ]
