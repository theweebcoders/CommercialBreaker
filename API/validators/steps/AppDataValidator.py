"""
AppDataValidator

Validates the app_data table which stores platform configuration and folder paths.
This is Step 0 in the pipeline - it must complete before any content processing.

Tables Validated:
- app_data: Platform type, URLs, folder paths, Plex configuration

Validation checks:
- Required configuration keys exist and are valid
- Folder paths are accessible
- Platform-specific requirements (Plex auth for dizquetv/tunarr)
- Platform compatibility (cutless mode requires custom DizqueTV)
"""

import os
from typing import Optional

from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class AppDataValidator(BaseValidator):
    """Validates platform configuration and folder setup"""

    @property
    def step_name(self) -> str:
        return "Platform/Folder Setup"

    @property
    def required_tables(self) -> list:
        return ["app_data"]

    @property
    def pipeline_order(self) -> int:
        return 0  # First step in pipeline

    def validate(self) -> ValidationResult:
        """
        Validate app_data configuration.

        Checks:
        1. app_data table exists with required keys
        2. Platform configuration is valid
        3. Folder paths are accessible
        4. Plex configuration (if required by platform)
        5. Platform compatibility (cutless mode support)
        """
        result = self.create_result(is_completed=False, is_valid=True)

        # Check table exists
        if not self.check_table_exists("app_data"):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "app_data table not found",
                "Platform configuration has not been initialized",
                "Complete platform setup in Page 2 (Platform Selection)",
                table="app_data"
            )
            return result

        result.is_completed = True

        # Validate configuration keys
        self._validate_platform_config(result)
        self._validate_folder_paths(result)
        self._validate_plex_config(result)
        self._validate_platform_compatibility(result)

        return result

    def _get_config_value(self, key: str) -> Optional[str]:
        """
        Get a configuration value from app_data.

        Args:
            key: Configuration key to retrieve

        Returns:
            Configuration value or None if not found
        """
        row = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = ?",
            (key,)
        )
        if row:
            return row['value'] if hasattr(row, 'keys') else row[0]
        return None

    def _validate_platform_config(self, result: ValidationResult):
        """
        Validate platform-related configuration.

        Args:
            result: ValidationResult to add issues to
        """
        # Platform type is critical
        platform_type = self._get_config_value("platform_type")

        if not platform_type:
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                "Platform type not configured",
                "platform_type key is missing or empty",
                "Select your platform (DizqueTV/Tunarr/ComBreakDirect) in Page 2",
                table="app_data"
            )
            return

        # Validate platform type is valid
        valid_platforms = ["dizquetv", "tunarr", "combreakdirect"]
        if platform_type.lower() not in valid_platforms:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Invalid platform type: {platform_type}",
                f"Must be one of: {', '.join(valid_platforms)}",
                "Re-select platform in Page 2",
                table="app_data"
            )

        # Platform URL should be set
        platform_url = self._get_config_value("platform_url")
        if not platform_url or platform_url.startswith("eg. "):
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "Platform URL not configured",
                f"platform_url is missing or contains example value: {platform_url}",
                f"Enter your {platform_type} URL in Page 2",
                table="app_data"
            )

        result.metadata["platform_type"] = platform_type
        result.metadata["platform_url"] = platform_url

    def _validate_folder_paths(self, result: ValidationResult):
        """
        Validate folder paths are configured and accessible.

        Args:
            result: ValidationResult to add issues to
        """
        # Required folder keys
        folder_keys = {
            "anime_folder": "Anime library folder",
            "bump_folder": "Toonami bumps folder",
            "working_folder": "Working/output folder"
        }

        # Check each folder
        for key, description in folder_keys.items():
            value = self._get_config_value(key)

            # Check if configured
            if not value or value.startswith("eg. "):
                self.add_issue(
                    result,
                    ValidationLevel.CRITICAL,
                    f"{description} not configured",
                    f"{key} is missing or contains example value",
                    f"Configure {description} path in Page 3",
                    table="app_data"
                )
                continue

            # Check if path exists (skip for Docker env vars or if running in test mode)
            if not value.startswith("$") and not os.path.exists(value):
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    f"{description} path does not exist",
                    f"Path: {value}",
                    f"Create the folder or update path in Page 3",
                    table="app_data"
                )

            result.metadata[key] = value

        # Optional: special_bump_folder
        special_bump = self._get_config_value("special_bump_folder")
        if special_bump:
            result.metadata["special_bump_folder"] = special_bump

    def _validate_plex_config(self, result: ValidationResult):
        """
        Validate Plex configuration for platforms that require it.

        Args:
            result: ValidationResult to add issues to
        """
        platform_type = self._get_config_value("platform_type")

        # Only dizquetv and tunarr need Plex
        if platform_type and platform_type.lower() in ["dizquetv", "tunarr"]:
            required_keys = {
                "plex_url": "Plex server URL",
                "plex_token": "Plex authentication token",
                "selected_anime_library": "Plex anime library",
                "selected_toonami_library": "Plex Toonami library"
            }

            for key, description in required_keys.items():
                value = self._get_config_value(key)

                if not value or value.startswith("eg. "):
                    self.add_issue(
                        result,
                        ValidationLevel.CRITICAL,
                        f"{description} not configured",
                        f"{key} is missing (required for {platform_type})",
                        "Complete Plex authentication in Page 3",
                        table="app_data"
                    )
                else:
                    result.metadata[key] = value

    def _validate_platform_compatibility(self, result: ValidationResult):
        """
        Validate platform compatibility settings.

        Args:
            result: ValidationResult to add issues to
        """
        platform_type = self._get_config_value("platform_type")
        cutless_used = self._get_config_value("cutless_mode_used")

        # If cutless mode is enabled, platform must support it
        if cutless_used and cutless_used.lower() == "true":
            # DizqueTV (custom fork) and ComBreakDirect support cutless mode
            # Tunarr does NOT support cutless mode
            cutless_compatible = platform_type and platform_type.lower() in ["dizquetv", "combreakdirect"]
            if not cutless_compatible:
                self.add_issue(
                    result,
                    ValidationLevel.CRITICAL,
                    f"Platform {platform_type} does not support cutless mode",
                    "Only DizqueTV (custom fork) and ComBreakDirect support cutless mode",
                    "Switch to DizqueTV/ComBreakDirect or disable cutless mode",
                    table="app_data"
                )

            result.metadata["cutless_mode"] = True
        else:
            result.metadata["cutless_mode"] = False
