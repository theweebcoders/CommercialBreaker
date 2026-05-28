"""
PlexAuthValidator - Validates Step 1: LoginToPlex

Validates Plex authentication for DizqueTV/Tunarr platforms.
This is split from AppDataValidator to track Plex login as a separate step.
Note: This step is CONDITIONAL - only required for DizqueTV and Tunarr, not ComBreakDirect.
"""

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class PlexAuthValidator(BaseValidator):
    """Validates Plex authentication in app_data table"""

    @property
    def step_name(self) -> str:
        return "PlexAuth"

    @property
    def required_tables(self) -> list:
        return []  # Conditional validator

    @property
    def pipeline_order(self) -> int:
        return 1  # Second step in pipeline

    def __init__(self):
        """Initialize PlexAuthValidator"""
        super().__init__()

    def _get_platform(self) -> str:
        """
        Get selected platform from app_data

        Returns:
            Platform name or 'unknown'
        """
        if not self.table_exists('app_data'):
            return 'unknown'

        result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'platform_type'"
        )

        if result is None:
            return 'unknown'

        return result[0]

    def has_completed(self) -> bool:
        """
        Check if Plex authentication is complete

        Returns:
            True if Plex auth complete (or not needed), False otherwise
        """
        platform = self._get_platform()

        # ComBreakDirect doesn't need Plex
        if platform == 'combreakdirect':
            return True

        # DizqueTV/Tunarr need Plex auth
        if not self.table_exists('app_data'):
            return False

        # Check for plex_token and plex_url
        token_result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'plex_token'"
        )
        url_result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'plex_url'"
        )

        if token_result is None or url_result is None:
            return False

        token = token_result[0]
        url = url_result[0]

        # Both must be non-empty
        return bool(token and len(token) > 0 and url and len(url) > 0)

    def validate(self) -> ValidationResult:
        """
        Validate Plex authentication

        Returns:
            ValidationResult with validation findings
        """
        result = self.create_result()

        platform = self._get_platform()

        # Check if Plex auth is needed for this platform
        if platform == 'combreakdirect':
            result.is_completed = True  # Not required for this platform
            self.add_info(
                result,
                "Plex authentication not required for ComBreakDirect"
            )
            result.metadata['plex_required'] = False
            return result

        if platform == 'unknown':
            self.add_issue(
                result,
                ValidationLevel.WARNING,
                "Platform not selected",
                "Cannot determine if Plex auth is required",
                "Select platform first"
            )
            return result

        # Platform requires Plex (dizquetv or tunarr)
        result.metadata['plex_required'] = True

        # Check app_data exists
        if not self.table_exists('app_data'):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "app_data table missing",
                "Plex configuration not initialized",
                "Run LoginToPlex to authenticate"
            )
            return result

        # Check for plex_token
        token_result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'plex_token'"
        )

        if token_result is None:
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "Plex token missing",
                "No 'plex_token' key in app_data",
                "Run LoginToPlex to authenticate with Plex"
            )
        else:
            token = token_result[0]
            if not token or len(token) == 0:
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    "Plex token is empty",
                    "Token exists but has no value",
                    "Re-run LoginToPlex to re-authenticate"
                )
            else:
                self.add_info(result, "Plex token found")
                result.metadata['has_token'] = True

        # Check for plex_url
        url_result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'plex_url'"
        )

        if url_result is None:
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "Plex URL missing",
                "No 'plex_url' key in app_data",
                "Run LoginToPlex to select Plex server"
            )
        else:
            url = url_result[0]
            if not url or len(url) == 0:
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    "Plex URL is empty",
                    "URL exists but has no value",
                    "Re-run LoginToPlex to select server"
                )
            else:
                self.add_info(result, f"Plex URL configured: {url}")
                result.metadata['has_url'] = True
                result.metadata['plex_url'] = url

        # Optional: Check for client_identifier (nice to have)
        client_id_result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = 'client_identifier'"
        )

        if client_id_result is None:
            self.add_info(result, "Client identifier not set (optional)")
        else:
            client_id = client_id_result[0]
            if client_id and len(client_id) > 0:
                result.metadata['has_client_id'] = True

        # Mark as completed if both token and URL are present
        if result.metadata.get('has_token') and result.metadata.get('has_url'):
            result.is_completed = True

        return result
