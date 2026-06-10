"""Browser engine using Playwright for JavaScript-heavy platforms.

Targeted platforms: Weibo, Zhihu, Xiaohongshu, Douyin, Bilibili, and
other sites that require client-side rendering.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from superscope.engine.checker import CheckResult, CheckStatus, ExtractedData


@dataclass
class BrowserProfile:
    """Browser configuration for a platform."""

    name: str
    """Platform name."""

    url_template: str
    """URL template with {username} placeholder, e.g. 'https://weibo.com/u/{username}'."""

    locale: str = "zh-CN"
    """Browser locale / language setting."""

    user_agent: Optional[str] = None
    """Override user agent string. If None, a default is used."""

    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    """Browser viewport dimensions."""

    wait_selector: Optional[str] = None
    """CSS selector to wait for before scraping (ensures page is loaded)."""

    extract_fn: Optional[Callable[..., Dict[str, Any]]] = None
    """Custom extraction function called in the browser context."""


class BrowserEngine:
    """Manages Playwright browser instances for JS-heavy site scraping.

    Supports headless and headed modes, custom viewports, locale settings,
    and per-platform extraction scripts.

    Usage::

        engine = BrowserEngine(headless=True)
        result = await engine.check("weibo", "someuser")
        await engine.close()
    """

    def __init__(
        self,
        headless: bool = True,
        proxy_url: Optional[str] = None,
        timeout: int = 30000,
    ) -> None:
        self.headless = headless
        self.proxy_url = proxy_url
        self.timeout = timeout
        self._browser: Any = None  # playwright Browser
        self._context: Any = None  # playwright BrowserContext
        self._playwright: Any = None  # playwright.Playwright

        self._profiles: Dict[str, BrowserProfile] = self._default_profiles()

    # ------------------------------------------------------------------
    # Default platform profiles
    # ------------------------------------------------------------------

    @staticmethod
    def _default_profiles() -> Dict[str, BrowserProfile]:
        """Build default profiles for known Chinese platforms.

        Returns:
            Dict of platform name -> BrowserProfile.
        """
        return {
            "weibo": BrowserProfile(
                name="weibo",
                url_template="https://weibo.com/u/{username}",
                wait_selector=".WB_frame",
            ),
            "zhihu": BrowserProfile(
                name="zhihu",
                url_template="https://www.zhihu.com/people/{username}",
                wait_selector=".ProfileHeader",
            ),
            "xiaohongshu": BrowserProfile(
                name="xiaohongshu",
                url_template="https://www.xiaohongshu.com/user/profile/{username}",
                wait_selector=".reds-user-profile",
            ),
            "douyin": BrowserProfile(
                name="douyin",
                url_template="https://www.douyin.com/user/{username}",
                wait_selector=".profile",
            ),
            "bilibili": BrowserProfile(
                name="bilibili",
                url_template="https://space.bilibili.com/{username}",
                wait_selector="#h-inner",
            ),
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _ensure_browser(self) -> None:
        """Lazily launch the Playwright browser if not already running."""
        if self._browser is not None:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for browser-based checks. "
                "Install it with: pip install superscope[playwright] && playwright install"
            )

        self._playwright = await async_playwright().start()

        launch_options: Dict[str, Any] = {
            "headless": self.headless,
        }
        if self.proxy_url:
            launch_options["proxy"] = {"server": self.proxy_url}

        self._browser = await self._playwright.chromium.launch(**launch_options)
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )

    async def close(self) -> None:
        """Close the browser and release all resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._context = None
        self._playwright = None

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def register_profile(self, profile: BrowserProfile) -> None:
        """Register or update a browser profile for a platform.

        Args:
            profile: BrowserProfile defining how to access and scrape the platform.
        """
        self._profiles[profile.name] = profile

    def unregister_profile(self, platform: str) -> None:
        """Remove a platform's browser profile."""
        self._profiles.pop(platform, None)

    def list_profiles(self) -> List[str]:
        """Return all registered platform profile names."""
        return list(self._profiles.keys())

    # ------------------------------------------------------------------
    # Page scraping
    # ------------------------------------------------------------------

    async def check(self, platform: str, username: str) -> CheckResult:
        """Check a username on a JS-heavy platform using Playwright.

        Args:
            platform: Platform identifier (e.g. 'weibo', 'zhihu').
            username: Username to look up.

        Returns:
            A CheckResult with the outcome.
        """
        profile = self._profiles.get(platform)
        if profile is None:
            return CheckResult(
                platform=platform,
                username=username,
                status=CheckStatus.ERROR,
                error_message=f"No browser profile for platform '{platform}'",
            )

        await self._ensure_browser()

        page = await self._context.new_page()  # type: ignore[union-attr]
        url = profile.url_template.format(username=username)

        try:
            await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")

            if profile.wait_selector:
                try:
                    await page.wait_for_selector(
                        profile.wait_selector,
                        timeout=self.timeout,
                    )
                except Exception as exc:
                    return CheckResult(
                        platform=platform,
                        username=username,
                        status=CheckStatus.NOT_FOUND,
                        error_message=f"Profile element not found: {exc}",
                    )

            # Extract page metadata
            title = await page.title()
            text_content = await page.evaluate("document.body.innerText") or ""

            # Check if page indicates a 404 / not found
            if self._is_not_found(title, text_content, platform):
                return CheckResult(
                    platform=platform,
                    username=username,
                    status=CheckStatus.NOT_FOUND,
                )

            extracted = await self._extract_page_data(page, profile, username)

            return CheckResult(
                platform=platform,
                username=username,
                status=CheckStatus.FOUND,
                data=extracted,
            )

        except Exception as exc:
            return CheckResult(
                platform=platform,
                username=username,
                status=CheckStatus.ERROR,
                error_message=str(exc),
            )
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_not_found(
        title: str,
        text_content: str,
        platform: str,  # noqa: ARG004
    ) -> bool:
        """Heuristic check for 404 / not-found pages.

        Args:
            title: Page title.
            text_content: Visible text on the page.
            platform: Platform identifier (for future platform-specific heuristics).

        Returns:
            True if the page appears to be a not-found/error page.
        """
        not_found_signals = [
            "404", "not found", "页面不存在", "用户不存在",
            "找不到", "page not found", "该页面不存在",
        ]
        combined = f"{title} {text_content}".lower()
        return any(signal.lower() in combined for signal in not_found_signals)

    @staticmethod
    async def _extract_page_data(
        page: Any,
        profile: BrowserProfile,
        username: str,
    ) -> ExtractedData:
        """Extract structured profile data from a loaded Playwright page.

        Args:
            page: Playwright Page object (fully loaded).
            profile: BrowserProfile for the platform.
            username: The username being checked.

        Returns:
            ExtractedData with available profile fields.
        """
        data = ExtractedData()
        data.url = profile.url_template.format(username=username)

        # Use custom extract function if provided
        if profile.extract_fn:
            try:
                extra = profile.extract_fn(page)
                data.extra = extra
            except Exception:
                pass

        # Basic extraction via page evaluation
        try:
            js_result = await page.evaluate("""() => {
                const meta = {};
                const ogTitle = document.querySelector('meta[property="og:title"]');
                if (ogTitle) meta.name = ogTitle.content;
                const ogImage = document.querySelector('meta[property="og:image"]');
                if (ogImage) meta.avatar_url = ogImage.content;
                const ogDesc = document.querySelector('meta[property="og:description"]');
                if (ogDesc) meta.bio = ogDesc.content;
                const ogUrl = document.querySelector('meta[property="og:url"]');
                if (ogUrl) meta.url = ogUrl.content;
                return meta;
            }""")
            if js_result.get("name"):
                data.name = js_result["name"]
            if js_result.get("avatar_url"):
                data.avatar_url = js_result["avatar_url"]
            if js_result.get("bio"):
                data.bio = js_result["bio"]
            if js_result.get("url"):
                data.url = js_result["url"]
        except Exception:
            pass

        return data
