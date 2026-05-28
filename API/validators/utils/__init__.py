"""
Validation Utilities

This module provides configuration constants and helper functions
for the validator system.
"""

from API.validators.utils.config import *
from API.validators.utils.helpers import *

__all__ = [
    # Constants from config
    'BLOCK_ID_PATTERN',
    'BLOCK_ID_DESCRIPTION',
    'TIMESTAMP_TOLERANCE_SEC',
    'MIN_BUMP_DURATION_MS',
    'MAX_BUMP_DURATION_MS',
    'TYPICAL_BUMP_MIN_MS',
    'TYPICAL_BUMP_MAX_MS',
    'MIN_EPISODE_PARTS',
    'MAX_EPISODE_PARTS',
    'TYPICAL_PARTS_MIN',
    'TYPICAL_PARTS_MAX',
    'VERSION_INDICATORS',
    'ORPHAN_WARNING_THRESHOLD',
    'ORPHAN_ERROR_THRESHOLD',
    'GENERIC_BUMP_KEYWORDS',
    'REQUIRED_BUMP_TYPES',
    'PLATFORM_INDICATORS',
    'CUTLESS_TABLE_PATTERNS',
    'CUTLESS_COLUMN_INDICATORS',

    # Helper functions
    'is_generic_bump',
    'is_valid_block_id',
    'extract_version_from_path',
    'is_timestamp_equal',
]
