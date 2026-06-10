"""Correlator — cross-reference results across platforms to link accounts."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from superscope.engine.checker import CheckResult, CheckStatus, ExtractedData


@dataclass
class CorrelationResult:
    """Result of correlating a set of platform results."""

    platforms: List[str]
    """Platforms included in this correlation."""

    confidence: float
    """Confidence score between 0.0 and 1.0."""

    matched_by: List[str]
    """List of matching signals (e.g. 'avatar_hash', 'email_domain', 'bio_similarity')."""

    matched_platforms: List[Tuple[str, str]]
    """Pairs of (platform_a, platform_b) that were matched."""

    shared_data: Dict[str, Any] = field(default_factory=dict)
    """Aggregated shared data across correlated platforms."""


class Correlator:
    """Cross-reference results from different platforms to identify linked accounts.

    Uses multiple signals to correlate profiles:
    - Avatar hash comparison (exact match)
    - Bio text similarity (cosine / fuzzy)
    - Email domain matching
    - Display name matching
    - URL / handle cross-references

    Usage::

        correlator = Correlator(min_confidence=0.5)
        results = correlator.correlate(all_check_results)
        for r in results:
            print(r.platforms, r.confidence, r.matched_by)
    """

    def __init__(
        self,
        min_confidence: float = 0.3,
        bio_similarity_threshold: float = 0.6,
    ) -> None:
        self.min_confidence = min_confidence
        self.bio_similarity_threshold = bio_similarity_threshold

    # ------------------------------------------------------------------
    # Main correlation entry point
    # ------------------------------------------------------------------

    def correlate(
        self,
        results: List[CheckResult],
    ) -> List[CorrelationResult]:
        """Correlate a list of check results into linked groups.

        Only results with status FOUND are considered for correlation.

        Args:
            results: List of CheckResult from a scan.

        Returns:
            List of CorrelationResult, one per linked group.
        """
        found: List[CheckResult] = [
            r for r in results
            if r.status == CheckStatus.FOUND and r.data is not None
        ]

        if len(found) < 2:
            return []

        # Build adjacency: platforms are nodes, weights are edges
        n = len(found)
        adjacency: List[Set[int]] = [set() for _ in range(n)]
        edges: List[Tuple[int, int, float, List[str]]] = []

        for i in range(n):
            for j in range(i + 1, n):
                confidence, reasons = self._compare(found[i], found[j])
                if confidence >= self.min_confidence:
                    adjacency[i].add(j)
                    adjacency[j].add(i)
                    edges.append((i, j, confidence, reasons))

        # Find connected components (groups of linked accounts)
        visited: Set[int] = set()
        groups: List[List[int]] = []

        for i in range(n):
            if i not in visited:
                group: List[int] = []
                stack = [i]
                while stack:
                    node = stack.pop()
                    if node not in visited:
                        visited.add(node)
                        group.append(node)
                        stack.extend(adjacency[node] - visited)
                if len(group) > 1:
                    groups.append(group)

        # Build CorrelationResult per group
        correlation_results: List[CorrelationResult] = []
        for group in groups:
            group_results = [found[idx] for idx in group]
            group_edges = [
                e for e in edges if e[0] in group and e[1] in group
            ]

            avg_confidence = (
                sum(e[2] for e in group_edges) / len(group_edges)
                if group_edges
                else 0.0
            )

            all_reasons: Set[str] = set()
            for _, _, _, reasons in group_edges:
                all_reasons.update(reasons)

            matched_pairs: List[Tuple[str, str]] = []
            for _, _, _, _ in group_edges:
                pass  # pairs derived below
            # Build matched_pairs from group edges
            for e_idx in group_edges:
                a_plat = found[e_idx[0]].platform
                b_plat = found[e_idx[1]].platform
                matched_pairs.append((a_plat, b_plat))

            shared = self._aggregate_shared(group_results)

            correlation_results.append(
                CorrelationResult(
                    platforms=[r.platform for r in group_results],
                    confidence=round(avg_confidence, 3),
                    matched_by=sorted(all_reasons),
                    matched_platforms=matched_pairs,
                    shared_data=shared,
                )
            )

        return correlation_results

    # ------------------------------------------------------------------
    # Pairwise comparison
    # ------------------------------------------------------------------

    def _compare(
        self,
        a: CheckResult,
        b: CheckResult,
    ) -> Tuple[float, List[str]]:
        """Compare two CheckResults and compute a correlation score.

        Args:
            a: First check result.
            b: Second check result.

        Returns:
            Tuple of (confidence_score, list_of_reasons).
        """
        data_a = a.data or ExtractedData()
        data_b = b.data or ExtractedData()

        confidence = 0.0
        reasons: List[str] = []

        # 1. Avatar hash match (strongest signal)
        if data_a.avatar_hash and data_b.avatar_hash:
            if data_a.avatar_hash == data_b.avatar_hash:
                confidence += 0.5
                reasons.append("avatar_hash")

        # 2. Email domain match
        if data_a.email and data_b.email:
            domain_a = data_a.email.split("@")[-1].lower()
            domain_b = data_b.email.split("@")[-1].lower()
            if domain_a == domain_b:
                confidence += 0.3
                reasons.append("email_domain")
            elif domain_a and domain_b:
                # Same provider (gmail.com vs gmail.com already caught above)
                pass

        # 3. Display name match
        if data_a.name and data_b.name:
            if data_a.name.lower().strip() == data_b.name.lower().strip():
                confidence += 0.25
                reasons.append("display_name")

        # 4. Bio similarity (fuzzy)
        if data_a.bio and data_b.bio:
            similarity = self._text_similarity(data_a.bio, data_b.bio)
            if similarity >= self.bio_similarity_threshold:
                confidence += 0.2 * similarity
                reasons.append("bio_similarity")

        # 5. Same profile URL
        if data_a.url and data_b.url:
            if data_a.url == data_b.url:
                confidence += 0.4
                reasons.append("same_url")

        # 6. Location
        if data_a.location and data_b.location:
            if data_a.location.lower().strip() == data_b.location.lower().strip():
                confidence += 0.1
                reasons.append("location")

        return min(confidence, 1.0), reasons

    # ------------------------------------------------------------------
    # Text similarity
    # ------------------------------------------------------------------

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """Compute a simple word-overlap similarity between two texts.

        Uses Jaccard similarity on word sets.

        Args:
            a: First text string.
            b: Second text string.

        Returns:
            Float between 0.0 and 1.0.
        """
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())

        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b

        return len(intersection) / len(union)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_shared(
        results: List[CheckResult],
    ) -> Dict[str, Any]:
        """Aggregate shared data across correlated results.

        Args:
            results: List of CheckResults (all should have data).

        Returns:
            Dict with merged fields.
        """
        shared: Dict[str, Any] = {}
        names: Set[str] = set()
        bios: List[str] = []
        emails: Set[str] = set()
        locations: Set[str] = set()
        avatar_urls: Set[str] = set()

        for r in results:
            d = r.data
            if d is None:
                continue
            if d.name:
                names.add(d.name)
            if d.bio:
                bios.append(d.bio)
            if d.email:
                emails.add(d.email)
            if d.location:
                locations.add(d.location)
            if d.avatar_url:
                avatar_urls.add(d.avatar_url)

        if names:
            shared["names"] = list(names)
        if bios:
            shared["bios"] = bios
        if emails:
            shared["emails"] = list(emails)
        if locations:
            shared["locations"] = list(locations)
        if avatar_urls:
            shared["avatar_urls"] = list(avatar_urls)

        return shared
