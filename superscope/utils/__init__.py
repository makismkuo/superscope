"""SuperScope utilities — helpers for domain extraction, text similarity, and hashing."""

from superscope.utils.helpers import (
    compare_avatar_hashes,
    compute_image_hash,
    cosine_similarity,
    extract_all_domains,
    extract_domain,
    is_valid_username,
    jaccard_similarity,
    sanitize_username,
)

__all__ = [
    "extract_domain",
    "extract_all_domains",
    "jaccard_similarity",
    "cosine_similarity",
    "compute_image_hash",
    "compare_avatar_hashes",
    "sanitize_username",
    "is_valid_username",
]
