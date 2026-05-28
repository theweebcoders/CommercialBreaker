"""
Validators Package

Provides comprehensive database validation and diagnostics for the Toonami Tools pipeline.
This package validates each step of the linear processing pipeline, ensuring data integrity
and providing actionable feedback for troubleshooting.

Main Components:
- DatabaseValidator: Main orchestrator for running all validations
- BaseValidator: Abstract base class for step-specific validators
- ValidationResult: Data structures for validation results and issues

Usage:
    from API.validators import DatabaseValidator

    validator = DatabaseValidator(status_callback=my_callback)
    results = validator.run_full_validation()
    status = validator.get_pipeline_status()
"""

from API.validators.ValidationResult import (
    ValidationLevel,
    ValidationIssue,
    ValidationResult
)
from API.validators.BaseValidator import BaseValidator
from API.validators.DatabaseValidator import DatabaseValidator

__all__ = [
    'ValidationLevel',
    'ValidationIssue',
    'ValidationResult',
    'BaseValidator',
    'DatabaseValidator'
]
