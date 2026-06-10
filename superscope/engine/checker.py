"""Async HTTP checker engine with timeout, retry, and proxy support."""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx


class CheckStatus(str, Enum):
    """Result status for a username check on a single platform."""

    FOUND = "found"
    """The username/profile was found on this platform."""

    NOT_FOUND = "not_found"
    """The username/profile does not exist on this platform."""

    ERROR = "error"
    """An error occurred during the check (timeout, connection, etc.)."""


@dataclass
class ExtractedData:
    """Data extracted from a matching profile page."""

    name: Optional[str] = None
    """Display name / full name on the profile."""

    avatar_url: Optional[str] = None
    """URL to the profile avatar image."""

    avatar_hash: Optional[str] = None
    """MD5/SHA hash of the avatar content (for cross-referencing)."""

    bio: Optional[str] = None
    """Profile biography / description text."""

    email: Optional[str] = None
    """Email address found on the profile (if any)."""

    location: Optional[str] = None
    """Location string from the profile."""

    url: Optional[str] = None
    """Canonical profile URL."""

    followers: Optional[int] = None
    """Follower count (if available)."""

    following: Optional[int] = None
    """Following count (if available)."""

    created_at: Optional[str] = None
    """Account creation date string (if available)."""

    extra: Dict[str, Any] = field(default_factory=dict)
    """Any additional platform-specific data."""


@dataclass
class CheckResult:
    """Result of checking a single username on a single platform."""

    platform: str
    """Platform identifier (e.g. 'github', 'weibo', 'twitter')."""

    username: str
    """The username that was checked."""

    status: CheckStatus
    """Whether the profile was found, not found, or errored."""

    data: Optional[ExtractedData] = None
    """Extracted profile data (only set when status is FOUND)."""

    error_message: Optional[str] = None
    """Human-readable error description (only set when status is ERROR)."""

    response_time_ms: Optional[float] = None
    """How long the request took in milliseconds."""

    http_status: Optional[int] = None
    """HTTP status code from the response."""


# "Not found" text patterns used to detect missing profiles
_NOT_FOUND_INDICATORS = [
    "not found", "page not found", "doesn't exist", "no user",
    "user not found", "404", "this page doesn't exist",
    "profile not found", "could not be found",
    "该用户不存在", "用户不存在", "页面不存在", "找不到",
    "没有找到", "无法找到", "不存在",
]


def _default_http_checker(url_template: str) -> "PlatformChecker":
    """Factory: create a generic HTTP GET checker from a URL template.

    The checker builds ``url_template.format(username=username)``, makes an
    HTTP GET, and inspects the response:
    - 200 OK + no "not found" keywords in body  → ``FOUND``
    - 200 OK + "not found" keywords             → ``NOT_FOUND``
    - 4xx (except 429/503)                       → ``NOT_FOUND``
    - Otherwise                                  → ``ERROR``
    """

    async def _check(username: str, client: httpx.AsyncClient) -> CheckResult:
        import time
        url = url_template.format(username=username)
        start = time.monotonic()

        try:
            resp = await client.get(url, follow_redirects=True)
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                platform="",
                username=username,
                status=CheckStatus.ERROR,
                error_message=str(exc),
                response_time_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000
        status_code = resp.status_code
        data: Optional[ExtractedData] = None

        if status_code == 200:
            body = resp.text.lower()
            # Scrape basic OpenGraph / meta info
            found_not_found = any(
                ind in body for ind in _NOT_FOUND_INDICATORS
            )
            if not found_not_found:
                data = ExtractedData(url=url, extra={"url": url})
            status = CheckStatus.NOT_FOUND if found_not_found else CheckStatus.FOUND
        elif status_code in (404, 410):
            status = CheckStatus.NOT_FOUND
        elif status_code in (429, 503):
            status = CheckStatus.ERROR
            data = CheckResult(
                platform="",
                username=username,
                status=CheckStatus.ERROR,
                error_message=f"Rate limited / unavailable (HTTP {status_code})",
                http_status=status_code,
                response_time_ms=elapsed,
            )
        else:
            status = CheckStatus.NOT_FOUND

        return CheckResult(
            platform="",
            username=username,
            status=status,
            data=data,
            http_status=status_code,
            response_time_ms=elapsed,
        )

    return _check


