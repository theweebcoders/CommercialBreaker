"""
PlatformSelectionValidator - Validates Step 0: Platform Selection

Validates that the user has selected a platform (DizqueTV, Tunarr, or ComBreakDirect).
This is split from AppDataValidator to track platform selection as a separate step.
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class PlatformSelectionValidator(BaseValidator):
    """Validates platform selection in app_data table"""

    @property
    def step_name(self) -> str:
        return "PlatformSelection"

    @property
    def required_tables(self) -> list:
        return ["app_data"]

    @property
    def pipeline_order(self) -> int:
        return 0  # First step in pipeline

    def __init__(self):
        """Initialize PlatformSelectionValidator"""
        super().__init__()

    def has_completed(self) -> bool:
        """
        Check if platform selection is complete

        Returns:
            True if platform selected, False otherwise
        """
        if not self.table_exists('app_data'):
            return False

        # Check for platform_type key (actual key used in database)
        result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'platform_type'"
        )

        if result is None:
            return False

        platform = result[0]
        return platform in ['dizquetv', 'tunarr', 'combreakdirect']

    def validate(self) -> ValidationResult:
        """
        Validate platform selection

        Returns:
            ValidationResult with validation findings
        """
        result = self.create_result()

        # Check app_data table exists
        if not self.table_exists('app_data'):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "app_data table missing",
                "Platform configuration not initialized",
                "Run platform selection in UI"
            )
            return result

        # Check for platform_type key (actual key used in database)
        platform_result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'platform_type'"
        )

        if platform_result is None:
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "Platform not selected",
                "No 'platform_type' key in app_data",
                "Select platform (DizqueTV, Tunarr, or ComBreakDirect) in UI"
            )
            return result

        platform = platform_result[0]

        # Validate platform value
        valid_platforms = ['dizquetv', 'tunarr', 'combreakdirect']
        if platform not in valid_platforms:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Invalid platform: {platform}",
                f"Platform must be one of: {', '.join(valid_platforms)}",
                "Select a valid platform in UI"
            )
            return result

        # Success - platform is selected
        result.is_completed = True
        self.add_info(result, f"Platform selected: {platform}")

        # Store in metadata
        result.metadata['platform'] = platform

        return result
