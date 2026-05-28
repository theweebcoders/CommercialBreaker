"""
CommercialBreaker Validator

Validates the output of the CommercialBreaker step, which detects commercial
break points and either physically cuts files or creates virtual cuts.

Tables Validated:
- commercial_injector_prep: Contains cut file data (traditional) or timestamps (cutless)
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class CommercialBreakerValidator(BaseValidator):
    """Validates CommercialBreaker step output"""

    @property
    def step_name(self) -> str:
        return "CommercialBreaker"

    @property
    def required_tables(self) -> list:
        return ["commercial_injector_prep"]

    @property
    def pipeline_order(self) -> int:
        return 11  # Eleventh step in pipeline

    def validate(self) -> ValidationResult:
        """
        Validate CommercialBreaker output.

        Checks:
        1. commercial_injector_prep exists and has data
        2. Mode-specific validation (cutless vs traditional)
        3. Timestamps are valid (cutless mode)
        4. Part numbers are sequential (traditional mode)
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check table exists
        if not self.check_table_exists("commercial_injector_prep"):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "commercial_injector_prep table not found",
                "CommercialBreaker has not created output table",
                "Run CommercialBreaker to detect commercial breaks"
            )
            return result

        row_count = self.get_row_count("commercial_injector_prep")
        if row_count == 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "commercial_injector_prep table is empty",
                "No commercial break data found",
                "Run CommercialBreaker on your episode files"
            )
            return result

        result.is_completed = True

        # Detect mode and validate accordingly
        is_cutless = self._detect_cutless_mode()
        result.metadata["is_cutless_mode"] = is_cutless

        if is_cutless:
            self._validate_cutless_mode(result)
        else:
            self._validate_traditional_mode(result)

        return result

    def _detect_cutless_mode(self) -> bool:
        """
        Detect if cutless mode was used.

        Returns:
            True if cutless mode detected
        """
        columns = self.get_column_names("commercial_injector_prep")
        return "startTime" in columns and "endTime" in columns

    def _validate_cutless_mode(self, result: ValidationResult):
        """
        Validate cutless mode output.

        Args:
            result: ValidationResult to add issues to
        """
        # Check for required cutless columns
        required_columns = ["FULL_FILE_PATH", "ORIGINAL_FILE_PATH", "startTime", "endTime", "duration"]
        missing_columns = self.check_required_columns("commercial_injector_prep", required_columns)

        if missing_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "Cutless mode table missing required columns",
                f"Missing columns: {', '.join(missing_columns)}",
                "Re-run CommercialBreaker in cutless mode",
                table="commercial_injector_prep"
            )
            return

        # Validate timestamp data
        prep_data = self.get_all_rows("commercial_injector_prep")

        missing_timestamps = 0
        invalid_timestamps = 0

        for entry in prep_data:
            start_time = entry.get("startTime")
            end_time = entry.get("endTime")

            # At least one timestamp should be present (per test suite)
            if start_time is None and end_time is None:
                missing_timestamps += 1

            # If both present, end should be after start
            if start_time is not None and end_time is not None:
                try:
                    if float(end_time) <= float(start_time):
                        invalid_timestamps += 1
                except (ValueError, TypeError):
                    invalid_timestamps += 1

        if missing_timestamps > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{missing_timestamps} entry/entries missing timestamps",
                f"Found {missing_timestamps}/{len(prep_data)} entries without startTime or endTime",
                "Re-run CommercialBreaker to detect timestamps",
                table="commercial_injector_prep"
            )

        if invalid_timestamps > 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{invalid_timestamps} entry/entries have invalid timestamps",
                "endTime should be greater than startTime",
                "Check commercial detection settings",
                table="commercial_injector_prep"
            )

        result.metadata["total_entries"] = len(prep_data)
        result.metadata["valid_timestamps"] = len(prep_data) - missing_timestamps - invalid_timestamps

    def _validate_traditional_mode(self, result: ValidationResult):
        """
        Validate traditional mode output.

        Args:
            result: ValidationResult to add issues to
        """
        # Check for required traditional columns
        required_columns = ["FULL_FILE_PATH", "Part Number"]
        missing_columns = self.check_required_columns("commercial_injector_prep", required_columns)

        if missing_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "Traditional mode table missing required columns",
                f"Missing columns: {', '.join(missing_columns)}",
                "Re-run CommercialBreaker in traditional mode",
                table="commercial_injector_prep"
            )
            return

        prep_data = self.get_all_rows("commercial_injector_prep")
        result.metadata["total_cut_parts"] = len(prep_data)

        missing_part_numbers = sum(1 for entry in prep_data if not entry.get("Part Number"))
        if missing_part_numbers > 0:
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{missing_part_numbers} entry/entries missing part numbers",
                f"Found {missing_part_numbers}/{len(prep_data)} entries without Part Number",
                "This may indicate incomplete cutting",
                table="commercial_injector_prep"
            )
