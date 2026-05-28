"""
Merger Validator

Validates the output of the ShowScheduler (Merger) step, which combines
bumps and content into cohesive lineup tables.

Tables Validated:
- lineup_vX_uncut: Uncut lineups (pre-commercial break)
- lineup_vX: Final lineups (post-commercial break)
- lineup_vX_cutless: Cutless lineups (post CutlessFinalizer)
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class MergerValidator(BaseValidator):
    """Validates ShowScheduler/Merger step output"""

    @property
    def step_name(self) -> str:
        return "ShowScheduler/Merger"

    @property
    def required_tables(self) -> list:
        return []  # Check dynamically for any lineup table

    @property
    def pipeline_order(self) -> int:
        return 8  # Eighth step in pipeline

    def has_completed(self) -> bool:
        """
        Check if ShowScheduler/Merger has completed.

        Overrides base implementation to check for ANY lineup_vX* table.
        Since we support multiple Toonami versions (0-9), we can't use required_tables.

        Returns:
            bool: True if at least one lineup table exists with data
        """
        for version in range(10):
            uncut_table = f"lineup_v{version}_uncut"
            final_table = f"lineup_v{version}"
            cutless_table = f"lineup_v{version}_cutless"

            if self.check_table_exists(uncut_table) and self.get_row_count(uncut_table) > 0:
                return True

            if self.check_table_exists(final_table) and self.get_row_count(final_table) > 0:
                return True

            if self.check_table_exists(cutless_table) and self.get_row_count(cutless_table) > 0:
                return True

        return False

    def validate(self) -> ValidationResult:
        """
        Validate Merger output.

        Checks:
        1. At least one lineup table exists (uncut or final)
        2. Lineups have minimum anime episode count
        3. Required columns are present
        4. BLOCK_IDs are populated
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check for lineup tables
        metadata = self.get_processing_metadata()
        is_cutless_mode = metadata.get('is_cutless', False)

        uncut_tables = []
        final_tables = []
        cutless_tables = []

        for version in range(10):
            uncut_table = f"lineup_v{version}_uncut"
            final_table = f"lineup_v{version}"
            cutless_table = f"lineup_v{version}_cutless"

            if self.check_table_exists(uncut_table):
                uncut_tables.append((version, uncut_table))

            if self.check_table_exists(final_table):
                final_tables.append((version, final_table))

            if self.check_table_exists(cutless_table):
                cutless_tables.append((version, cutless_table))

        if not uncut_tables and not final_tables and not cutless_tables:
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "No lineup tables found",
                "Expected at least one lineup_vX* table",
                "Run ShowScheduler/Merger to create lineup tables"
            )
            return result

        if is_cutless_mode and not cutless_tables:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "Cutless mode detected but no lineup_vX_cutless tables were found",
                "CutlessFinalizer should create lineup_vX_cutless tables for each version",
                "Re-run CutlessFinalizer (and BumpCalculator if required) to create cutless lineups"
            )

        result.is_completed = True

        # Validate uncut lineups
        for version, table_name in uncut_tables:
            self._validate_lineup_table(result, version, table_name, lineup_type="uncut")

        # Validate final lineups
        for version, table_name in final_tables:
            self._validate_lineup_table(result, version, table_name, lineup_type="final")

        # Validate cutless lineups
        for version, table_name in cutless_tables:
            self._validate_lineup_table(result, version, table_name, lineup_type="cutless")

        result.metadata["uncut_versions"] = [v for v, _ in uncut_tables]
        result.metadata["final_versions"] = [v for v, _ in final_tables]
        result.metadata["cutless_versions"] = [v for v, _ in cutless_tables]

        return result

    def _validate_lineup_table(self, result: ValidationResult, version: int, table_name: str, lineup_type: str):
        """
        Validate a specific lineup table.

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the lineup table
            lineup_type: 'uncut', 'final', or 'cutless'
        """
        row_count = self.get_row_count(table_name)

        if row_count == 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version} {lineup_type} lineup is empty",
                f"Table {table_name} has no data",
                f"This may indicate no content for version {version}",
                table=table_name
            )
            return

        # Check required columns
        required_columns = ["FULL_FILE_PATH", "BLOCK_ID"]
        missing_columns = self.check_required_columns(table_name, required_columns)

        if missing_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Version {version} {lineup_type} lineup missing columns",
                f"Missing columns: {', '.join(missing_columns)}",
                "Re-run ShowScheduler/Merger to rebuild lineup",
                table=table_name
            )
            return

        # Count anime episodes (must have at least 6 per test suite)
        anime_count = self.count_anime_episodes(table_name, "FULL_FILE_PATH")

        min_anime = 6  # From test suite requirements
        if anime_count < min_anime:
            self.add_issue(
                result,
                ValidationLevel.WARNING if anime_count > 0 else ValidationLevel.ERROR,
                f"Version {version} {lineup_type} lineup has insufficient anime episodes",
                f"Found {anime_count} anime episodes, expected at least {min_anime}",
                "Add more anime episodes to your library or check episode filtering",
                table=table_name
            )

        result.metadata[f"v{version}_{lineup_type}_total"] = row_count
        result.metadata[f"v{version}_{lineup_type}_anime"] = anime_count
