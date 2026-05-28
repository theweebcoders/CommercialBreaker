"""
UncutEncoder Validator

Validates the output of the UncutEncoder step, which identifies uncut files
and assigns them BLOCK_IDs to keep related content together.

Tables Validated:
- uncut_encoded_data: Uncut episodes with BLOCK_ID assignments
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class UncutEncoderValidator(BaseValidator):
    """Validates UncutEncoder step output"""

    @property
    def step_name(self) -> str:
        return "UncutEncoder"

    @property
    def required_tables(self) -> list:
        return ["uncut_encoded_data"]

    @property
    def pipeline_order(self) -> int:
        return 6  # Sixth step in pipeline

    def validate(self) -> ValidationResult:
        """
        Validate UncutEncoder output.

        Checks:
        1. uncut_encoded_data exists and has data
        2. BLOCK_ID column is present and populated
        3. File paths are valid
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check table structure
        if not self.validate_table_structure(
            result,
            "uncut_encoded_data",
            required_columns=["FULL_FILE_PATH", "BLOCK_ID"],
            min_rows=1
        ):
            return result

        result.is_completed = True

        # Validate data quality
        self._validate_uncut_data(result)

        return result

    def _validate_uncut_data(self, result: ValidationResult):
        """
        Validate uncut data quality.

        Args:
            result: ValidationResult to add issues to
        """
        uncut_data = self.get_all_rows("uncut_encoded_data")

        missing_paths = 0
        missing_block_ids = 0
        missing_block_id_files = []
        missing_block_id_multibumps = 0
        missing_block_id_specials = 0

        for entry in uncut_data:
            file_path = entry.get("FULL_FILE_PATH", "")

            if not file_path:
                missing_paths += 1

            if not entry.get("BLOCK_ID"):
                missing_block_ids += 1

                # Check if this is a multi-bump (which legitimately doesn't have BLOCK_ID)
                # Multi-bumps typically have "Next" or "Later" in their names
                if "next" in file_path.lower() or "later" in file_path.lower():
                    missing_block_id_multibumps += 1
                # Check if this is a S00 episode (special/OVA/movie - expected to not have BLOCK_ID)
                elif " - S00E" in file_path or " - s00e" in file_path.lower():
                    missing_block_id_specials += 1
                else:
                    # Track up to 5 examples of non-multibump/non-special files missing BLOCK_ID
                    if len(missing_block_id_files) < 5:
                        missing_block_id_files.append(file_path.split('/')[-1])  # Just filename

        if missing_paths > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_paths} entry/entries missing file path",
                f"Found {missing_paths}/{len(uncut_data)} entries without FULL_FILE_PATH",
                "Re-run UncutEncoder to rebuild table",
                table="uncut_encoded_data"
            )

        # Multi-bumps and S00 specials are expected to not have BLOCK_IDs - only report actual problems
        actual_missing = missing_block_ids - missing_block_id_multibumps - missing_block_id_specials

        if actual_missing > 0:
            example_text = f"Examples: {', '.join(missing_block_id_files[:3])}" if missing_block_id_files else ""
            exclusions = f"excluding {missing_block_id_multibumps} multi-bumps, {missing_block_id_specials} S00 specials"
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{actual_missing} entry/entries missing BLOCK_ID ({exclusions})",
                f"Found {actual_missing} entries without BLOCK_ID that aren't multi-bumps or S00 specials. {example_text}",
                "Re-run UncutEncoder to assign BLOCK_IDs",
                table="uncut_encoded_data"
            )
        # Don't report multi-bumps or S00 specials without BLOCK_IDs - that's expected behavior

        result.metadata["total_uncut_entries"] = len(uncut_data)
        result.metadata["unique_block_ids"] = len(set(e.get("BLOCK_ID") for e in uncut_data if e.get("BLOCK_ID")))
        result.metadata["multibumps_without_block_id"] = missing_block_id_multibumps
        result.metadata["specials_without_block_id"] = missing_block_id_specials
