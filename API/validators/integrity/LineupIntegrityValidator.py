"""
LineupIntegrity Validator

Validates the integrity of final lineup tables by checking bump placement rules
and transition logic. This implements the comprehensive validation from the test suite.

Validates:
- Multibumps → Anime transitions
- Intro → Anime with matching BLOCK_ID
- Back → Anime sequences
- Anime → To Ads sequences
- Chain continuity
- Episode-aware validation
"""

import re
from typing import List, Dict, Any, Optional

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel
from API.validators.utils import (
    VERSION_INDICATORS,
    extract_version_from_path
)


class LineupIntegrityValidator(BaseValidator):
    """Validates lineup integrity with comprehensive bump placement rules"""

    def __init__(self):
        """Initialize validator and cache bump placement data."""
        super().__init__()
        self._bump_placement_cache = None

    @property
    def step_name(self) -> str:
        return "LineupIntegrity"

    @property
    def required_tables(self) -> list:
        return []  # Check dynamically for lineup tables

    @property
    def pipeline_order(self) -> int:
        return 20  # Final validation step

    def _load_bump_placement_cache(self):
        """
        Load bump placement data from lineup_prep_out table.

        Creates a mapping of FULL_FILE_PATH → PLACEMENT_2 for quick lookup.
        This allows us to properly identify bump types instead of using string matching.
        """
        if self._bump_placement_cache is not None:
            return

        self._bump_placement_cache = {}

        if not self.table_exists('lineup_prep_out'):
            return

        rows = self.fetchall_as_dicts("SELECT FULL_FILE_PATH, PLACEMENT_2 FROM lineup_prep_out")

        for row in rows:
            path = row.get('FULL_FILE_PATH')
            placement = row.get('PLACEMENT_2')
            if path and placement:
                self._bump_placement_cache[path] = placement.lower()

    def _get_bump_placement_type(self, file_path: str) -> Optional[str]:
        """
        Get the bump placement type for a file path.

        Args:
            file_path: Full file path to check

        Returns:
            Placement type ('back', 'to ads', 'intro', 'generic', etc.) or None if not a bump
        """
        self._load_bump_placement_cache()
        return self._bump_placement_cache.get(file_path)

    def is_bump(self, file_path: str) -> bool:
        """Use placement metadata when available before falling back to BaseValidator logic."""
        placement = self._get_bump_placement_type(file_path)
        if placement is not None:
            return True
        return super().is_bump(file_path)

    def _is_bump_entry(self, entry: Optional[Dict[str, Any]]) -> bool:
        """Determine if a lineup row represents a bump using row context before filename heuristics."""
        if not entry:
            return False

        # Multi-show bumps always have codes populated
        code = entry.get("Code")
        if code is not None and str(code).strip() != "":
            return True

        # Some tables keep placement metadata directly on the row
        placement = entry.get("PLACEMENT_2") or entry.get("PLACEMENT")
        if placement:
            return True

        file_path = entry.get("FULL_FILE_PATH", "")
        if file_path and not self.validate_episode_pattern(file_path):
            return True

        return self.is_bump(file_path)

    def _is_bump_type(self, file_path: str, expected_type: str) -> bool:
        """
        Check if a file path is a specific bump type.

        Args:
            file_path: Full file path to check
            expected_type: Expected placement type (e.g., 'back', 'to ads', 'intro')

        Returns:
            True if file is a bump of the expected type, False otherwise
        """
        placement = self._get_bump_placement_type(file_path)
        if placement is None:
            return False
        return expected_type.lower() in placement

    def has_completed(self) -> bool:
        """
        Check if lineup integrity validation can run.

        Overrides base implementation to check for ANY final lineup_vX table.
        This is the final validation step that runs after all lineups are created.

        Returns:
            bool: True if at least one final lineup table exists with data
        """
        for version in range(10):
            table_name = f"lineup_v{version}"
            if self.check_table_exists(table_name) and self.get_row_count(table_name) > 0:
                return True
        return False

    def validate(self) -> ValidationResult:
        """
        Validate lineup integrity.

        Checks:
        1. Multibumps must be followed by anime
        2. Intro bumps must be followed by anime with same BLOCK_ID
        3. "Back" bumps must be followed by anime
        4. "To ads" bumps must be preceded by anime
        5. Chain continuity (optional strict mode)
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Find final lineup tables
        lineup_tables = []
        for version in range(10):
            table_name = f"lineup_v{version}"
            if self.check_table_exists(table_name):
                lineup_tables.append((version, table_name))

        if not lineup_tables:
            self.add_issue(
                result,
                ValidationLevel.INFO,
                "No final lineup tables found",
                "LineupIntegrity validation requires final lineup_vX tables",
                "Complete the pipeline to create final lineups"
            )
            return result

        result.is_completed = True

        # Validate each lineup table
        for version, table_name in lineup_tables:
            self._validate_lineup_integrity(result, version, table_name)

        return result

    def _validate_lineup_integrity(self, result: ValidationResult, version: int, table_name: str):
        """
        Validate integrity of a specific lineup table.

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the lineup table
        """
        lineup = self.get_all_rows(table_name)

        if len(lineup) == 0:
            return

        # Run all validation rules
        self._validate_multibump_to_anime(result, version, table_name, lineup)
        self._validate_intro_to_anime(result, version, table_name, lineup)
        self._validate_back_to_anime(result, version, table_name, lineup)
        self._validate_anime_to_to_ads(result, version, table_name, lineup)
        self._validate_chain_continuity(result, version, table_name, lineup)
        self._validate_version_consistency(result, version, table_name, lineup)

    def _validate_multibump_to_anime(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        lineup: List[Dict[str, Any]]
    ):
        """
        Rule: Multibumps (with Code) must be followed by anime.

        Args:
            result: ValidationResult to add issues to
            version: Version number
            table_name: Table name
            lineup: Lineup data
        """
        violations = []

        for i in range(len(lineup) - 1):
            current = lineup[i]
            next_entry = lineup[i + 1]

            # Check if current has Code (multibump indicator)
            code = current.get("Code")
            if code is not None and code != "":
                # Next entry should be anime
                next_path = next_entry.get("FULL_FILE_PATH", "")
                if self._is_bump_entry(next_entry):
                    violations.append({
                        'row': i,
                        'bump_path': current.get("FULL_FILE_PATH", ""),
                        'code': code,
                        'next_path': next_path
                    })

        if violations:
            # Create detailed error message listing all violations
            details_lines = [f"Multibumps with Code must be followed by anime. Found {len(violations)} violation(s):"]
            for v in violations[:5]:  # Show first 5 violations
                details_lines.append(f"  Row {v['row']}: {v['bump_path']} (Code: {v['code']})")
                details_lines.append(f"    → Followed by: {v['next_path']}")
            if len(violations) > 5:
                details_lines.append(f"  ... and {len(violations) - 5} more")

            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version}: {len(violations)} multibump → anime violation(s)",
                "\n".join(details_lines),
                "Check lineup merger logic and bump placement",
                table=table_name,
                row_index=violations[0]['row']
            )

        result.metadata[f"v{version}_multibump_violations"] = len(violations)

    def _validate_intro_to_anime(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        lineup: List[Dict[str, Any]]
    ):
        """
        Rule: Intro bumps starting new blocks must be followed by anime with same BLOCK_ID.

        Args:
            result: ValidationResult to add issues to
            version: Version number
            table_name: Table name
            lineup: Lineup data
        """
        violations = []

        for i in range(len(lineup) - 1):
            current = lineup[i]
            next_entry = lineup[i + 1]

            current_path = current.get("FULL_FILE_PATH", "")
            current_block = current.get("BLOCK_ID", "")

            # Check if this is an intro bump using proper database lookup
            # Also check for "uncut" which indicates intro bumps for uncut lineups
            is_intro = self._is_bump_type(current_path, 'intro') or "uncut" in current_path.lower()

            # Check if starting a new block
            is_new_block = True
            if i > 0:
                prev_block = lineup[i - 1].get("BLOCK_ID", "")
                is_new_block = prev_block != current_block

            if is_intro and is_new_block:
                # Next entry should be anime with same BLOCK_ID
                next_path = next_entry.get("FULL_FILE_PATH", "")
                next_block = next_entry.get("BLOCK_ID", "")

                if self.is_anime(next_path):
                    if next_block != current_block:
                        violations.append({
                            'row': i,
                            'intro_path': current_path,
                            'intro_block': current_block,
                            'anime_block': next_block
                        })
                else:
                    violations.append({
                        'row': i,
                        'intro_path': current_path,
                        'intro_block': current_block,
                        'next_path': next_path
                    })

        if violations:
            # Create detailed error message listing all violations
            details_lines = [f"Intro bumps should be followed by anime with matching BLOCK_ID. Found {len(violations)} violation(s):"]
            for v in violations[:5]:  # Show first 5 violations
                details_lines.append(f"  Row {v['row']}: {v.get('intro_path', 'N/A')}")
                if 'anime_block' in v:
                    details_lines.append(f"    Intro BLOCK_ID: {v['intro_block']}, Anime BLOCK_ID: {v['anime_block']}")
                else:
                    details_lines.append(f"    → Followed by non-anime: {v['next_path']}")
            if len(violations) > 5:
                details_lines.append(f"  ... and {len(violations) - 5} more")

            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version}: {len(violations)} intro → anime BLOCK_ID violation(s)",
                "\n".join(details_lines),
                "Check BLOCK_ID assignment logic",
                table=table_name,
                row_index=violations[0]['row']
            )

        result.metadata[f"v{version}_intro_violations"] = len(violations)

    def _validate_back_to_anime(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        lineup: List[Dict[str, Any]]
    ):
        """
        Rule: "Back" bumps must be followed by anime.

        Args:
            result: ValidationResult to add issues to
            version: Version number
            table_name: Table name
            lineup: Lineup data
        """
        violations = []

        for i in range(len(lineup) - 1):
            current = lineup[i]
            next_entry = lineup[i + 1]

            current_path = current.get("FULL_FILE_PATH", "")

            # Check if this is a "back" bump using proper database lookup
            if self._is_bump_type(current_path, 'back'):
                # Next entry should be anime
                next_path = next_entry.get("FULL_FILE_PATH", "")
                if self._is_bump_entry(next_entry):
                    violations.append({
                        'row': i,
                        'back_bump': current_path,
                        'next_path': next_path
                    })

        if violations:
            # Create detailed error message listing all violations
            details_lines = [f"'Back' bumps should be followed by anime. Found {len(violations)} violation(s):"]
            for v in violations[:5]:  # Show first 5 violations
                details_lines.append(f"  Row {v['row']}: {v['back_bump']}")
                details_lines.append(f"    → Followed by: {v['next_path']}")
            if len(violations) > 5:
                details_lines.append(f"  ... and {len(violations) - 5} more")

            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version}: {len(violations)} back → anime violation(s)",
                "\n".join(details_lines),
                "Check bump placement after commercial breaks",
                table=table_name,
                row_index=violations[0]['row']
            )

        result.metadata[f"v{version}_back_violations"] = len(violations)

    def _validate_anime_to_to_ads(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        lineup: List[Dict[str, Any]]
    ):
        """
        Rule: "To ads" bumps must be preceded by anime.

        Args:
            result: ValidationResult to add issues to
            version: Version number
            table_name: Table name
            lineup: Lineup data
        """
        violations = []

        for i in range(1, len(lineup)):
            current = lineup[i]
            prev_entry = lineup[i - 1]

            current_path = current.get("FULL_FILE_PATH", "")

            # Check if this is a "to ads" bump using proper database lookup
            if self._is_bump_type(current_path, 'to ads'):
                # Previous entry should be anime
                prev_path = prev_entry.get("FULL_FILE_PATH", "")
                if self._is_bump_entry(prev_entry):
                    violations.append({
                        'row': i,
                        'to_ads_bump': current_path,
                        'prev_path': prev_path
                    })

        if violations:
            # Create detailed error message listing all violations
            details_lines = [f"'To ads' bumps should be preceded by anime. Found {len(violations)} violation(s):"]
            for v in violations[:5]:  # Show first 5 violations
                details_lines.append(f"  Row {v['row']}: {v['to_ads_bump']}")
                details_lines.append(f"    → Preceded by: {v['prev_path']}")
            if len(violations) > 5:
                details_lines.append(f"  ... and {len(violations) - 5} more")

            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version}: {len(violations)} anime → to ads violation(s)",
                "\n".join(details_lines),
                "Check bump placement before commercial breaks",
                table=table_name,
                row_index=violations[0]['row']
            )

        result.metadata[f"v{version}_to_ads_violations"] = len(violations)

    def _validate_chain_continuity(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        lineup: List[Dict[str, Any]]
    ):
        """
        Rule: Chain continuity - multibumps should form coherent chains.
        This is a warning-level check (non-strict mode per test suite).

        Args:
            result: ValidationResult to add issues to
            version: Version number
            table_name: Table name
            lineup: Lineup data
        """
        # Extract multibump chain
        chain_breaks = []

        last_multibump_shows = None

        for i, entry in enumerate(lineup):
            code = entry.get("Code")
            if code:
                # Parse show names from Code (simplified)
                # Real implementation would decode using codes table
                path = entry.get("FULL_FILE_PATH", "")

                # Check for "Next" or "Later" keywords indicating chain
                if "next" in path.lower() or "later" in path.lower():
                    # This multibump announces next shows
                    # The following anime should match
                    if i + 1 < len(lineup):
                        next_entry = lineup[i + 1]
                        next_path = next_entry.get("FULL_FILE_PATH", "")

                        # Basic chain validation (non-strict)
                        if self._is_bump_entry(next_entry):
                            chain_breaks.append({
                                'row': i,
                                'bump_path': path
                            })

        if chain_breaks:
            # This is INFO level since chain validation is non-strict
            self.add_issue(
                result,
                ValidationLevel.INFO,
                f"Version {version}: {len(chain_breaks)} potential chain continuity issue(s)",
                "Some multibump chains may not flow optimally",
                "This is informational - chains are validated in non-strict mode",
                table=table_name
            )

        result.metadata[f"v{version}_chain_breaks"] = len(chain_breaks)

    def _validate_version_consistency(
        self,
        result: ValidationResult,
        version: int,
        table_name: str,
        lineup: List[Dict[str, Any]]
    ):
        """
        Rule: Bumps in a lineup should match the lineup version.

        Checks that V2 lineups don't have V3/V8/V9 bumps mixed in, etc.
        This helps maintain era-appropriate viewing experience.

        Args:
            result: ValidationResult to add issues to
            version: Expected Toonami version number for this lineup
            table_name: Table name
            lineup: Lineup data
        """
        mismatched_bumps = []

        # Version 8 ("Mixed") intentionally combines eras, so skip mismatch detection
        if version == 8:
            result.metadata[f"v{version}_version_mismatches"] = 0
            return

        for i, entry in enumerate(lineup):
            path = entry.get('FULL_FILE_PATH', '').lower()

            # Only check bump files (skip anime)
            if self.is_anime(path):
                continue

            # Skip if it's not a network bump (e.g., intro/generic/local files)
            # Look for "toonami" in path to identify network bumps
            if 'toonami' not in path:
                continue

            # Extract version from bump path
            bump_version = extract_version_from_path(path)

            # If we detected a version and it doesn't match the lineup version
            if bump_version is not None and bump_version != version:
                mismatched_bumps.append({
                    'row': i,
                    'path': entry.get('FULL_FILE_PATH', ''),
                    'bump_version': bump_version,
                    'lineup_version': version
                })

        # Report mismatches
        if mismatched_bumps:
            # Get unique versions found
            found_versions = set(b['bump_version'] for b in mismatched_bumps)
            version_str = ', '.join([f"V{v}" for v in sorted(found_versions)])

            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version}: {len(mismatched_bumps)} bump(s) from different version(s) detected",
                f"Found bumps from {version_str} in V{version} lineup. This may be intentional for variety but could affect era authenticity.",
                "This is not necessarily an error - some users mix versions intentionally. Verify bump selection is correct for your desired viewing experience.",
                table=table_name,
                row_index=mismatched_bumps[0]['row']
            )

        result.metadata[f"v{version}_version_mismatches"] = len(mismatched_bumps)
