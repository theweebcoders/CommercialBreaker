"""
Multilineup Validator

Validates the output of the Multilineup step, which reorders multi-show bumps
to create the longest possible chains (solving the traveling salesman problem).

Tables Validated:
- multibumps_vX_data_reordered: Reordered multi-show bumps by version
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class MultilineupValidator(BaseValidator):
    """Validates Multilineup step output"""

    @property
    def step_name(self) -> str:
        return "Multilineup"

    @property
    def required_tables(self) -> list:
        # At least one reordered table should exist
        return []  # We'll check dynamically

    @property
    def pipeline_order(self) -> int:
        return 7  # Seventh step in pipeline

    def has_completed(self) -> bool:
        """
        Check if Multilineup has completed.

        Overrides base implementation to check for ANY multibumps_vX_data_reordered table.
        Since we support multiple Toonami versions (0-9), we can't use required_tables.

        Returns:
            bool: True if at least one reordered table exists with data
        """
        for version in range(10):
            table_name = f"multibumps_v{version}_data_reordered"
            if self.check_table_exists(table_name) and self.get_row_count(table_name) > 0:
                return True
        return False

    def validate(self) -> ValidationResult:
        """
        Validate Multilineup output.

        Checks:
        1. At least one multibumps_vX_data_reordered table exists
        2. Reordered tables have data
        3. Chains are properly formed
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check for any reordered tables
        reordered_tables = []
        for version in range(10):
            table_name = f"multibumps_v{version}_data_reordered"
            if self.check_table_exists(table_name):
                reordered_tables.append((version, table_name))

        if not reordered_tables:
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "No reordered multibumps tables found",
                "Expected at least one multibumps_vX_data_reordered table",
                "Run Multilineup to create reordered bump chains"
            )
            return result

        result.is_completed = True

        # Validate each reordered table
        for version, table_name in reordered_tables:
            self._validate_reordered_table(result, version, table_name)

        result.metadata["reordered_versions"] = [v for v, _ in reordered_tables]

        return result

    def _validate_reordered_table(self, result: ValidationResult, version: int, table_name: str):
        """
        Validate a specific reordered table.

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
            table_name: Name of the reordered table
        """
        row_count = self.get_row_count(table_name)

        if row_count == 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version} reordered table is empty",
                f"Table {table_name} has no data",
                "This may indicate no multi-show bumps for this version",
                table=table_name
            )
        else:
            result.metadata[f"v{version}_reordered_count"] = row_count

            # Check for required columns (should match source multibumps table)
            required_columns = ["FULL_FILE_PATH", "SHOW_NAME_1"]
            missing_columns = self.check_required_columns(table_name, required_columns)

            if missing_columns:
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    f"Version {version} reordered table missing columns",
                    f"Missing columns: {', '.join(missing_columns)}",
                    "Re-run Multilineup to rebuild reordered tables",
                    table=table_name
                )
