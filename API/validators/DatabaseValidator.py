"""
Database Validator - Main Orchestrator

Coordinates all step validators and provides the main entry point for database validation.
This is the single source of truth for validation operations.

Following the coding philosophy:
- Centralized orchestration (like FrontEndLogic)
- Status broadcasting for user transparency
- Error reporting through ErrorManager
- Thread-safe database operations through DatabaseManager
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from collections import defaultdict
import re

from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager, ErrorLevel
from API.validators.ValidationResult import (
    ValidationResult,
    ValidationIssue,
    ValidationLevel,
    PipelineStatus
)


class DatabaseValidator:
    """
    Main orchestrator for database validation.

    Coordinates all step validators and provides high-level validation operations.
    """

    def __init__(self, status_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the database validator.

        Args:
            status_callback: Optional callback function for status updates
        """
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
        self.status_callback = status_callback

        # Validators will be initialized when StepValidators package is complete
        self.validators = []
        self._initialize_validators()

    def _initialize_validators(self):
        """
        Initialize all step validators.

        This method dynamically imports and instantiates all validators
        from the steps/ and integrity/ packages.
        """
        # Import validators here to avoid circular dependencies
        try:
            # Phase 0: Platform Setup validators
            from API.validators.steps.PlatformSelectionValidator import PlatformSelectionValidator
            from API.validators.steps.PlexAuthValidator import PlexAuthValidator
            from API.validators.steps.FolderMakerValidator import FolderMakerValidator
            from API.validators.steps.AppDataValidator import AppDataValidator

            # Phase 1-4: Step Validators
            from API.validators.steps.ToonamiCheckerValidator import ToonamiCheckerValidator
            from API.validators.steps.LineupPrepValidator import LineupPrepValidator
            from API.validators.steps.BumpEncoderValidator import BumpEncoderValidator
            from API.validators.steps.UncutEncoderValidator import UncutEncoderValidator
            from API.validators.steps.MultilineupValidator import MultilineupValidator
            from API.validators.steps.MergerValidator import MergerValidator
            from API.validators.steps.EpisodeFilterValidator import EpisodeFilterValidator
            from API.validators.steps.CommercialBreakerValidator import CommercialBreakerValidator
            from API.validators.steps.CommercialInjectorPrepValidator import CommercialInjectorPrepValidator
            from API.validators.steps.CommercialInjectorValidator import CommercialInjectorValidator
            from API.validators.steps.BlockMakerValidator import BlockMakerValidator
            from API.validators.steps.PostCutBumpFilterValidator import PostCutBumpFilterValidator
            from API.validators.steps.BumpCalculatorValidator import BumpCalculatorValidator
            from API.validators.steps.CutlessFinalizerValidator import CutlessFinalizerValidator

            # Cross-cutting: Integrity validators
            from API.validators.integrity.LineupIntegrityValidator import LineupIntegrityValidator
            from API.validators.integrity.ReferentialIntegrityValidator import ReferentialIntegrityValidator

            # Instantiate validators in pipeline order
            self.validators = [
                # Phase 0: Platform Setup
                PlatformSelectionValidator(),  # Step 0
                PlexAuthValidator(),  # Step 1
                FolderMakerValidator(),  # Step 2

                # Phase 1: Content Discovery
                ToonamiCheckerValidator(),  # Step 3

                # Phase 2: Prepare Uncut Content
                LineupPrepValidator(),  # Step 4
                BumpEncoderValidator(),  # Step 5
                UncutEncoderValidator(),  # Step 6
                MultilineupValidator(),  # Step 7 (first run)
                MergerValidator(),  # Step 8 (uncut + cut runs)
                EpisodeFilterValidator(),  # Step 9

                # Phase 3: Commercial Detection
                CommercialBreakerValidator(),  # Step 11

                # Phase 4: Prepare Cut Anime
                CommercialInjectorPrepValidator(),  # Step 12
                CommercialInjectorValidator(),  # Step 13
                BlockMakerValidator(),  # Step 14
                PostCutBumpFilterValidator(),  # Step 14a
                BumpCalculatorValidator(),  # Step 16a (cutless)
                CutlessFinalizerValidator(),  # Step 16 (cutless)

                # Cross-cutting validators
                LineupIntegrityValidator(),
                ReferentialIntegrityValidator(),

                # Keep AppDataValidator for folder validation
                AppDataValidator()
            ]

            # Sort by pipeline order
            self.validators.sort(key=lambda v: v.pipeline_order)

        except ImportError as e:
            # Validators not yet implemented, start with empty list
            self.validators = []
            if self.status_callback:
                self.status_callback(f"Warning: Some validators not yet available: {e}")

    def _broadcast_status(self, message: str):
        """
        Broadcast a status message.

        Args:
            message: Status message to broadcast
        """
        if self.status_callback:
            self.status_callback(message)

    def run_full_validation(self) -> Dict[str, Any]:
        """
        Run comprehensive validation of the entire database.

        Returns:
            Dictionary containing:
                - results: List of ValidationResult objects
                - issues: Flat list of all ValidationIssue objects
                - summary: Summary statistics
                - pipeline_status: PipelineStatus object
        """
        self._broadcast_status("Starting database validation...")

        all_results = []
        all_issues = []

        # Run each validator
        for i, validator in enumerate(self.validators, 1):
            self._broadcast_status(
                f"Validating {validator.step_name} ({i}/{len(self.validators)})..."
            )

            try:
                result = validator.validate()
                all_results.append(result)

                # Filter issues:
                # - Keep all WARNING, ERROR, CRITICAL
                # - Keep useful INFO (duplicate episodes, etc.)
                # - Filter noise INFO (platform selection, tokens, etc.)
                actionable_issues = []
                for issue in result.issues:
                    if issue.level != ValidationLevel.INFO:
                        # Keep all non-INFO issues
                        actionable_issues.append(issue)
                    elif self._is_useful_info(issue):
                        # Keep useful INFO messages
                        actionable_issues.append(issue)
                    # Otherwise skip noise INFO

                all_issues.extend(actionable_issues)

                # Report only actionable issues to ErrorManager
                for issue in actionable_issues:
                    self._report_issue_to_error_manager(issue)

            except Exception as e:
                # If a validator crashes, create an error result
                self.error_manager.send_critical(
                    source="DatabaseValidator",
                    operation=f"validate_{validator.step_name}",
                    message=f"Validator crashed: {validator.step_name}",
                    details=str(e),
                    suggestion="Check validator implementation for bugs"
                )

                # Create error result
                error_result = ValidationResult(
                    step_name=validator.step_name,
                    is_completed=False,
                    is_valid=False
                )
                error_result.add_issue(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    step=validator.step_name,
                    message="Validation failed due to internal error",
                    details=str(e),
                    suggestion="Report this issue to the developers"
                ))
                all_results.append(error_result)
                all_issues.extend(error_result.issues)

        # Consolidate issues by validator
        consolidated_issues = self._consolidate_issues(all_issues)

        # Generate summary
        summary = self._generate_summary(all_results, consolidated_issues)
        pipeline_status = self.get_pipeline_status()

        self._broadcast_status(f"Validation complete: {summary['summary_text']}")

        # Convert issues to dicts for JSON serialization
        issues_dict = [issue.to_dict() for issue in consolidated_issues]

        return {
            "results": all_results,
            "issues": issues_dict,
            "summary": summary,
            "pipeline_status": pipeline_status,
            "timestamp": datetime.now().isoformat()
        }

    def _is_useful_info(self, issue: ValidationIssue) -> bool:
        """
        Determine if an INFO-level issue contains useful information.

        Args:
            issue: ValidationIssue to check

        Returns:
            True if this INFO message should be shown to the user, False if it's noise
        """
        # Useful INFO patterns
        useful_patterns = [
            "repeated in lineup",  # Duplicate episode detection
            "repeated",  # General repetition info
        ]

        message_lower = issue.message.lower()
        return any(pattern in message_lower for pattern in useful_patterns)

    def _report_issue_to_error_manager(self, issue: ValidationIssue):
        """
        Report a validation issue to the ErrorManager.

        Args:
            issue: ValidationIssue to report
        """
        # Map ValidationLevel to ErrorLevel
        level_map = {
            ValidationLevel.INFO: ErrorLevel.INFO,
            ValidationLevel.WARNING: ErrorLevel.WARNING,
            ValidationLevel.ERROR: ErrorLevel.ERROR,
            ValidationLevel.CRITICAL: ErrorLevel.CRITICAL
        }

        error_level = level_map.get(issue.level, ErrorLevel.ERROR)

        self.error_manager.send_error(
            level=error_level,
            source="DatabaseValidator",
            operation=issue.step,
            message=issue.message,
            details=issue.details,
            suggestion=issue.suggestion
        )

    def _consolidate_issues(self, issues: List[ValidationIssue]) -> List[ValidationIssue]:
        """
        Consolidate multiple issues from the same validator into grouped issues.

        Args:
            issues: List of ValidationIssue objects

        Returns:
            List of consolidated ValidationIssue objects
        """
        if not issues:
            return []

        # Group issues by (step_name, level)
        grouped = defaultdict(list)
        for issue in issues:
            key = (issue.step, issue.level)
            grouped[key].append(issue)

        # Consolidate groups
        consolidated = []
        for (step, level), step_issues in grouped.items():
            if len(step_issues) == 1:
                # Single issue - keep as-is
                consolidated.append(step_issues[0])
            else:
                # Multiple issues - consolidate
                consolidated_issue = self._create_consolidated_issue(step, level, step_issues)
                consolidated.append(consolidated_issue)

        # Sort by level (CRITICAL → ERROR → WARNING → INFO), then by step
        level_order = {
            ValidationLevel.CRITICAL: 0,
            ValidationLevel.ERROR: 1,
            ValidationLevel.WARNING: 2,
            ValidationLevel.INFO: 3
        }
        consolidated.sort(key=lambda i: (level_order.get(i.level, 999), i.step))

        return consolidated

    def _create_consolidated_issue(
        self,
        step: str,
        level: ValidationLevel,
        issues: List[ValidationIssue]
    ) -> ValidationIssue:
        """
        Create a single consolidated issue from multiple issues.

        Args:
            step: Step name
            level: Validation level
            issues: List of issues to consolidate

        Returns:
            Consolidated ValidationIssue
        """
        # Check if these are version-based errors (CutlessFinalizer pattern)
        if self._are_version_errors(issues):
            return self._consolidate_version_errors(step, level, issues)

        # Check if these are similar list items (folders, files, etc.)
        if self._are_list_items(issues):
            return self._consolidate_list_items(step, level, issues)

        # Default: create numbered list
        return self._consolidate_generic(step, level, issues)

    def _are_version_errors(self, issues: List[ValidationIssue]) -> bool:
        """Check if issues are version-based (e.g., Version 3: ...)."""
        version_pattern = re.compile(r'Version \d+:')
        return all(version_pattern.search(issue.message) for issue in issues)

    def _are_list_items(self, issues: List[ValidationIssue]) -> bool:
        """Check if issues are simple list items (similar structure)."""
        # If all messages are short and similar in structure, treat as list
        if len(issues) < 2:
            return False

        # Check for common patterns: "X not found", "X missing", "X does not exist"
        common_patterns = [
            r'does not exist',
            r'missing',
            r'not found',
            r'not configured'
        ]

        for pattern in common_patterns:
            if all(re.search(pattern, issue.message, re.IGNORECASE) for issue in issues):
                return True

        return False

    def _consolidate_version_errors(
        self,
        step: str,
        level: ValidationLevel,
        issues: List[ValidationIssue]
    ) -> ValidationIssue:
        """Consolidate version-based errors (CutlessFinalizer)."""
        # Extract version information and preserve details
        by_version = defaultdict(list)
        version_details = {}

        for issue in issues:
            match = re.search(r'Version (\d+):', issue.message)
            if match:
                version = match.group(1)
                # Extract the error type (after "Version X: ")
                error_type = re.sub(r'Version \d+:\s*', '', issue.message)
                by_version[version].append(error_type)

                # Preserve the actual details (BLOCK_IDs, etc.)
                if issue.details:
                    if version not in version_details:
                        version_details[version] = []
                    version_details[version].append(issue.details)

        # Format consolidated message with preserved details
        version_summaries = []
        for version in sorted(by_version.keys()):
            errors = by_version[version]
            version_summaries.append(f"Version {version}: {', '.join(errors)}")

            # Add the detailed BLOCK_ID information
            if version in version_details:
                for detail in version_details[version]:
                    version_summaries.append(f"{detail}")

        consolidated_details = "\n\n".join(version_summaries)

        # Get unique suggestions, consolidating similar ones
        suggestions = [i.suggestion for i in issues if i.suggestion]
        if not suggestions:
            suggestion = ""
        elif len(suggestions) == 1:
            suggestion = suggestions[0]
        else:
            # Deduplicate and consolidate similar suggestions
            unique_suggestions = []
            seen_prefixes = set()
            for sug in suggestions:
                # Check if this suggestion starts with something we've seen
                # (e.g., "Re-run CutlessFinalizer to X" and "Re-run CutlessFinalizer to Y")
                prefix = sug.split(' to ')[0] if ' to ' in sug else sug[:30]
                if prefix not in seen_prefixes:
                    unique_suggestions.append(sug)
                    seen_prefixes.add(prefix)

            suggestion = unique_suggestions[0] if len(unique_suggestions) == 1 else " | ".join(unique_suggestions)

        return ValidationIssue(
            level=level,
            step=step,
            message=f"{len(by_version)} version(s) with validation issues",
            details=consolidated_details,
            suggestion=suggestion
        )

    def _consolidate_list_items(
        self,
        step: str,
        level: ValidationLevel,
        issues: List[ValidationIssue]
    ) -> ValidationIssue:
        """Consolidate list-style errors (missing folders, files, etc.)."""
        # Create bullet list
        bullets = []
        for issue in issues:
            if issue.details:
                bullets.append(f"• {issue.message}: {issue.details}")
            else:
                bullets.append(f"• {issue.message}")

        consolidated_details = "\n".join(bullets)

        # Determine consolidated message
        # Extract common theme from first issue
        first_msg = issues[0].message.lower()
        if 'folder' in first_msg or 'directory' in first_msg:
            theme = "folder/directory"
        elif 'file' in first_msg:
            theme = "file"
        elif 'path' in first_msg:
            theme = "path"
        else:
            theme = "issue"

        # Get unique suggestions
        unique_suggestions = list(dict.fromkeys(i.suggestion for i in issues if i.suggestion))
        suggestion = unique_suggestions[0] if len(unique_suggestions) == 1 else " | ".join(unique_suggestions)

        return ValidationIssue(
            level=level,
            step=step,
            message=f"{len(issues)} {theme} issue(s) detected",
            details=consolidated_details,
            suggestion=suggestion
        )

    def _consolidate_generic(
        self,
        step: str,
        level: ValidationLevel,
        issues: List[ValidationIssue]
    ) -> ValidationIssue:
        """Generic consolidation - numbered list."""
        # Create numbered list
        items = []
        for i, issue in enumerate(issues, 1):
            if issue.details:
                items.append(f"{i}. {issue.message}\n   Details: {issue.details}")
            else:
                items.append(f"{i}. {issue.message}")

        consolidated_details = "\n".join(items)

        # Get unique suggestions
        unique_suggestions = list(dict.fromkeys(i.suggestion for i in issues if i.suggestion))
        suggestion = unique_suggestions[0] if len(unique_suggestions) == 1 else " | ".join(unique_suggestions)

        return ValidationIssue(
            level=level,
            step=step,
            message=f"{len(issues)} issues detected",
            details=consolidated_details,
            suggestion=suggestion
        )

    def _generate_summary(
        self,
        results: List[ValidationResult],
        issues: List[ValidationIssue]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics from validation results.

        Args:
            results: List of ValidationResult objects
            issues: List of all ValidationIssue objects

        Returns:
            Dictionary with summary statistics
        """
        total_steps = len(results)
        completed_steps = sum(1 for r in results if r.is_completed)
        valid_steps = sum(1 for r in results if r.is_completed and r.is_valid)

        # Count issues by severity
        critical_count = sum(1 for i in issues if i.level == ValidationLevel.CRITICAL)
        error_count = sum(1 for i in issues if i.level == ValidationLevel.ERROR)
        warning_count = sum(1 for i in issues if i.level == ValidationLevel.WARNING)
        info_count = sum(1 for i in issues if i.level == ValidationLevel.INFO)

        # Generate summary text
        summary_text = f"{completed_steps}/{total_steps} steps completed, {valid_steps}/{completed_steps} valid"
        if critical_count > 0:
            summary_text += f" | {critical_count} critical"
        if error_count > 0:
            summary_text += f" | {error_count} errors"
        if warning_count > 0:
            summary_text += f" | {warning_count} warnings"

        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "valid_steps": valid_steps,
            "completion_percentage": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "validation_percentage": (valid_steps / total_steps * 100) if total_steps > 0 else 0,
            "critical_count": critical_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "summary_text": summary_text
        }

    def get_pipeline_status(self) -> PipelineStatus:
        """
        Get high-level status of the pipeline without full validation.

        This is a quick check to determine which steps have been completed,
        with phase-aware tracking.

        Returns:
            PipelineStatus object with phase information
        """
        # Refresh schema to see any tables created by other threads
        self.db_manager.refresh_schema()

        completed_steps = []
        current_step = None

        # Check each validator for completion
        for validator in self.validators:
            # Use validator's has_completed() method for accurate detection
            # This fixes the all([]) == True bug for validators with empty required_tables
            if validator.has_completed():
                completed_steps.append(validator.step_name)
            elif not current_step:
                # This is the first incomplete step
                current_step = validator.step_name

        # Detect cutless mode
        is_cutless = self._is_cutless_mode()

        # Determine current step if not set
        if not current_step and len(completed_steps) < len(self.validators):
            # Next step after completed steps
            next_index = len(completed_steps)
            if next_index < len(self.validators):
                current_step = self.validators[next_index].step_name

        # Get phase information
        phase_info = self._get_phase_info(completed_steps)

        # Get version status
        version_status = self._get_version_status()

        return PipelineStatus(
            completed_steps=completed_steps,
            current_step=current_step,
            is_cutless_mode=is_cutless,
            total_steps=len(self.validators),
            metadata={
                "available_versions": self._get_available_versions(),
                "phase_info": phase_info,
                "version_status": version_status
            }
        )

    def _get_row_count(self, table_name: str) -> int:
        """
        Get row count for a table.

        Args:
            table_name: Name of table

        Returns:
            Number of rows, or 0 if table doesn't exist
        """
        if not self.db_manager.table_exists(table_name):
            return 0

        try:
            result = self.db_manager.fetchone(
                f"SELECT COUNT(*) as count FROM {table_name}"
            )
            return result['count'] if result else 0
        except Exception:
            return 0

    def _is_cutless_mode(self) -> bool:
        """
        Detect if database is using cutless mode.

        Returns:
            True if cutless mode detected
        """
        cutless_tables = [
            "lineup_v2_cutless",
            "lineup_v3_cutless",
            "lineup_v8_cutless",
            "lineup_v9_cutless",
            "bump_durations"
        ]

        return any(self.db_manager.table_exists(table) for table in cutless_tables)

    def _get_available_versions(self) -> List[int]:
        """
        Get list of Toonami versions present in database.

        Returns:
            List of version numbers
        """
        versions = []
        for version in range(10):
            if (self.db_manager.table_exists(f"lineup_v{version}") or
                self.db_manager.table_exists(f"multibumps_v{version}_data")):
                versions.append(version)
        return versions

    def validate_specific_step(self, step_name: str) -> Optional[ValidationResult]:
        """
        Validate a specific pipeline step by name.

        Args:
            step_name: Name of the step to validate

        Returns:
            ValidationResult for that step, or None if step not found
        """
        for validator in self.validators:
            if validator.step_name == step_name:
                self._broadcast_status(f"Validating {step_name}...")
                result = validator.validate()
                self._broadcast_status(f"{step_name} validation complete")
                return result

        return None

    def get_step_names(self) -> List[str]:
        """
        Get list of all step names in pipeline order.

        Returns:
            List of step names
        """
        return [validator.step_name for validator in self.validators]

    def _get_phase_info(self, completed_steps: List[str]) -> Dict[str, Any]:
        """
        Get phase-aware information about pipeline progress.

        Args:
            completed_steps: List of completed step names

        Returns:
            Dictionary with phase information
        """
        try:
            from API.validators.PhaseTracker import PhaseTracker

            phase_tracker = PhaseTracker()
            phase_status = phase_tracker.get_current_phase(completed_steps)

            return phase_status

        except ImportError:
            # PhaseTracker not available
            return {
                "status": "unknown",
                "message": "Phase tracking not available"
            }

    def _get_version_status(self) -> Dict[str, List[int]]:
        """
        Get which versions were created in each phase.

        Returns:
            Dictionary mapping phase keys to version lists
        """
        versions = {}

        # Phase 1 versions (uncut lineups from "Prepare Content" phase)
        uncut_versions = []
        for v in [2, 3, 8, 9]:
            if self.db_manager.table_exists(f'lineup_v{v}_uncut'):
                uncut_versions.append(v)
        versions['phase_1_uncut'] = uncut_versions

        # Phase 3 versions (cut lineups from "Prepare Cut Lineup" phase)
        mode = self._is_cutless_mode()
        cut_versions = []

        if mode:
            # Cutless mode - check for _cutless tables
            for v in [2, 3, 8, 9]:
                if self.db_manager.table_exists(f'lineup_v{v}_cutless'):
                    cut_versions.append(v)
        else:
            # Traditional mode - check for lineup_vX (without _uncut or _cutless suffix)
            for v in [2, 3, 8, 9]:
                table = f'lineup_v{v}'
                # Make sure it's not an uncut table
                if (self.db_manager.table_exists(table) and
                    not self.db_manager.table_exists(f'{table}_uncut')):
                    cut_versions.append(v)

        versions['phase_3_cut'] = cut_versions

        return versions

    def detect_processing_mode(self) -> Dict[str, Any]:
        """
        Detect the processing mode and platform from database state.

        Returns:
            Dict with keys:
            - 'mode': 'cutless' or 'traditional'
            - 'platform': 'DizqueTV', 'Tunarr', 'ComBreakDirect', or 'unknown'
            - 'confidence': 'high', 'medium', 'low'
            - 'indicators': List of evidence used for detection
            - 'warnings': List of compatibility warnings
        """
        indicators = []
        warnings = []

        # Detect cutless mode
        is_cutless = self._is_cutless_mode()
        mode = 'cutless' if is_cutless else 'traditional'

        if is_cutless:
            indicators.append("Found cutless-specific tables (lineup_vX_cutless)")

        # Detect platform
        platform = 'unknown'
        confidence = 'low'

        # Check app_data for platform selection
        if self.db_manager.table_exists('app_data'):
            platform_row = self.db_manager.fetchone(
                "SELECT value FROM app_data WHERE key = 'platform_type'"
            )
            if platform_row and platform_row.get('value'):
                platform = platform_row['value']
                confidence = 'high'
                indicators.append(f"Platform explicitly set in app_data: {platform}")

        # Fallback: infer from table existence
        if platform == 'unknown':
            if self.db_manager.table_exists('bump_durations'):
                # ComBreakDirect requires bump_durations
                platform = 'ComBreakDirect'
                confidence = 'medium'
                indicators.append("Found bump_durations table (ComBreakDirect indicator)")
            elif is_cutless:
                # Cutless only works with DizqueTV
                platform = 'DizqueTV'
                confidence = 'medium'
                indicators.append("Cutless mode active (DizqueTV only)")

        # Check for compatibility issues
        compatibility_warnings = self._check_mode_compatibility(mode, platform, is_cutless)
        warnings.extend(compatibility_warnings)

        return {
            'mode': mode,
            'platform': platform,
            'confidence': confidence,
            'indicators': indicators,
            'warnings': warnings
        }

    def _check_mode_compatibility(self, mode: str, platform: str, is_cutless: bool) -> List[str]:
        """
        Check for mode/platform compatibility issues and stale data.

        Args:
            mode: Detected mode ('cutless' or 'traditional')
            platform: Detected platform
            is_cutless: Whether cutless mode is detected

        Returns:
            List of warning messages
        """
        warnings = []

        if mode == 'cutless':
            # Check for stale traditional cut files
            if self.db_manager.table_exists('commercial_injector_prep'):
                columns = [row['name'] for row in self.db_manager.fetchall(
                    "PRAGMA table_info(commercial_injector_prep)"
                )]
                if 'ORIGINAL_FILE_PATH' not in columns:
                    warnings.append(
                        "Stale traditional cut data detected in commercial_injector_prep. "
                        "Re-run Prepare Content in cutless mode to update tables."
                    )

            # Verify platform compatibility
            if platform == 'Tunarr':
                warnings.append(
                    "Platform incompatibility: Cutless mode active but platform is Tunarr (unsupported). "
                    "Cutless mode only works with DizqueTV. Switch platform or disable cutless mode."
                )

        elif mode == 'traditional':
            # Check for stale cutless tables
            cutless_tables = []
            for v in range(10):
                table_name = f"lineup_v{v}_cutless"
                if self.db_manager.table_exists(table_name):
                    cutless_tables.append(table_name)

            if cutless_tables:
                warnings.append(
                    f"Stale cutless tables detected: {', '.join(cutless_tables)}. "
                    "These are from a previous cutless run and can be ignored or deleted."
                )

        return warnings
