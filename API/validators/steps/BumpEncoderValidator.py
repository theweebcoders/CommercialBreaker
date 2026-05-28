"""
BumpEncoder Validator

Validates the output of the BumpEncoder step, which creates abbreviated codes
for bumps and separates them into singles and multibumps by version.

Tables Validated:
- codes: Mapping of abbreviation codes to full show names
- singles_data: Single-show bumps with codes
- multibumps_vX_data: Multi-show bumps by Toonami version (X = 0-9)
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class BumpEncoderValidator(BaseValidator):
    """Validates BumpEncoder step output"""

    @property
    def step_name(self) -> str:
        return "BumpEncoder"

    @property
    def required_tables(self) -> list:
        return ["codes"]

    @property
    def optional_tables(self) -> list:
        # Version-specific tables
        tables = ["singles_data"]
        for version in range(10):
            tables.append(f"multibumps_v{version}_data")
        return tables

    @property
    def pipeline_order(self) -> int:
        return 5  # Fifth step in pipeline

    def validate(self) -> ValidationResult:
        """
        Validate BumpEncoder output.

        Checks:
        1. codes table exists and has mappings
        2. At least one version-specific multibumps table exists
        3. Codes are properly formatted
        4. Version-specific data is separated correctly
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check codes table
        if not self.validate_table_structure(
            result,
            "codes",
            required_columns=["Code", "Name"],
            min_rows=1
        ):
            # Critical issues found
            return result

        # If codes table exists, step is at least partially completed
        result.is_completed = True

        # Validate code mappings
        self._validate_codes(result)

        # Check for version-specific tables
        self._validate_version_tables(result)

        # Validate singles data if it exists
        if self.check_table_exists("singles_data"):
            self._validate_singles_data(result)

        return result

    def _validate_codes(self, result: ValidationResult):
        """
        Validate code mappings.

        Args:
            result: ValidationResult to add issues to
        """
        codes = self.get_all_rows("codes")

        # Track issues
        missing_codes = 0
        missing_names = 0
        duplicate_codes = {}

        for i, code_entry in enumerate(codes):
            code = code_entry.get("Code", "")
            name = code_entry.get("Name", "")

            if not code:
                missing_codes += 1

            if not name:
                missing_names += 1

            # Track duplicates
            if code:
                if code in duplicate_codes:
                    duplicate_codes[code].append(i)
                else:
                    duplicate_codes[code] = [i]

        # Report issues
        if missing_codes > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_codes} code mapping(s) missing Code value",
                f"Found {missing_codes}/{len(codes)} entries without Code",
                "Re-run BumpEncoder to rebuild code mappings",
                table="codes"
            )

        if missing_names > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_names} code mapping(s) missing Name value",
                f"Found {missing_names}/{len(codes)} entries without Name",
                "Re-run BumpEncoder to rebuild code mappings",
                table="codes"
            )

        # Check for duplicates
        duplicates = {code: indices for code, indices in duplicate_codes.items() if len(indices) > 1}
        if duplicates:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{len(duplicates)} duplicate code(s) found",
                f"Codes with duplicates: {', '.join(list(duplicates.keys())[:5])}",
                "This may cause issues with bump decoding",
                table="codes"
            )

        result.metadata["total_codes"] = len(codes)
        result.metadata["unique_codes"] = len(duplicate_codes)

    def _validate_version_tables(self, result: ValidationResult):
        """
        Validate version-specific multibumps tables.

        Args:
            result: ValidationResult to add issues to
        """
        available_versions = []

        for version in range(10):
            table_name = f"multibumps_v{version}_data"
            if self.check_table_exists(table_name):
                row_count = self.get_row_count(table_name)
                available_versions.append(version)
                result.metadata[f"v{version}_multibumps"] = row_count

                if row_count == 0:
                    self.add_issue(
                        result,
                        ValidationLevel.INFO,
                        f"Version {version} multibumps table is empty",
                        f"Table {table_name} exists but has no data",
                        "This is normal if you don't have v{version} bumps",
                        table=table_name
                    )

        if not available_versions:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                "No version-specific multibumps tables found",
                "Expected at least one multibumps_vX_data table",
                "Check that you have multi-show bumps in your bump library"
            )
        else:
            result.metadata["available_versions"] = available_versions

    def _validate_singles_data(self, result: ValidationResult):
        """
        Validate singles_data table.

        Args:
            result: ValidationResult to add issues to
        """
        if not self.check_table_exists("singles_data"):
            return

        row_count = self.get_row_count("singles_data")
        result.metadata["singles_count"] = row_count

        if row_count == 0:
            self.add_issue(
                result,
                ValidationLevel.INFO,
                "singles_data table is empty",
                "No single-show bumps found",
                "This is unusual but may be valid if you only have multi-show bumps",
                table="singles_data"
            )
        else:
            # Check for Code column
            columns = self.get_column_names("singles_data")
            if "Code" not in columns:
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    "singles_data missing Code column",
                    "The Code column should have been added by BumpEncoder",
                    "Re-run BumpEncoder to rebuild singles_data",
                    table="singles_data"
                )
