"""
CommercialInjectorPrepValidator - Validates Step 12: CommercialInjectorPrep

Validates commercial_injector_prep table creation.

IMPORTANT: This table is created by DIFFERENT tools depending on mode:
- Traditional Mode: CommercialInjectorPrep tool scans cut files
- Cutless Mode: VirtualCut creates this table (CommercialInjectorPrep is SKIPPED)

Schema differs by mode:
- Traditional: Has 'Part Number', no timestamps
- Cutless: Has 'startTime', 'endTime', 'ORIGINAL_FILE_PATH', 'duration'
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class CommercialInjectorPrepValidator(BaseValidator):
    """Validates commercial_injector_prep table (traditional or cutless)"""

    @property
    def step_name(self) -> str:
        return "CommercialInjectorPrep"

    @property
    def required_tables(self) -> list:
        return ["commercial_injector_prep"]

    @property
    def pipeline_order(self) -> int:
        return 12  # Step 12 in pipeline

    def __init__(self):
        """Initialize CommercialInjectorPrepValidator"""
        super().__init__()

    def _detect_mode_from_table(self) -> str:
        """
        Detect mode from commercial_injector_prep schema

        Returns:
            'cutless', 'traditional', or 'unknown'
        """
        if not self.table_exists('commercial_injector_prep'):
            return 'unknown'

        # Get first row to check schema
        rows = self.fetchall_as_dicts("SELECT * FROM commercial_injector_prep LIMIT 1")

        if not rows:
            return 'unknown'

        first_row = rows[0]

        # Cutless mode has startTime, endTime, ORIGINAL_FILE_PATH
        if 'startTime' in first_row and 'ORIGINAL_FILE_PATH' in first_row:
            return 'cutless'

        # Traditional mode has Part Number without timestamps
        if 'Part Number' in first_row and 'startTime' not in first_row:
            return 'traditional'

        return 'unknown'

    def _get_mode(self) -> str:
        """
        Infer operating mode from database state.

        Preference order:
        1. Schema inspection of commercial_injector_prep
        2. app_data.cutless_mode_used flag
        3. Cutless table heuristics
        4. Default to traditional
        """
        detected_mode = self._detect_mode_from_table()
        if detected_mode != 'unknown':
            return detected_mode

        if self.table_exists('app_data'):
            result = self.db_manager.fetchone(
                "SELECT value FROM app_data WHERE key = 'cutless_mode_used'"
            )
            if result and str(result[0]).lower() == 'true':
                return 'cutless'

        if self.is_cutless_mode():
            return 'cutless'

        return 'traditional'

    def has_completed(self) -> bool:
        """
        Check if commercial_injector_prep table exists

        Returns:
            True if table exists with data, False otherwise
        """
        if not self.table_exists('commercial_injector_prep'):
            return False

        # Check has rows
        result = self.db_manager.fetchone(
            "SELECT COUNT(*) FROM commercial_injector_prep"
        )

        if result is None:
            return False

        return result[0] > 0

    def validate(self) -> ValidationResult:
        """
        Validate commercial_injector_prep table

        Returns:
            ValidationResult with validation findings
        """
        result = self.create_result()

        mode_hint = self._get_mode()
        result.metadata['mode_hint'] = mode_hint

        # Check if table exists
        if not self.table_exists('commercial_injector_prep'):
            if mode_hint == 'cutless':
                self.add_issue(
                    result,
                    ValidationLevel.CRITICAL,
                    "commercial_injector_prep table missing",
                    "Cutless mode: VirtualCut should create this table",
                    "Run CommercialBreaker with cutless mode enabled"
                )
            else:
                self.add_issue(
                    result,
                    ValidationLevel.CRITICAL,
                    "commercial_injector_prep table missing",
                    "Traditional mode: CommercialInjectorPrep should create this table",
                    "Run CommercialInjectorPrep to organize cut files"
                )
            return result

        # Table exists - check for data
        rows = self.fetchall_as_dicts("SELECT * FROM commercial_injector_prep")

        if len(rows) == 0:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "commercial_injector_prep is empty",
                "No cut file entries organized",
                "Check CommercialBreaker/CommercialInjectorPrep output"
            )
            return result

        # Detect mode from schema
        detected_mode = self._detect_mode_from_table()
        result.metadata['detected_mode'] = detected_mode

        # Use schema detection when available; fallback to hints otherwise
        mode = detected_mode if detected_mode != 'unknown' else mode_hint
        result.metadata['mode'] = mode

        # Validate schema matches expected mode
        first_row = rows[0]

        if mode == 'cutless':
            # Validate cutless schema
            required_cutless_cols = ['startTime', 'endTime', 'ORIGINAL_FILE_PATH', 'duration']
            missing_cols = [col for col in required_cutless_cols if col not in first_row]

            if missing_cols:
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    f"Cutless schema incomplete",
                    f"Missing columns: {', '.join(missing_cols)}",
                    "VirtualCut did not create proper cutless schema"
                )
            else:
                self.add_info(result, f"Cutless mode: {len(rows)} virtual cuts validated")
                result.metadata['has_cutless_schema'] = True

                # Check for NULL timestamps
                # Note: Bumps should have NULL timestamps (only duration populated)
                # Anime episodes should have at least startTime OR endTime
                # Having one NULL is valid (first part has NULL start, last part has NULL end)
                null_timestamps = []
                for r in rows:
                    if r.get('startTime') is None and r.get('endTime') is None:
                        # Check if this is anime or bump
                        path = r.get('FULL_FILE_PATH', '')
                        if self.is_anime(path):
                            null_timestamps.append(r)

                if len(null_timestamps) > 0:
                    self.add_issue(
                        result,
                        ValidationLevel.ERROR,
                        f"{len(null_timestamps)} anime episode(s) missing timestamps",
                        f"Table: commercial_injector_prep | Found {len(null_timestamps)}/{len(rows)} anime entries with NULL startTime AND endTime",
                        "Check VirtualCut timestamp calculation for cutless mode"
                    )

        else:  # traditional mode
            # Validate traditional schema
            if 'Part Number' not in first_row:
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    "Traditional schema incomplete",
                    "Missing 'Part Number' column",
                    "CommercialInjectorPrep did not create proper schema"
                )
            else:
                self.add_info(result, f"Traditional mode: {len(rows)} cut file entries validated")
                result.metadata['has_traditional_schema'] = True

            # Warn if cutless columns present (mode mismatch)
            if 'startTime' in first_row or 'endTime' in first_row:
                self.add_issue(
                    result,
                    ValidationLevel.WARNING,
                    "Found cutless columns in traditional mode",
                    "Table has startTime/endTime (cutless schema)",
                    "Mode mismatch - check config.cutless_mode setting"
                )

        # General validation - check for required columns
        required_cols = ['SHOW_NAME_1', 'Season and Episode', 'FULL_FILE_PATH']
        missing = [col for col in required_cols if col not in first_row]

        if missing:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Missing required columns",
                f"Columns: {', '.join(missing)}",
                "Table schema is invalid"
            )
        else:
            # Mark as completed if table exists with valid data and schema
            result.is_completed = True

        return result
