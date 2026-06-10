"""SuperScope engine — proxy, checker, and browser modules."""

from superscope.engine.proxy import ProxyConfig, ProxyManager
from superscope.engine.checker import (
    CheckResult,
    CheckStatus,
    CheckerEngine,
    ExtractedData,
)
from superscope.engine.browser import BrowserEngine, BrowserProfile

__all__ = [
    "ProxyConfig",
    "ProxyManager",
    "CheckResult",
    "CheckStatus",
    "CheckerEngine",
    "ExtractedData",
    "BrowserEngine",
    "BrowserProfile",
]
