"""
BumpCalculatorValidator - Validates Step 16a: BumpCalculator

Validates bump_durations table creation for ComBreakDirect cutless runs.

BumpCalculator measures every bump file with ffprobe so ComBreakDirect can
derive exact cutless playback timing. Other platforms never run this step,
so the validator becomes a no-op unless platform_type == ComBreakDirect.
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel
from API.validators.utils import (
    MIN_BUMP_DURATION_MS,
    MAX_BUMP_DURATION_MS,
    TYPICAL_BUMP_MIN_MS,
    TYPICAL_BUMP_MAX_MS
)


class BumpCalculatorValidator(BaseValidator):
    """Validates bump_durations table (ComBreakDirect cutless mode only)"""

    @property
    def step_name(self) -> str:
        return "BumpCalculator"

    @property
    def required_tables(self) -> list:
        return []  # Conditional - only required in cutless mode

    @property
    def pipeline_order(self) -> int:
        return 16  # Step 16a in pipeline (before CutlessFinalizer)

    def __init__(self):
        """Initialize BumpCalculatorValidator"""
        super().__init__()

    def has_completed(self) -> bool:
        """
        Check if bump durations have been calculated

        Returns:
            True if completed (or not required), False otherwise
        """
        metadata = self.get_processing_metadata()

        # Only ComBreakDirect needs bump durations
        if metadata['platform'] != 'combreakdirect':
            return True

        # ComBreakDirect always runs in cutless mode, but guard anyway
        if metadata['mode'] != 'cutless':
            return True

        # Cutless mode - check for table
        if not self.table_exists('bump_durations'):
            return False

        # Check has data
        result = self.db_manager.fetchone(
            "SELECT COUNT(*) FROM bump_durations"
        )

        if result is None:
            return False

        return result[0] > 0

    def validate(self) -> ValidationResult:
        """
        Validate bump duration calculations

        Returns:
            ValidationResult with validation findings
        """
        result = self.create_result()

        metadata = self.get_processing_metadata()
        platform = metadata['platform']
        result.metadata['platform'] = platform

        if platform != 'combreakdirect':
            result.is_completed = True
            self.add_info(
                result,
                "BumpCalculator not required for platform "
                f"'{platform or 'unknown'}'"
            )
            return result

        mode = metadata['mode']
        result.metadata['mode'] = mode

        # Traditional mode - not required
        if mode != 'cutless':
            result.is_completed = True  # Not required in traditional mode
            self.add_info(
                result,
                "Traditional mode: bump durations are ignored"
            )
            return result

        # Cutless mode - REQUIRED
        if not self.table_exists('bump_durations'):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "bump_durations table missing",
                "Cutless mode requires bump durations for CutlessFinalizer",
                "Run BumpCalculator to measure bump file durations"
            )
            return result

        # Check for data
        rows = self.fetchall_as_dicts("SELECT * FROM bump_durations")

        if len(rows) == 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "bump_durations is empty",
                "No bump durations calculated",
                "Check BumpCalculator ran successfully on bump files"
            )
            return result

        # Validate schema
        first_row = rows[0]
        required_cols = ['FULL_FILE_PATH', 'duration']
        missing_cols = [col for col in required_cols if col not in first_row]

        if missing_cols:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "bump_durations schema incomplete",
                f"Missing columns: {', '.join(missing_cols)}",
                "Table schema is invalid"
            )
            return result

        # Check for invalid durations
        self._validate_bump_duration_ranges(result, rows)

        # Mark as completed if table exists with data
        result.is_completed = True

        return result

    def _validate_bump_duration_ranges(self, result: ValidationResult, rows: list):
        """
        Validate bump durations are within reasonable ranges.

        NOTE: Durations in database are stored in milliseconds.

        Checks:
        1. All durations > 0 (ERROR)
        2. No NULL durations (ERROR)
        3. Durations within absolute bounds (1s to 5min) (WARNING)
        4. Durations within typical range (5s to 60s) (INFO)

        Args:
            result: ValidationResult to add issues to
            rows: List of bump duration entries
        """
        zero_or_negative = []
        null_durations = []
        out_of_absolute_range = []
        out_of_typical_range = []

        for row in rows:
            duration_ms = row.get('duration')
            path = row.get('FULL_FILE_PATH', 'unknown')

            # Check for NULL durations
            if duration_ms is None:
                null_durations.append({'path': path, 'duration_ms': None})
                continue

            # Check for zero or negative durations
            if duration_ms <= 0:
                zero_or_negative.append({'path': path, 'duration_ms': duration_ms})
                continue

            # Check absolute bounds (1s to 300s = 1000ms to 300000ms)
            if duration_ms < MIN_BUMP_DURATION_MS or duration_ms > MAX_BUMP_DURATION_MS:
                out_of_absolute_range.append({
                    'path': path,
                    'duration_ms': duration_ms,
                    'duration_sec': duration_ms / 1000.0,
                    'expected_range': f'{MIN_BUMP_DURATION_MS / 1000:.0f}s-{MAX_BUMP_DURATION_MS / 1000:.0f}s'
                })

            # Check typical range (5s to 60s = 5000ms to 60000ms) - informational only
            elif duration_ms < TYPICAL_BUMP_MIN_MS or duration_ms > TYPICAL_BUMP_MAX_MS:
                out_of_typical_range.append({
                    'path': path,
                    'duration_ms': duration_ms,
                    'duration_sec': duration_ms / 1000.0,
                    'typical_range': f'{TYPICAL_BUMP_MIN_MS / 1000:.0f}s-{TYPICAL_BUMP_MAX_MS / 1000:.0f}s'
                })

        # Report NULL durations (ERROR)
        if null_durations:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{len(null_durations)} bump(s) have NULL durations",
                f"Sample: {null_durations[0]['path']}",
                "BumpCalculator failed to measure these bump files. Re-run BumpCalculator.",
                table="bump_durations"
            )
            result.is_valid = False

        # Report zero/negative durations (ERROR)
        if zero_or_negative:
            first = zero_or_negative[0]
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"{len(zero_or_negative)} bump(s) with zero or negative duration",
                f"Bumps must have positive duration. Sample: {first['path']} = {first['duration_ms']}ms",
                "Check ffprobe can access these files. Re-run BumpCalculator.",
                table="bump_durations"
            )
            result.is_valid = False

        # Report out of absolute range (WARNING)
        if out_of_absolute_range:
            first = out_of_absolute_range[0]
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                f"{len(out_of_absolute_range)} bump(s) with unusual duration",
                f"Duration outside typical bounds ({first['expected_range']}). Sample: {first['path']} = {first['duration_sec']:.1f}s",
                "Verify these files are actually bumps and not full episodes. Very short (<1s) or very long (>5min) durations are suspicious.",
                table="bump_durations"
            )

        # Report out of typical range (INFO only - for awareness)
        if out_of_typical_range:
            first = out_of_typical_range[0]
            self.add_issue(
                result,
                ValidationLevel.INFO,
                f"{len(out_of_typical_range)} bump(s) outside typical duration range",
                f"Most Toonami bumps are {first['typical_range']}. Sample: {first['path']} = {first['duration_sec']:.1f}s",
                "This may be normal for special bumps or intros. Just informational.",
                table="bump_durations"
            )

        # Calculate valid count
        valid_count = len(rows) - len(null_durations) - len(zero_or_negative)

        # Success summary
        if valid_count > 0:
            self.add_info(
                result,
                f"Calculated durations for {valid_count}/{len(rows)} bumps"
            )

        # Store metadata
        result.metadata['total_bumps'] = len(rows)
        result.metadata['valid_durations'] = valid_count
        result.metadata['null_durations'] = len(null_durations)
        result.metadata['zero_or_negative_durations'] = len(zero_or_negative)
        result.metadata['out_of_absolute_range'] = len(out_of_absolute_range)
        result.metadata['out_of_typical_range'] = len(out_of_typical_range)
