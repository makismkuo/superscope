"""Utility functions for domain extraction, text similarity, and avatar hash comparison."""

import hashlib
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse


# ------------------------------------------------------------------
# Domain extraction
# ------------------------------------------------------------------

def extract_domain(url: str) -> Optional[str]:
    """Extract the registered domain from a URL.

    Handles full URLs and bare hostnames. Strips ``www.`` prefix.

    Args:
        url: A URL or hostname string (e.g. ``https://www.example.com/path``).

    Returns:
        The registered domain (e.g. ``example.com``), or None if parsing fails.

    Examples:
        >>> extract_domain("https://www.github.com/someuser")
        'github.com'
        >>> extract_domain("weibo.com")
        'weibo.com'
    """
    # If no scheme, prepend one so urlparse works correctly
    if not re.match(r"^https?://", url.lower()):
        url = f"http://{url}"

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
    except ValueError:
        return None

    if not hostname:
        return None

    # Strip www. prefix
    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname


def extract_all_domains(text: str) -> List[str]:
    """Extract all URLs and return their domains from a text block.

    Args:
        text: Arbitrary text that may contain URLs.

    Returns:
        Deduplicated list of registered domains found in the text.
    """
    url_pattern = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+")
    matches = url_pattern.findall(text)

    domains: List[str] = []
    seen: set = set()

    for match in matches:
        domain = extract_domain(match)
        if domain and domain not in seen:
            seen.add(domain)
            domains.append(domain)

    return domains


# ------------------------------------------------------------------
# Text similarity
# ------------------------------------------------------------------

def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity between two text strings based on word sets.

    Args:
        text_a: First text string.
        text_b: Second text string.

    Returns:
        A float between 0.0 (no overlap) and 1.0 (identical word sets).

    Examples:
        >>> jaccard_similarity("hello world", "hello there")
        0.333...  # {hello} / {hello, world, there}
    """
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())

    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def cosine_similarity(text_a: str, text_b: str) -> float:
    """Compute a simple token-overlap cosine similarity between two texts.

    Uses bag-of-words with binary presence (no TF-IDF weighting).

    Args:
        text_a: First text string.
        text_b: Second text string.

    Returns:
        A float between 0.0 and 1.0.

    Examples:
        >>> cosine_similarity("hello world", "hello universe")
        0.5
    """
    words_a = text_a.lower().split()
    words_b = text_b.lower().split()

    all_words = set(words_a) | set(words_b)
    if not all_words:
        return 1.0

    vec_a = {w: 1 for w in words_a}
    vec_b = {w: 1 for w in words_b}

    dot_product = sum(1 for w in all_words if w in vec_a and w in vec_b)
    mag_a = len(words_a) ** 0.5
    mag_b = len(words_b) ** 0.5

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot_product / (mag_a * mag_b)


# ------------------------------------------------------------------
# Avatar hash comparison
# ------------------------------------------------------------------

def compute_image_hash(data: bytes, algorithm: str = "md5") -> str:
    """Compute a hash of raw image bytes.

    Args:
        data: Raw image bytes.
        algorithm: Hash algorithm (``md5``, ``sha1``, ``sha256``).

    Returns:
        Hex digest string.

    Raises:
        ValueError: If the algorithm is not supported.

    Examples:
        >>> compute_image_hash(b"fake_image_bytes")
        '1e4c...'
    """
    algorithm = algorithm.lower()
    if algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def compare_avatar_hashes(
    hash_a: str,
    hash_b: str,
    algorithm: str = "md5",
) -> Tuple[bool, float]:
    """Compare two avatar hashes and return whether they match.

    For MD5, only exact match is meaningful. For perceptual hashing
    (when supported), returns a similarity score.

    Args:
        hash_a: First hash string (hex).
        hash_b: Second hash string (hex).
        algorithm: Hash algorithm used (default ``md5``).

    Returns:
        Tuple of (is_match, similarity_score). For MD5, score is
        1.0 if exact match, 0.0 otherwise.
    """
    if algorithm in ("md5", "sha1", "sha256"):
        if hash_a.lower() == hash_b.lower():
            return True, 1.0
        return False, 0.0

    raise ValueError(f"Unsupported comparison algorithm: {algorithm}")


# ------------------------------------------------------------------
# Username sanitization
# ------------------------------------------------------------------

def sanitize_username(username: str) -> str:
    """Normalize a username by stripping whitespace and lowercasing.

    Args:
        username: Raw username string.

    Returns:
        Sanitized username.
    """
    return username.strip().lower()


def is_valid_username(username: str) -> bool:
    """Check if a string is a reasonable username.

    Must be non-empty, contain at least 2 characters, and use only
    allowed characters (letters, digits, underscores, dots, hyphens).

    Args:
        username: Username string to validate.

    Returns:
        True if the username appears valid.
    """
    if not username or len(username) < 2:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_.-]+$", username))
