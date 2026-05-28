"""
Base Validator Abstract Class

Provides common validation utilities and defines the interface that all
step-specific validators must implement.

Following the coding philosophy:
- Validate everything, trust nothing
- Use DatabaseManager for all database operations
- Use ErrorManager for consistent error reporting
- Single responsibility: each validator handles one pipeline step
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import re

from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
from API.validators.ValidationResult import (
    ValidationResult,
    ValidationIssue,
    ValidationLevel
)


class BaseValidator(ABC):
    """
    Abstract base class for all step validators.

    Provides common utilities and enforces a consistent interface
    for validating individual pipeline steps.
    """

    def __init__(self):
        """Initialize with DatabaseManager and ErrorManager"""
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        self._processing_metadata = None

    @property
    @abstractmethod
    def step_name(self) -> str:
        """
        Human-readable name of the pipeline step being validated.

        Example: "ToonamiChecker", "LineupPrep", "BumpEncoder"
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def required_tables(self) -> List[str]:
        """
        List of database tables that MUST exist for this step to be considered complete.

        Example: ["Toonami_Episodes", "Toonami_Shows"]
        """
        raise NotImplementedError

    @property
    def optional_tables(self) -> List[str]:
        """
        List of database tables that MAY exist for this step (mode-dependent or optional features).

        Default: empty list
        """
        return []

    @property
    def pipeline_order(self) -> int:
        """
        Position in the pipeline (1-20). Used for ordering validation results.

        Default: 999 (end of pipeline)
        """
        return 999

    @abstractmethod
    def validate(self) -> ValidationResult:
        """
        Run validation for this pipeline step.

        Returns:
            ValidationResult containing overall status, issues, and metadata
        """
        raise NotImplementedError

    def has_completed(self) -> bool:
        """
        Check if this pipeline step has completed (tables exist with data).

        This is used for quick completion detection in get_pipeline_status().
        Default implementation checks if all required_tables exist and have rows.

        Validators with dynamic table detection (empty required_tables) should
        override this method to implement custom completion logic.

        Returns:
            bool: True if step has completed, False otherwise
        """
        # Default implementation: check required_tables
        if not self.required_tables:
            # Validators with no required_tables should override this method
            # Returning False here prevents the all([]) == True bug
            return False

        # Check that all required tables exist and have data
        for table in self.required_tables:
            if not self.check_table_exists(table):
                return False
            if self.get_row_count(table) == 0:
                return False

        return True

    # ==================== Common Validation Utilities ====================

    def create_result(self, is_completed: bool = False, is_valid: bool = True) -> ValidationResult:
        """
        Create a ValidationResult for this step with default values.

        Args:
            is_completed: Whether this step has been run
            is_valid: Whether the step's output is valid

        Returns:
            ValidationResult initialized for this step
        """
        return ValidationResult(
            step_name=self.step_name,
            is_completed=is_completed,
            is_valid=is_valid
        )

    def add_issue(
        self,
        result: ValidationResult,
        level: ValidationLevel,
        message: str,
        details: str,
        suggestion: str,
        table: Optional[str] = None,
        row_index: Optional[int] = None
    ):
        """
        Add a validation issue to a result.

        Args:
            result: ValidationResult to add issue to
            level: Severity level
            message: User-friendly description
            details: Technical details
            suggestion: Actionable fix suggestion
            table: Optional table name
            row_index: Optional row number
        """
        issue = ValidationIssue(
            level=level,
            step=self.step_name,
            message=message,
            details=details,
            suggestion=suggestion,
            table=table,
            row_index=row_index
        )
        result.add_issue(issue)

    def add_info(self, result: ValidationResult, message: str):
        """
        Add an informational message to validation result.

        Args:
            result: ValidationResult to add info to
            message: Informational message
        """
        self.add_issue(
            result,
            ValidationLevel.INFO,
            message,
            "",
            ""
        )

    def check_table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        return self.db_manager.table_exists(table_name)

    def table_exists(self, table_name: str) -> bool:
        """
        Alias for check_table_exists for convenience.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        return self.check_table_exists(table_name)

    def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of rows, or 0 if table doesn't exist
        """
        if not self.check_table_exists(table_name):
            return 0

        try:
            result = self.db_manager.fetchone(
                f"SELECT COUNT(*) as count FROM {table_name}"
            )
            return result['count'] if result else 0
        except Exception:
            return 0

    def get_column_names(self, table_name: str) -> List[str]:
        """
        Get list of column names for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column names, or empty list if table doesn't exist
        """
        if not self.check_table_exists(table_name):
            return []

        try:
            result = self.db_manager.fetchall(f"PRAGMA table_info({table_name})")
            return [row['name'] for row in result]
        except Exception:
            return []

    def check_required_columns(
        self,
        table_name: str,
        required_columns: List[str]
    ) -> List[str]:
        """
        Check if all required columns exist in a table.

        Args:
            table_name: Name of the table
            required_columns: List of required column names

        Returns:
            List of missing column names (empty if all present)
        """
        actual_columns = self.get_column_names(table_name)
        return [col for col in required_columns if col not in actual_columns]

    def get_all_rows(self, table_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all rows from a table as dictionaries.

        Args:
            table_name: Name of the table
            limit: Optional limit on number of rows to fetch

        Returns:
            List of rows as dictionaries
        """
        if not self.check_table_exists(table_name):
            return []

        try:
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            return self.db_manager.fetchall_as_dicts(query)
        except Exception:
            return []

    def fetchall_as_dicts(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a query and return results as dictionaries.

        Args:
            query: SQL query to execute

        Returns:
            List of rows as dictionaries
        """
        try:
            return self.db_manager.fetchall_as_dicts(query)
        except Exception:
            return []

    def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """
        Execute a query and return first result as dictionary.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            First row as dictionary, or None if no results
        """
        try:
            if params:
                return self.db_manager.fetchone(query, params)
            else:
                return self.db_manager.fetchone(query)
        except Exception:
            return None

    def fetchall(self, query: str, params: Optional[tuple] = None) -> List:
        """
        Execute a query and return all results.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            List of rows
        """
        try:
            if params:
                return self.db_manager.fetchall(query, params)
            else:
                return self.db_manager.fetchall(query)
        except Exception:
            return []

    def validate_episode_pattern(self, text: str) -> bool:
        """
        Check if text contains valid episode pattern (SxxExx).

        NOTE: This method only checks for episode pattern presence.
        For bump vs anime detection, use is_anime() or is_bump() instead,
        which use the same logic as main processing tools.

        Args:
            text: Text to check for episode pattern

        Returns:
            True if valid episode pattern found
        """
        pattern = r'S\d{2}E\d{2}'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def is_bump(self, file_path: str) -> bool:
        """
        Check if file path represents a bump (not anime).

        Uses same detection logic as main processing tools (EpisodeFilter, LineupPrep, Plex).
        This ensures validators are consistent with the rest of the codebase.

        Args:
            file_path: Full file path to check

        Returns:
            True if bump, False if anime
        """
        from API.validators.utils.helpers import is_bump
        return is_bump(file_path)

    def is_anime(self, file_path: str) -> bool:
        """
        Check if file path represents anime episode (not a bump).

        Uses same detection logic as main processing tools (EpisodeFilter, LineupPrep, Plex).
        This ensures validators are consistent with the rest of the codebase.

        Args:
            file_path: Full file path to check

        Returns:
            True if anime, False if bump
        """
        from API.validators.utils.helpers import is_anime
        return is_anime(file_path)

    def extract_episode_info(self, text: str) -> Optional[Dict[str, str]]:
        """
        Extract season and episode numbers from text.

        Args:
            text: Text containing episode pattern

        Returns:
            Dict with 'season' and 'episode' keys, or None if not found
        """
        pattern = r'S(\d{2})E(\d{2})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {
                'season': match.group(1),
                'episode': match.group(2)
            }
        return None

    def count_anime_episodes(self, table_name: str, column: str = "FULL_FILE_PATH") -> int:
        """
        Count rows containing anime episodes (with SxxExx pattern).

        Args:
            table_name: Name of the table
            column: Column to check for episode pattern

        Returns:
            Number of anime episodes found
        """
        rows = self.get_all_rows(table_name)
        count = 0
        for row in rows:
            value = row.get(column, "")
            if value and self.validate_episode_pattern(str(value)):
                count += 1
        return count

    def validate_table_structure(
        self,
        result: ValidationResult,
        table_name: str,
        required_columns: List[str],
        min_rows: int = 1
    ) -> bool:
        """
        Common validation pattern: check table exists, has required columns, and minimum rows.

        Args:
            result: ValidationResult to add issues to
            table_name: Table to validate
            required_columns: Columns that must exist
            min_rows: Minimum number of rows required

        Returns:
            True if all checks pass, False otherwise
        """
        # Check table exists
        if not self.check_table_exists(table_name):
            self.add_issue(
                result,
                ValidationLevel.CRITICAL,
                f"Table '{table_name}' does not exist",
                f"The {self.step_name} step has not created this required table",
                f"Run {self.step_name} to create this table",
                table=table_name
            )
            return False

        # Check row count
        row_count = self.get_row_count(table_name)
        if row_count < min_rows:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Table '{table_name}' has insufficient data",
                f"Expected at least {min_rows} row(s), found {row_count}",
                f"Re-run {self.step_name} to populate this table",
                table=table_name
            )
            return False

        # Check required columns
        missing_columns = self.check_required_columns(table_name, required_columns)
        if missing_columns:
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                f"Table '{table_name}' is missing required columns",
                f"Missing columns: {', '.join(missing_columns)}",
                f"Re-run {self.step_name} to rebuild the table with correct schema",
                table=table_name
            )
            return False

        # All checks passed
        result.metadata[f"{table_name}_row_count"] = row_count
        return True

    def is_cutless_mode(self) -> bool:
        """
        Detect if the database is using cutless mode.

        Returns:
            True if cutless mode detected, False otherwise
        """
        # Check for cutless-specific tables
        cutless_tables = [
            "lineup_v2_cutless",
            "lineup_v3_cutless",
            "lineup_v8_cutless",
            "lineup_v9_cutless",
            "bump_durations"
        ]

        for table in cutless_tables:
            if self.check_table_exists(table):
                return True

        # Check for timing columns in commercial_injector_prep
        if self.check_table_exists("commercial_injector_prep"):
            columns = self.get_column_names("commercial_injector_prep")
            if "startTime" in columns and "endTime" in columns:
                return True

        return False

    def get_processing_metadata(self) -> Dict[str, Any]:
        """
        Get cached processing metadata (platform, mode, flags).

        Returns:
            Dict with keys:
                - platform (lowercase string or 'unknown')
                - is_cutless (bool)
                - mode ('cutless' or 'traditional')
                - requires_bump_calculator (bool)
        """
        if self._processing_metadata is not None:
            return self._processing_metadata

        platform = 'unknown'
        cutless_flag = False

        if self.table_exists('app_data'):
            row = self.db_manager.fetchone(
                "SELECT value FROM app_data WHERE key = 'platform_type'"
            )
            if row and row[0]:
                platform = str(row[0]).lower()

            cutless_row = self.db_manager.fetchone(
                "SELECT value FROM app_data WHERE key = 'cutless_mode_used'"
            )
            if cutless_row and str(cutless_row[0]).lower() == 'true':
                cutless_flag = True

        is_cutless = cutless_flag or self.is_cutless_mode()
        mode = 'cutless' if is_cutless else 'traditional'
        requires_bump_calculator = is_cutless and platform == 'combreakdirect'

        self._processing_metadata = {
            'platform': platform,
            'is_cutless': is_cutless,
            'mode': mode,
            'requires_bump_calculator': requires_bump_calculator
        }
        return self._processing_metadata

    def get_available_versions(self) -> List[int]:
        """
        Get list of Toonami versions that have data in the database.

        Returns:
            List of version numbers (e.g., [2, 3, 8, 9])
        """
        versions = []
        for version in range(10):  # Check versions 0-9
            # Check if any version-specific table exists
            if (self.check_table_exists(f"lineup_v{version}") or
                self.check_table_exists(f"multibumps_v{version}_data")):
                versions.append(version)
        return versions
