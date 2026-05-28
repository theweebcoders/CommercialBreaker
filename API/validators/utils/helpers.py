"""
Validation Helper Functions

Utility functions used across multiple validators for common validation tasks.
"""

import os
import re
from functools import lru_cache
from typing import Set

from API.validators.utils.config import (
    BLOCK_ID_PATTERN,
    GENERIC_BUMP_KEYWORDS,
    VERSION_INDICATORS,
    TIMESTAMP_TOLERANCE_SEC
)

_EPISODE_PATTERN = re.compile(r"S\d{2}E\d{2}", re.IGNORECASE)


def _normalize_name(value: str) -> str:
    """Lowercase and collapse non-alphanumerics to spaces."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _filename_stem(file_path: str) -> str:
    """Return lowercase filename without extension."""
    return os.path.splitext(os.path.basename(file_path or ""))[0]


def _contains_episode_pattern(text: str) -> bool:
    return bool(_EPISODE_PATTERN.search(text or ""))


@lru_cache(maxsize=1)
def _get_network_token() -> str:
    """Normalized network name (cached)."""
    try:
        import config  # pylint: disable=import-error

        return _normalize_name(getattr(config, "network", ""))
    except Exception:
        return ""


@lru_cache(maxsize=1)
def _get_generic_aliases() -> Set[str]:
    """Normalized set of generic bump names/keywords."""
    aliases: Set[str] = set()

    for keyword in GENERIC_BUMP_KEYWORDS:
        normalized = _normalize_name(keyword)
        if normalized:
            aliases.add(normalized)

    try:
        import config  # pylint: disable=import-error

        extra = getattr(config, "generic_bumps", [])
    except Exception:
        extra = []

    for keyword in extra or []:
        normalized = _normalize_name(keyword)
        if normalized:
            aliases.add(normalized)

    return aliases


def _strip_network_prefix(normalized_name: str, network_token: str) -> str:
    """Remove the normalized network prefix and version digits from a name."""
    if network_token and normalized_name.startswith(network_token):
        remainder = normalized_name[len(network_token):].strip()
        # Drop leading version identifiers like "2 0" or "v9"
        remainder = re.sub(r"^(?:v?\d+\s*)+", "", remainder).strip()
        return remainder
    return normalized_name


def is_generic_bump(file_path: str) -> bool:
    """
    Check if a file path represents a generic bump.

    Generic bumps can appear anywhere in the interleaving pattern
    without violating placement rules.

    Args:
        file_path: Full file path to check

    Returns:
        True if path indicates a generic bump, False otherwise
    """
    stem = _filename_stem(file_path)
    if not stem or _contains_episode_pattern(stem):
        return False

    normalized = _normalize_name(stem)
    if not normalized:
        return False

    aliases = _get_generic_aliases()
    network_token = _get_network_token()
    remainder = _strip_network_prefix(normalized, network_token)

    if remainder in aliases or normalized in aliases:
        return True

    remainder_tokens = remainder.split()
    if remainder_tokens:
        first = remainder_tokens[0]
        if first in aliases:
            # Allow numeric suffixes (e.g., "robot 5")
            if len(remainder_tokens) == 1 or all(token.isdigit() for token in remainder_tokens[1:]):
                return True

    return False


def is_bump(file_path: str) -> bool:
    """
    Check if file path represents a bump (not anime).

    Uses the same logic as the main processing tools: identify files whose
    filenames begin with the network name or match the configured generic
    bump aliases, while treating anything with an episode pattern as anime.

    Args:
        file_path: Full file path to check

    Returns:
        True if bump, False if anime

    Examples:
        >>> is_bump("/app/bump/Toonami 2 0 Naruto back 4.mp4")
        True
        >>> is_bump("/app/anime/Naruto - S01E05 - Episode Title.mkv")
        False
    """
    stem = _filename_stem(file_path)
    if not stem:
        return False

    # Episodes include SxxExx pattern anywhere in filename
    if _contains_episode_pattern(stem):
        return False

    normalized = _normalize_name(stem)
    if not normalized:
        return False

    network_token = _get_network_token()
    if network_token and network_token != "networkless":
        # Bumps always start with the active network name (e.g., "Toonami")
        if normalized.startswith(network_token):
            return True

    if is_generic_bump(file_path):
        return True

    return False


def is_anime(file_path: str) -> bool:
    """
    Check if file path represents anime episode (not a bump).

    Inverse of is_bump() - provided for readability in validator code.

    Args:
        file_path: Full file path to check

    Returns:
        True if anime, False if bump

    Examples:
        >>> is_anime("/app/anime/Naruto - S01E05 - Episode Title.mkv")
        True
        >>> is_anime("/app/bump/Toonami 2 0 Naruto back 4.mp4")
        False
    """
    return not is_bump(file_path)


def is_valid_block_id(block_id: str) -> bool:
    """
    Validate BLOCK_ID format.

    Args:
        block_id: BLOCK_ID string to validate

    Returns:
        True if BLOCK_ID matches expected pattern, False otherwise
    """
    if not block_id:
        return False
    return BLOCK_ID_PATTERN.match(str(block_id)) is not None


def extract_version_from_path(file_path: str) -> int:
    """
    Extract Toonami version number from bump file path.

    Args:
        file_path: Full file path to analyze

    Returns:
        Version number (2, 3, 8, 9) or None if not detectable
    """
    path_lower = file_path.lower()

    for version, indicators in VERSION_INDICATORS.items():
        if any(indicator in path_lower for indicator in indicators):
            return version

    return None


def is_timestamp_equal(ts1: float, ts2: float, tolerance: float = TIMESTAMP_TOLERANCE_SEC) -> bool:
    """
    Compare two timestamps with tolerance for floating point errors.

    Args:
        ts1: First timestamp
        ts2: Second timestamp
        tolerance: Acceptable difference (default: TIMESTAMP_TOLERANCE_SEC)

    Returns:
        True if timestamps are equal within tolerance
    """
    if ts1 is None or ts2 is None:
        return False
    return abs(ts1 - ts2) <= tolerance