class CheckerEngine:
    """Async HTTP checker with configurable timeout, retries, and proxy support.

    Each platform checker is defined as a callable that receives the username
    and returns a CheckResult. Built-in default checkers are registered
    for common patterns (JSON API, HTML scraping, etc.).

    Usage::

        engine = CheckerEngine(timeout=10, retries=3)
        engine.register_http_defaults_from_db()
        result = await engine.check("github", "someuser")
        print(result.status, result.data)
    """

    def __init__(
        self,
        timeout: int = 15,
        retries: int = 3,
        proxy_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        follow_redirects: bool = True,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.proxy_url = proxy_url
        self.follow_redirects = follow_redirects

        self._user_agent: str = (
            user_agent
            or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) "
               "Chrome/122.0.0.0 Safari/537.36"
        )

        self._checkers: Dict[str, "PlatformChecker"] = {}
        """Registered platform checker functions."""

    def register_http_defaults_from_db(
        self,
        db: "Any",  # SiteDatabase — avoid circular import at module level
    ) -> int:
        """Register default HTTP checkers for all http-engine platforms in *db*.

        Args:
            db: A ``SiteDatabase`` instance.

        Returns:
            Number of checkers registered.
        """
        count = 0
        for site in db.get_all():
            name = site.get("name", "")
            engine = site.get("engine", "http")
            url_tpl = site.get("url_template", "") or site.get("url", "")
            if not name or not url_tpl:
                continue
            if engine != "http":
                continue  # skip browser-only platforms
            if name in self._checkers:
                continue  # already has a custom checker
            self._checkers[name] = _default_http_checker(url_tpl)
            count += 1
        return count

    # ------------------------------------------------------------------
    # Client creation
    # ------------------------------------------------------------------

    def _build_client(self) -> httpx.AsyncClient:
        """Build an httpx AsyncClient with the current proxy and timeout config.

        Returns:
            A configured httpx.AsyncClient instance.
        """
        transport: Optional[httpx.AsyncHTTPTransport] = None
        if self.proxy_url:
            transport = httpx.AsyncHTTPTransport(proxy=self.proxy_url)

        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
        )

        return httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            follow_redirects=self.follow_redirects,
            headers={"User-Agent": self._user_agent},
        )

    # ------------------------------------------------------------------
    # Checker registration
    # ------------------------------------------------------------------

    def register_checker(self, platform: str, checker: "PlatformChecker") -> None:
        """Register a platform-specific checker function.

        Args:
            platform: Platform identifier (e.g. 'github', 'weibo').
            checker: Async callable that accepts (username, client) and returns CheckResult.
        """
        self._checkers[platform] = checker

    def unregister_checker(self, platform: str) -> None:
        """Remove a previously registered platform checker."""
        self._checkers.pop(platform, None)

    def list_platforms(self) -> List[str]:
        """Return all registered platform identifiers."""
        return list(self._checkers.keys())

    # ------------------------------------------------------------------
    # Single check with retries
    # ------------------------------------------------------------------

    async def check(
        self,
        platform: str,
        username: str,
        _attempt: int = 0,
    ) -> CheckResult:
        """Check a username on a single platform with automatic retries.

        Args:
            platform: Platform identifier.
            username: Username to search for.
            _attempt: Internal — number of retries already performed.

        Returns:
            A CheckResult with the outcome.
        """
        checker = self._checkers.get(platform)
        if checker is None:
            return CheckResult(
                platform=platform,
                username=username,
                status=CheckStatus.ERROR,
                error_message=f"No checker registered for platform '{platform}'",
            )

        try:
            async with self._build_client() as client:
                result = await checker(username, client)
                return result
        except httpx.TimeoutException as exc:
            return await self._handle_error(
                platform, username, exc,
                f"Request timed out after {self.timeout}s",
                _attempt,
            )
        except httpx.ConnectError as exc:
            return await self._handle_error(
                platform, username, exc,
                "Connection failed",
                _attempt,
            )
        except httpx.HTTPStatusError as exc:
            return await self._handle_error(
                platform, username, exc,
                f"HTTP {exc.response.status_code}",
                _attempt,
            )
        except Exception as exc:
            return await self._handle_error(
                platform, username, exc,
                str(exc),
                _attempt,
            )

    async def _handle_error(
        self,
        platform: str,
        username: str,
        exception: Exception,
        message: str,
        attempt: int,
    ) -> CheckResult:
        """Handle an error with optional retry logic.

        Args:
            platform: Platform identifier.
            username: The username being checked.
            exception: The exception that was raised.
            message: Human-readable error description.
            attempt: Current retry attempt number.

        Returns:
            CheckResult with either a retry or final error state.
        """
        if attempt < self.retries:
            return await self.check(platform, username, _attempt=attempt + 1)

        return CheckResult(
            platform=platform,
            username=username,
            status=CheckStatus.ERROR,
            error_message=message,
        )

    # ------------------------------------------------------------------
    # Batch checks
    # ------------------------------------------------------------------

    async def check_many(
        self,
        platforms: List[str],
        username: str,
    ) -> Dict[str, CheckResult]:
        """Check a username across multiple platforms concurrently.

        Args:
            platforms: List of platform identifiers.
            username: Username to search for.

        Returns:
            Dict mapping platform identifier -> CheckResult.
        """
        import asyncio

        tasks = [self.check(p, username) for p in platforms]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: Dict[str, CheckResult] = {}
        for platform, result in zip(platforms, results):
            if isinstance(result, Exception):
                output[platform] = CheckResult(
                    platform=platform,
                    username=username,
                    status=CheckStatus.ERROR,
                    error_message=str(result),
                )
            else:
                output[platform] = result
        return output

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def compute_avatar_hash(content: bytes) -> str:
        """Compute an MD5 hash for avatar content (for cross-referencing).

        Args:
            content: Raw image bytes.

        Returns:
            Hex MD5 digest string.
        """
        return hashlib.md5(content).hexdigest()


# Type alias for platform checker callables
PlatformChecker = Any
"""Signature: async def check(username: str, client: httpx.AsyncClient) -> CheckResult"""
