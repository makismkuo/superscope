"""
SuperScope Site Database
========================
Loads and filters the sites.json database of platforms to scan.
"""

import json
import os
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "sites.json")


class SiteDatabase:
    """Loads, filters, and queries the sites.json platform database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._sites: List[Dict[str, Any]] = []
        self._loaded = False

    def load(self) -> List[Dict[str, Any]]:
        """Load sites from the JSON file. Returns the full site list."""
        if not os.path.isfile(self.db_path):
            raise FileNotFoundError(
                f"Sites database not found at: {self.db_path}"
            )
        with open(self.db_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(
                f"Expected a JSON array at top level, got {type(data).__name__}"
            )

        required_keys = {"name", "url_template", "method"}
        for i, entry in enumerate(data):
            missing = required_keys - set(entry.keys())
            if missing:
                raise KeyError(
                    f"Entry {i} ('{entry.get('name', 'unknown')}') "
                    f"missing required keys: {missing}"
                )
            if entry["method"] not in ("http", "browser"):
                raise ValueError(
                    f"Entry {i} ('{entry['name']}'): method must be "
                    f"'http' or 'browser', got '{entry['method']}'"
                )

        self._sites = data
        self._loaded = True
        return self._sites

    @property
    def sites(self) -> List[Dict[str, Any]]:
        """Return loaded sites, loading on first access."""
        if not self._loaded:
            self.load()
        return self._sites

    @property
    def count(self) -> int:
        """Total number of sites in the database."""
        return len(self.sites)

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a single site by its name (case-insensitive)."""
        for site in self.sites:
            if site["name"].lower() == name.lower():
                return site
        return None

    def filter(
        self,
        tags: Optional[List[str]] = None,
        country: Optional[str] = None,
        category: Optional[str] = None,
        method: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Filter sites by tags, country, category, method, and enabled status.

        Args:
            tags: Only return sites whose tags list contains ALL specified tags.
            country: Two-letter country code (e.g. 'us', 'cn', 'ru').
            category: Site category (e.g. 'tech', 'social', 'media').
            method: 'http' or 'browser'.
            enabled_only: If True (default), only return sites with enabled=True.

        Returns:
            Filtered list of site dicts.
        """
        results = self.sites

        if enabled_only:
            results = [s for s in results if s.get("enabled", True)]

        if tags:
            tag_set = set(t.lower() for t in tags)
            results = [
                s for s in results
                if tag_set.issubset(set(t.lower() for t in s.get("tags", [])))
            ]

        if country:
            country_lower = country.lower()
            results = [
                s for s in results
                if s.get("country", "").lower() == country_lower
            ]

        if category:
            cat_lower = category.lower()
            results = [
                s for s in results
                if s.get("category", "").lower() == cat_lower
            ]

        if method:
            results = [
                s for s in results
                if s.get("method", "").lower() == method.lower()
            ]

        return results

    def get_enabled(self) -> List[Dict[str, Any]]:
        """Return all enabled sites."""
        return [s for s in self.sites if s.get("enabled", True)]

    def get_http_sites(self) -> List[Dict[str, Any]]:
        """Return enabled sites that can be checked via HTTP."""
        return self.filter(method="http", enabled_only=True)

    def get_browser_sites(self) -> List[Dict[str, Any]]:
        """Return enabled sites that require browser automation."""
        return self.filter(method="browser", enabled_only=True)

    def get_categories(self) -> List[str]:
        """Return a sorted list of all unique categories in the database."""
        return sorted(
            {s["category"] for s in self.sites if "category" in s}
        )

    def get_countries(self) -> List[str]:
        """Return a sorted list of all unique country codes."""
        return sorted(
            {s["country"] for s in self.sites if "country" in s}
        )

    def get_all_tags(self) -> List[str]:
        """Return a sorted list of all unique tags across all sites."""
        all_tags: set = set()
        for s in self.sites:
            all_tags.update(t.lower() for t in s.get("tags", []))
        return sorted(all_tags)

    def build_url(self, site: Dict[str, Any], username: str) -> str:
        """Build a profile URL by substituting {username} in the url_template.

        Args:
            site: A site dict from the database.
            username: The username to substitute.

        Returns:
            The complete profile URL, or empty string for platform-only sites.
        """
        url_tmpl = site.get("url_template", "")
        if not url_tmpl:
            return ""  # platform-only site
        return url_tmpl.format(username=username)

    def to_dict(self) -> Dict[str, Any]:
        """Return database metadata + all sites as a dict."""
        return {
            "total": self.count,
            "sites": self.sites,
        }

    def __repr__(self) -> str:
        return f"<SiteDatabase: {self.count} sites loaded from {self.db_path}>"

    def __len__(self) -> int:
        return self.count

    def __iter__(self):
        return iter(self.sites)

    def __getitem__(self, index):
        return self.sites[index]


# ---------------------------------------------------------------------------
# Convenience singleton
# ---------------------------------------------------------------------------
_db: Optional[SiteDatabase] = None


def get_database(db_path: Optional[str] = None) -> SiteDatabase:
    """Return the shared SiteDatabase singleton."""
    global _db
    if _db is None:
        _db = SiteDatabase(db_path=db_path)
        _db.load()
    return _db
