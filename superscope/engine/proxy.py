"""Proxy manager with auto Tor detection, SOCKS5/HTTP proxy rotation, and retry logic."""

import random
import socket
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProxyConfig:
    """Configuration for a single proxy entry."""

    url: str
    """Full proxy URL, e.g. socks5://127.0.0.1:9050 or http://proxy:8080."""

    username: Optional[str] = None
    """Optional username for authenticated proxies."""

    password: Optional[str] = None
    """Optional password for authenticated proxies."""

    weight: int = 1
    """Relative weight for random selection (higher = more likely)."""

    max_failures: int = 3
    """Number of consecutive failures before this proxy is temporarily disabled."""


@dataclass
class ProxyStatus:
    """Runtime status of a single proxy."""

    config: ProxyConfig
    failures: int = 0
    disabled: bool = False


class ProxyManager:
    """Manages a pool of SOCKS5/HTTP proxies with auto Tor detection and rotation.

    Features:
    - Auto-detect a running Tor daemon on localhost:9050
    - Round-robin / weighted-random rotation across proxy pool
    - Automatic retry on failure — marks dead proxies as disabled
    - Supports both SOCKS5 and HTTP(S) proxy URLs

    Usage::

        mgr = ProxyManager(auto_detect_tor=True)
        proxy = mgr.get_proxy()       # returns a ProxyConfig or None
        async with mgr.rotate_on_failure() as proxy_url:
            # make request — if it fails, rotates automatically
    """

    def __init__(
        self,
        proxies: Optional[List[ProxyConfig]] = None,
        auto_detect_tor: bool = True,
        tor_host: str = "127.0.0.1",
        tor_port: int = 9050,
    ) -> None:
        self._proxies: List[ProxyStatus] = [
            ProxyStatus(config=p) for p in (proxies or [])
        ]
        self._tor_host = tor_host
        self._tor_port = tor_port
        self._tor_detected: Optional[bool] = None

        if auto_detect_tor:
            self._auto_detect_tor()

    # ------------------------------------------------------------------
    # Tor detection
    # ------------------------------------------------------------------

    def _auto_detect_tor(self) -> bool:
        """Check if a Tor SOCKS5 daemon is reachable on localhost:9050.

        Returns:
            True if Tor is detected, False otherwise.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        try:
            result = sock.connect_ex((self._tor_host, self._tor_port))
            if result == 0:
                tor_cfg = ProxyConfig(
                    url=f"socks5://{self._tor_host}:{self._tor_port}",
                    weight=10,
                )
                # Only add Tor once
                if not any(
                    p.config.url.startswith("socks5://") and str(self._tor_port) in p.config.url
                    for p in self._proxies
                ):
                    self._proxies.append(ProxyStatus(config=tor_cfg))
                self._tor_detected = True
                return True
            self._tor_detected = False
            return False
        except OSError:
            self._tor_detected = False
            return False
        finally:
            sock.close()

    @property
    def tor_available(self) -> bool:
        """Whether a Tor SOCKS5 proxy was detected at startup.

        Returns:
            True if Tor was detected, False if not checked or unavailable.
        """
        return bool(self._tor_detected)

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------

    @property
    def available_count(self) -> int:
        """Number of proxies currently considered healthy."""
        return sum(1 for p in self._proxies if not p.disabled)

    @property
    def all_count(self) -> int:
        """Total number of proxies in the pool (including disabled)."""
        return len(self._proxies)

    def add_proxy(self, config: ProxyConfig) -> None:
        """Add a new proxy to the pool."""
        self._proxies.append(ProxyStatus(config=config))

    def remove_proxy(self, url: str) -> None:
        """Remove a proxy by URL."""
        self._proxies = [p for p in self._proxies if p.config.url != url]

    def disable_proxy(self, url: str) -> None:
        """Manually mark a proxy as disabled."""
        for p in self._proxies:
            if p.config.url == url:
                p.disabled = True
                break

    def reset_proxy(self, url: str) -> None:
        """Reset failure count and re-enable a proxy."""
        for p in self._proxies:
            if p.config.url == url:
                p.failures = 0
                p.disabled = False
                break

    def reset_all(self) -> None:
        """Re-enable all proxies and reset failure counters."""
        for p in self._proxies:
            p.failures = 0
            p.disabled = False

    # ------------------------------------------------------------------
    # Proxy selection
    # ------------------------------------------------------------------

    def get_proxy(self) -> Optional[ProxyConfig]:
        """Select an available proxy using weighted random selection.

        Returns:
            A ProxyConfig for an available proxy, or None if none are healthy.
        """
        available = [p for p in self._proxies if not p.disabled]
        if not available:
            return None

        weights = [p.config.weight for p in available]
        total = sum(weights)
        if total == 0:
            return available[0].config

        r = random.uniform(0, total)
        running = 0.0
        for p, w in zip(available, weights):
            running += w
            if r <= running:
                return p.config

        return available[-1].config

    def get_all_proxies(self) -> List[ProxyConfig]:
        """Return all currently healthy proxy configurations."""
        return [p.config for p in self._proxies if not p.disabled]

    # ------------------------------------------------------------------
    # Failure handling
    # ------------------------------------------------------------------

    def record_failure(self, url: str) -> Optional[ProxyConfig]:
        """Record a failure for the given proxy and optionally rotate.

        If the proxy exceeds its max_failures threshold, it is disabled.
        A fallback proxy is returned if available.

        Args:
            url: The proxy URL that failed.

        Returns:
            A fallback ProxyConfig, or None if all proxies are exhausted.
        """
        for p in self._proxies:
            if p.config.url == url:
                p.failures += 1
                if p.failures >= p.config.max_failures:
                    p.disabled = True
                break
        return self.get_proxy()

    def record_success(self, url: str) -> None:
        """Record a successful request, resetting the failure counter."""
        for p in self._proxies:
            if p.config.url == url:
                p.failures = 0
                break
