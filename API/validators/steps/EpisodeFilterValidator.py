"""
EpisodeFilter Validator

Validates the output of the EpisodeFilter step, which filters bump files out of
the uncut lineup to create a list of just episode files for commercial breaking.

Tables Validated:
- lineup_v8_uncut_filtered: Filtered episode list (bumps removed, Code/BLOCK_ID dropped)

Note: This is a REQUIRED step in the pipeline.
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel
import config


class EpisodeFilterValidator(BaseValidator):
    """Validates EpisodeFilter step output"""

    @property
    def step_name(self) -> str:
        return "EpisodeFilter"

    @property
    def required_tables(self) -> list:
        return ["lineup_v8_uncut_filtered"]

    @property
    def pipeline_order(self) -> int:
        return 9  # Ninth step in pipeline

    def has_completed(self) -> bool:
        """
        Check if EpisodeFilter has completed.

        This is a required step. Returns True only if the filtered table exists with data.
        """
        return (
            self.check_table_exists("lineup_v8_uncut_filtered") and
            self.get_row_count("lineup_v8_uncut_filtered") > 0
        )

    def validate(self) -> ValidationResult:
        """
        Validate EpisodeFilter output.

        Checks:
        1. lineup_v8_uncut_filtered table exists (optional step)
        2. Table contains only episode files (no bumps)
        3. Code and BLOCK_ID columns have been dropped
        4. FULL_FILE_PATH column exists
        5. Episodes match SxxExx pattern
        6. No network name in paths (for normal mode)
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check if filtered table exists
        if not self.check_table_exists("lineup_v8_uncut_filtered"):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "EpisodeFilter not run",
                "lineup_v8_uncut_filtered table not found",
                "Run EpisodeFilter to create filtered episode list for commercial breaking"
            )
            return result

        result.is_completed = True

        # Validate table structure
        if not self.validate_table_structure(
            result,
            "lineup_v8_uncut_filtered",
            required_columns=["FULL_FILE_PATH"],
            min_rows=1
        ):
            return result

        # Validate that Code and BLOCK_ID columns were dropped
        all_columns = self.get_column_names("lineup_v8_uncut_filtered")

        if "Code" in all_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "Code column not dropped",
                "lineup_v8_uncut_filtered should not have Code column",
                "Re-run EpisodeFilter to properly drop Code column",
                table="lineup_v8_uncut_filtered"
            )
            result.is_valid = False

        if "BLOCK_ID" in all_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "BLOCK_ID column not dropped",
                "lineup_v8_uncut_filtered should not have BLOCK_ID column",
                "Re-run EpisodeFilter to properly drop BLOCK_ID column",
                table="lineup_v8_uncut_filtered"
            )
            result.is_valid = False

        # Get filtered data
        filtered_data = self.get_all_rows("lineup_v8_uncut_filtered")

        if not filtered_data:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "Filtered table is empty",
                "No episodes found after filtering",
                "Check that your uncut lineup contains actual episode files",
                table="lineup_v8_uncut_filtered"
            )
            result.is_valid = False
            return result

        # Validate that entries are episodes (not bumps)
        self._validate_episode_filtering(result, filtered_data)

        # Count valid episodes
        episode_count = sum(1 for entry in filtered_data
                          if self.is_anime(entry.get("FULL_FILE_PATH", "")))

        result.metadata["filtered_episodes"] = len(filtered_data)
        result.metadata["valid_episode_patterns"] = episode_count

        return result

    def _validate_episode_filtering(self, result: ValidationResult, filtered_data: list):
        """
        Validate that bump files were properly filtered out.

        Args:
            result: ValidationResult to add issues to
            filtered_data: List of filtered entries
        """
        network = getattr(config, 'network', 'Toonami')
        network_lower = network.lower()
        is_networkless = network_lower == "networkless"

        bump_indicators = 0
        non_episode_patterns = 0

        for entry in filtered_data:
            file_path = entry.get("FULL_FILE_PATH", "")

            if not file_path:
                continue

            file_path_lower = file_path.lower()

            # Check for bump folder indicators
            if '/bump' in file_path_lower or '\\bump' in file_path_lower:
                bump_indicators += 1
            elif '/special' in file_path_lower or '\\special' in file_path_lower:
                bump_indicators += 1

            # Check for network name in path (if not networkless mode)
            if not is_networkless and network_lower in file_path_lower:
                bump_indicators += 1

            # Check if entry is a bump (not an anime episode)
            if self.is_bump(file_path):
                non_episode_patterns += 1

        # Report issues
        if bump_indicators > 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{bump_indicators} potential bump files in filtered data",
                "Some files appear to be bumps based on path patterns",
                "Check that bump filtering logic is working correctly",
                table="lineup_v8_uncut_filtered"
            )

        if non_episode_patterns > 0:
            # This is a warning, not error, because some shows might have non-standard naming
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{non_episode_patterns} files don't match standard episode pattern",
                "Expected pattern: SxxExx (e.g., S01E01)",
                "Verify these are actual episodes with non-standard naming",
                table="lineup_v8_uncut_filtered"
            )

        result.metadata["potential_bumps"] = bump_indicators
        result.metadata["non_standard_naming"] = non_episode_patterns
