"""
FolderMakerValidator - Validates Step 2: FolderMaker

Validates that working directories have been created.
Checks for existence and write permissions of:
- <working_dir>/cut/
- <working_dir>/toonami_filtered/
"""

import os
from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel


class FolderMakerValidator(BaseValidator):
    """Validates working folder creation"""

    @property
    def step_name(self) -> str:
        return "FolderMaker"

    @property
    def required_tables(self) -> list:
        return []  # No database tables, just folders

    @property
    def pipeline_order(self) -> int:
        return 2  # Third step in pipeline

    def __init__(self):
        """Initialize FolderMakerValidator"""
        super().__init__()

    def _get_working_dir(self) -> str:
        """
        Get working directory from config or app_data

        Returns:
            Working directory path
        """
        try:
            import config
            if hasattr(config, 'working_dir'):
                return config.working_dir
        except ImportError:
            pass

        # Try to get from app_data
        if self.table_exists('app_data'):
            result = self.db_manager.fetchone(
                "SELECT value FROM app_data WHERE key = 'working_dir'"
            )
            if result:
                return result[0]

        # Fallback to default
        return '/app/working'

    def has_completed(self) -> bool:
        """
        Check if folders have been created

        For databases created elsewhere (e.g., Docker), we infer completion
        from later pipeline steps rather than checking filesystem.

        Returns:
            True if folders exist OR pipeline has progressed past this step
        """
        # If later steps completed, folders must have been created
        # Check for ToonamiChecker completion (step 3)
        if self.table_exists('Toonami_Episodes') or self.table_exists('toonami_episodes'):
            return True

        # Otherwise check filesystem
        working_dir = self._get_working_dir()

        cut_folder = os.path.join(working_dir, 'cut')
        filtered_folder = os.path.join(working_dir, 'toonami_filtered')

        return os.path.exists(cut_folder) and os.path.exists(filtered_folder)

    def validate(self) -> ValidationResult:
        """
        Validate working folder creation

        Returns:
            ValidationResult with validation findings
        """
        result = self.create_result()

        # Check if later steps completed (database created in Docker, etc.)
        if self.table_exists('Toonami_Episodes') or self.table_exists('toonami_episodes'):
            result.is_completed = True
            self.add_info(result, "Folders verified via downstream table existence")
            result.metadata['inferred_from_downstream'] = True
            return result

        working_dir = self._get_working_dir()
        cut_folder = os.path.join(working_dir, 'cut')
        filtered_folder = os.path.join(working_dir, 'toonami_filtered')

        result.metadata['working_dir'] = working_dir

        # Note: Parent working directory validation is handled by AppDataValidator
        # This validator only checks subdirectories created by FolderMaker

        # If parent doesn't exist, we can't check subdirectories
        if not os.path.exists(working_dir):
            # Don't report this - AppDataValidator handles parent directory validation
            # Just mark as not completed if we haven't inferred from downstream
            if not result.is_completed:
                return result

        # Check cut folder
        if not os.path.exists(cut_folder):
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "cut folder missing",
                f"Expected: {cut_folder}",
                "Run FolderMaker to create working directories"
            )
        else:
            # Check if writable
            if not os.access(cut_folder, os.W_OK):
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    "cut folder not writable",
                    f"Path: {cut_folder}",
                    "Check folder permissions (chmod +w)"
                )
            else:
                self.add_info(result, f"cut folder OK: {cut_folder}")
                result.metadata['has_cut_folder'] = True

        # Check toonami_filtered folder
        if not os.path.exists(filtered_folder):
            self.add_issue(
                result,
                ValidationLevel.ERROR,
                "toonami_filtered folder missing",
                f"Expected: {filtered_folder}",
                "Run FolderMaker to create working directories"
            )
        else:
            # Check if writable
            if not os.access(filtered_folder, os.W_OK):
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    "toonami_filtered folder not writable",
                    f"Path: {filtered_folder}",
                    "Check folder permissions (chmod +w)"
                )
            else:
                self.add_info(result, f"toonami_filtered folder OK: {filtered_folder}")
                result.metadata['has_filtered_folder'] = True

        # Mark as completed if both folders exist and are writable
        if result.metadata.get('has_cut_folder') and result.metadata.get('has_filtered_folder'):
            result.is_completed = True

        return result
