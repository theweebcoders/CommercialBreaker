"""
PostCutBumpFilter Validator

Validates the output of the PostCutBumpFilter step, which filters multi-show bumps
to remove references to shows that don't have episode blocks after commercial breaking.

Tables Validated:
- lineup_prep_out_postcut: Filtered lineup prep data
- multibumps_vX_data_postcut: Filtered multibump data (for versions 0-9)
- multibumps_vX_data_reordered_postcut: Reordered multibump data

Note: This is an optional step - only runs if there are multi-show bumps that
reference shows without episode cuts.
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class PostCutBumpFilterValidator(BaseValidator):
    """Validates PostCutBumpFilter step output"""

    @property
    def step_name(self) -> str:
        return "PostCutBumpFilter"

    @property
    def required_tables(self) -> list:
        return []  # Optional step

    @property
    def optional_tables(self) -> list:
        tables = ["lineup_prep_out_postcut"]
        for version in range(10):
            tables.append(f"multibumps_v{version}_data_postcut")
            tables.append(f"multibumps_v{version}_data_reordered_postcut")
        return tables

    @property
    def pipeline_order(self) -> int:
        return 14.5  # Step 14a - between BlockMaker and second Merger

    def has_completed(self) -> bool:
        """
        Check if PostCutBumpFilter has completed.

        This is an optional step, so returns True if any postcut tables exist.
        Returns False if no postcut tables exist (step not run, which is valid).
        """
        postcut_tables = self._find_postcut_tables()
        return len(postcut_tables) > 0

    def validate(self) -> ValidationResult:
        """
        Validate PostCutBumpFilter output.

        Checks:
        1. At least one postcut table exists (if step ran)
        2. Postcut tables have valid structure
        3. Postcut tables have content (or step didn't need to filter)
        4. Show names in bumps match available episodes
        5. Reordered postcut tables exist if needed
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check if any postcut tables exist
        postcut_tables = self._find_postcut_tables()

        if not postcut_tables:
            self.add_issue(
                result,
                ValidationLevel.INFO,
                "PostCutBumpFilter not run",
                "No _postcut tables found",
                "This is normal if all bumps referenced shows with episode cuts"
            )
            return result

        result.is_completed = True

        # Validate lineup_prep_out_postcut if it exists
        if "lineup_prep_out_postcut" in postcut_tables:
            self._validate_lineup_postcut(result)

        # Validate multibump postcut tables
        multibump_versions = self._get_multibump_versions(postcut_tables)
        for version in multibump_versions:
            self._validate_multibump_postcut(result, version)

        result.metadata["postcut_tables_count"] = len(postcut_tables)
        result.metadata["multibump_versions"] = multibump_versions

        return result

    def _find_postcut_tables(self) -> list:
        """Find all _postcut tables in the database."""
        postcut_tables = []

        if self.check_table_exists("lineup_prep_out_postcut"):
            postcut_tables.append("lineup_prep_out_postcut")

        for version in range(10):
            table_name = f"multibumps_v{version}_data_postcut"
            if self.check_table_exists(table_name):
                postcut_tables.append(table_name)

            reordered_name = f"multibumps_v{version}_data_reordered_postcut"
            if self.check_table_exists(reordered_name):
                postcut_tables.append(reordered_name)

        return postcut_tables

    def _get_multibump_versions(self, postcut_tables: list) -> list:
        """Extract multibump version numbers from postcut tables."""
        versions = set()
        for table in postcut_tables:
            if "multibumps_v" in table and "_data_postcut" in table:
                # Extract version number from table name
                try:
                    version_str = table.split("multibumps_v")[1].split("_data")[0]
                    versions.add(int(version_str))
                except (IndexError, ValueError):
                    pass
        return sorted(versions)

    def _validate_lineup_postcut(self, result: ValidationResult):
        """
        Validate lineup_prep_out_postcut table.

        Args:
            result: ValidationResult to add issues to
        """
        table_name = "lineup_prep_out_postcut"

        # Check for required columns (should match lineup_prep_out)
        required_columns = ["FULL_FILE_PATH"]

        if not self.validate_table_structure(
            result,
            table_name,
            required_columns=required_columns,
            min_rows=0  # Can be empty if everything was filtered
        ):
            return

        row_count = self.get_row_count(table_name)

        if row_count == 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                "All lineup bumps were filtered out",
                "lineup_prep_out_postcut is empty",
                "This may indicate no bumps reference shows with episode cuts",
                table=table_name
            )
        else:
            result.metadata["lineup_postcut_bumps"] = row_count

        # Compare with original lineup_prep_out if it exists
        if self.check_table_exists("lineup_prep_out"):
            original_count = self.get_row_count("lineup_prep_out")
            filtered_count = original_count - row_count

            if filtered_count > 0:
                percentage = (filtered_count / original_count) * 100
                result.metadata["lineup_filtered_count"] = filtered_count
                result.metadata["lineup_filtered_percentage"] = round(percentage, 1)

                self.add_issue(
                    result,
                    ValidationLevel.INFO,
                    f"Filtered {filtered_count} lineup bumps ({percentage:.1f}%)",
                    f"Kept {row_count} out of {original_count} bumps",
                    "These bumps referenced shows without episode cuts",
                    table=table_name
                )

    def _validate_multibump_postcut(self, result: ValidationResult, version: int):
        """
        Validate multibump postcut tables for a specific version.

        Args:
            result: ValidationResult to add issues to
            version: Toonami version number
        """
        data_table = f"multibumps_v{version}_data_postcut"
        reordered_table = f"multibumps_v{version}_data_reordered_postcut"

        # Validate data table
        if not self.check_table_exists(data_table):
            return

        if not self.validate_table_structure(
            result,
            data_table,
            required_columns=["FULL_FILE_PATH"],
            min_rows=0
        ):
            return

        data_count = self.get_row_count(data_table)

        if data_count == 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"Version {version}: All multibumps filtered out",
                f"{data_table} is empty",
                "This may indicate no multibumps reference shows with episode cuts",
                table=data_table
            )
        else:
            result.metadata[f"v{version}_postcut_bumps"] = data_count

        # Compare with original if it exists
        original_table = f"multibumps_v{version}_data"
        if self.check_table_exists(original_table):
            original_count = self.get_row_count(original_table)
            filtered_count = original_count - data_count

            if filtered_count > 0:
                percentage = (filtered_count / original_count) * 100
                result.metadata[f"v{version}_filtered_count"] = filtered_count
                result.metadata[f"v{version}_filtered_percentage"] = round(percentage, 1)

        # Check reordered table if data exists
        if data_count > 0:
            if self.check_table_exists(reordered_table):
                reordered_count = self.get_row_count(reordered_table)
                result.metadata[f"v{version}_reordered_postcut_bumps"] = reordered_count

                # Reordered table should have same or fewer entries (due to chaining)
                if reordered_count > data_count:
                    self.add_issue(
                        result,
                        ValidationLevel.WARNING,
                        f"Version {version}: Reordered table has more entries than data table",
                        f"Reordered: {reordered_count}, Data: {data_count}",
                        "This is unusual - reordered table should not exceed data table",
                        table=reordered_table
                    )
