"""
Validation Result Data Structures

Defines the data structures used throughout the validation system to represent
validation results, issues, and status information.

Following the coding philosophy: these structures provide the five components of
good errors (where, what, why, details, and how to fix).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class ValidationLevel(Enum):
    """Severity levels for validation issues"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __str__(self):
        return self.value

    def to_symbol(self):
        """Get a visual symbol for the validation level"""
        symbols = {
            ValidationLevel.INFO: "ℹ",
            ValidationLevel.WARNING: "⚠",
            ValidationLevel.ERROR: "✗",
            ValidationLevel.CRITICAL: "⊗"
        }
        return symbols.get(self, "?")


@dataclass
class ValidationIssue:
    """
    Represents a single validation issue found during database validation.

    Follows the five components of good errors:
    1. Where: step, table, row_index
    2. What: message (user-friendly)
    3. Why: details (technical explanation)
    4. How to fix: suggestion (actionable)
    5. When: timestamp
    """
    level: ValidationLevel
    step: str
    message: str
    details: str
    suggestion: str
    table: Optional[str] = None
    row_index: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'level': self.level.value,
            'step': self.step,
            'message': self.message,
            'details': self.details,
            'suggestion': self.suggestion,
            'table': self.table,
            'row_index': self.row_index,
            'timestamp': self.timestamp.isoformat()
        }

    def __str__(self):
        """Human-readable string representation"""
        location = f"[{self.step}"
        if self.table:
            location += f" → {self.table}"
        if self.row_index is not None:
            location += f" row {self.row_index}"
        location += "]"

        return f"{self.level.to_symbol()} {self.level.value} {location}: {self.message}"


@dataclass
class ValidationResult:
    """
    Result of validating a single pipeline step.

    Contains:
    - step_name: Which pipeline step was validated
    - is_valid: Overall pass/fail status
    - is_completed: Whether this step has been run at all
    - issues: List of all validation issues found
    - metadata: Additional information (row counts, timing, etc.)
    """
    step_name: str
    is_valid: bool
    is_completed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue):
        """Add a validation issue to this result"""
        self.issues.append(issue)

        # Update is_valid if we have ERROR or CRITICAL issues
        if issue.level in [ValidationLevel.ERROR, ValidationLevel.CRITICAL]:
            self.is_valid = False

    def get_issues_by_level(self, level: ValidationLevel) -> List[ValidationIssue]:
        """Get all issues of a specific severity level"""
        return [issue for issue in self.issues if issue.level == level]

    def get_issue_counts(self) -> Dict[str, int]:
        """Get counts of issues by severity level"""
        return {
            'critical': len(self.get_issues_by_level(ValidationLevel.CRITICAL)),
            'error': len(self.get_issues_by_level(ValidationLevel.ERROR)),
            'warning': len(self.get_issues_by_level(ValidationLevel.WARNING)),
            'info': len(self.get_issues_by_level(ValidationLevel.INFO))
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'step_name': self.step_name,
            'is_valid': self.is_valid,
            'is_completed': self.is_completed,
            'issues': [issue.to_dict() for issue in self.issues],
            'metadata': self.metadata,
            'issue_counts': self.get_issue_counts()
        }

    def get_status_symbol(self) -> str:
        """Get a visual symbol for the overall status"""
        if not self.is_completed:
            return "○"  # Not run
        elif not self.is_valid:
            return "✗"  # Failed
        elif any(issue.level == ValidationLevel.WARNING for issue in self.issues):
            return "⚠"  # Warning
        else:
            return "✓"  # Success

    def get_status_description(self) -> str:
        """Get a human-readable status description"""
        if not self.is_completed:
            return "Not completed"
        elif not self.is_valid:
            counts = self.get_issue_counts()
            critical = counts['critical']
            error = counts['error']
            if critical > 0:
                return f"Failed: {critical} critical issue(s)"
            else:
                return f"Failed: {error} error(s)"
        elif any(issue.level == ValidationLevel.WARNING for issue in self.issues):
            count = len(self.get_issues_by_level(ValidationLevel.WARNING))
            return f"Completed with {count} warning(s)"
        else:
            return "Completed successfully"

    def __str__(self):
        """Human-readable string representation"""
        status = self.get_status_symbol()
        desc = self.get_status_description()
        return f"{status} {self.step_name}: {desc}"


@dataclass
class PipelineStatus:
    """
    Overall status of the entire Toonami Tools pipeline.

    Provides a high-level view of which steps have been completed
    and what the current state of the pipeline is.
    """
    completed_steps: List[str] = field(default_factory=list)
    current_step: Optional[str] = None
    is_cutless_mode: bool = False
    total_steps: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def completion_percentage(self) -> float:
        """Calculate percentage of pipeline completed"""
        if self.total_steps == 0:
            return 0.0
        return (len(self.completed_steps) / self.total_steps) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'completed_steps': self.completed_steps,
            'current_step': self.current_step,
            'is_cutless_mode': self.is_cutless_mode,
            'total_steps': self.total_steps,
            'completion_percentage': self.completion_percentage(),
            'metadata': self.metadata
        }

    def __str__(self):
        """Human-readable string representation"""
        pct = self.completion_percentage()
        mode = "Cutless" if self.is_cutless_mode else "Traditional"
        return f"Pipeline: {len(self.completed_steps)}/{self.total_steps} steps ({pct:.1f}%) | Mode: {mode}"
