"""Username variant generation — leet speak, separators, number suffixes, and more."""

from typing import Dict, List, Optional, Set


class VariantGenerator:
    """Generates common username variants from a base username.

    Useful for OSINT enumeration: given a known username, generate
    likely alternative handles used across platforms.

    Supported transformations:
    - Original username
    - Lowercase / uppercase
    - Leet speak substitutions (e -> 3, a -> 4, etc.)
    - Underscore, dot, hyphen separated
    - Common number suffixes (1, 123, 2024, etc.)
    - Prefixes (the_, real_, official_)
    - Truncations and permutations

    Usage::

        gen = VariantGenerator()
        variants = gen.generate("john_doe")
        # Returns: ['john_doe', 'johndoe', 'john.doe', 'john-doe', ...]
    """

    # Leet speak substitution map
    LEET_MAP: Dict[str, List[str]] = {
        "a": ["4", "@"],
        "e": ["3"],
        "g": ["9", "6"],
        "i": ["1", "!"],
        "l": ["1", "|"],
        "o": ["0"],
        "s": ["5", "$", "z"],
        "t": ["7", "+"],
        "b": ["8"],
        "z": ["2"],
    }

    # Common number suffixes appended to usernames
    NUMBER_SUFFIXES: List[str] = [
        "1", "123", "01", "007", "1234",
        "42", "69", "99", "000", "420",
        "2020", "2021", "2022", "2023", "2024",
        "2025", "2026",
    ]

    # Common prefixes
    PREFIXES: List[str] = [
        "the", "real", "official", "its", "mr", "ms",
    ]

    # Separator characters
    SEPARATORS: List[str] = ["_", ".", "-", ""]

    def __init__(
        self,
        max_variants: int = 200,
        include_leet: bool = True,
        include_numbers: bool = True,
        include_separators: bool = True,
        include_prefixes: bool = True,
        include_case: bool = True,
    ) -> None:
        self.max_variants = max_variants
        self.include_leet = include_leet
        self.include_numbers = include_numbers
        self.include_separators = include_separators
        self.include_prefixes = include_prefixes
        self.include_case = include_case

    def generate(self, username: str) -> List[str]:
        """Generate all variant usernames from the given base.

        The original username is always included first.

        Args:
            username: Base username to generate variants from.

        Returns:
            Deduplicated list of variant usernames, preserving insertion order,
            limited to ``max_variants`` entries.
        """
        variants: List[str] = []
        seen: Set[str] = set()

        def _add(v: str) -> None:
            if v and v not in seen:
                seen.add(v)
                variants.append(v)

        # Original, stripped, lowercase
        base = username.strip()
        if not base:
            return []

        base_lower = base.lower()
        _add(base)
        if base_lower != base:
            _add(base_lower)

        # Case variants
        if self.include_case:
            _add(base.upper())
            _add(base.capitalize())

        # Separator variants: split on existing separators, rejoin
        base_parts = self._split_parts(base)
        if self.include_separators:
            self._add_separator_variants(base_parts, _add)
        else:
            # Just the joined version with no separator
            joined = "".join(base_parts)
            if joined != base:
                _add(joined)

        # Leet speak
        if self.include_leet:
            self._add_leet_variants(base_lower, _add)

        # Number suffixes
        if self.include_numbers:
            self._add_number_variants(base_lower, _add)

        # Prefixes
        if self.include_prefixes:
            sep_choices = ["_", ""]
            for prefix in self.PREFIXES:
                for sep in sep_choices:
                    _add(f"{prefix}{sep}{base_lower}")

        # Enforce limit
        return variants[: self.max_variants]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_parts(username: str) -> List[str]:
        """Split a username into word parts by common separators.

        Args:
            username: The username string.

        Returns:
            List of word parts (e.g. 'john_doe' -> ['john', 'doe']).
        """
        for sep in ["_", ".", "-", " "]:
            if sep in username:
                return [p for p in username.split(sep) if p]
        return [username]

    def _add_separator_variants(
        self,
        parts: List[str],
        add_fn: "Callable[[str], None]",
    ) -> None:
        """Generate variants by joining parts with different separators.

        Args:
            parts: List of word parts.
            add_fn: Callback to add each variant.
        """
        if len(parts) <= 1:
            return

        for sep in self.SEPARATORS:
            variant = sep.join(parts)
            add_fn(variant)

        # Also try reversing parts
        if len(parts) > 1:
            rev_sep = self.SEPARATORS[0]  # underscore
            add_fn(rev_sep.join(reversed(parts)))

    def _add_leet_variants(
        self,
        base: str,
        add_fn: "Callable[[str], None]",
    ) -> None:
        """Generate leet-speak substitutions for the base username.

        For each character in the base, if a leet mapping exists,
        substitute the first option.

        Args:
            base: Lowercase base username.
            add_fn: Callback to add each variant.
        """
        # Single-pass substitution (first option per char)
        leet_result = []
        for ch in base:
            if ch in self.LEET_MAP:
                leet_result.append(self.LEET_MAP[ch][0])
            else:
                leet_result.append(ch)
        leeted = "".join(leet_result)
        if leeted != base:
            add_fn(leeted)

    def _add_number_variants(
        self,
        base: str,
        add_fn: "Callable[[str], None]",
    ) -> None:
        """Append common number suffixes to the base username.

        Args:
            base: Lowercase base username.
            add_fn: Callback to add each variant.
        """
        for suffix in self.NUMBER_SUFFIXES:
            add_fn(f"{base}{suffix}")
            add_fn(f"{base}_{suffix}")


# Import Callable for type hint in private methods
from typing import Callable  # noqa: E402 (re-import for type alias)
