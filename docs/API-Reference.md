# API Reference

This document provides detailed information about the internal APIs used throughout the CommercialBreaker & Toonami Tools system.

## FrontEndLogic Orchestrator API

The `LogicController` class in `API/FrontEndLogic.py` serves as the central orchestrator API for all user interfaces. It provides a unified interface for workflow management, state persistence, and real-time communication via an in-memory message broker.

### Core Architecture

```python
from API import LogicController

# Initialize the orchestrator
logic = LogicController()

# All UIs interact through this single API
logic.login_to_plex()
logic.on_continue_first(anime_lib, toonami_lib, platform_url, platform_type)
```

### Class: LogicController

#### Constructor

```python
def __init__(self):
    """
    Initializes the LogicController with:
    - SQLite database connection for state persistence
    - In-memory message broker for real-time communication
    - Platform compatibility evaluation
    - Channel-based subscriber lists for UI updates
    """
```

### Database Methods

The LogicController uses DatabaseManager for all database operations:

- `_setup_database()` - Initializes the app_data table
- `_set_data(key, value)` - Stores configuration values
- `_get_data(key)` - Retrieves configuration values
- `_check_table_exists(table_name)` - Verifies table existence

**Database Operations**
```python
def _setup_database(self) -> None:
    """Initialize the SQLite database and create necessary tables"""

def _set_data(self, key: str, value: str) -> None:
    """Persist data to SQLite database"""

def _get_data(self, key: str) -> str | None:
    """Retrieve data from SQLite database"""

def _check_table_exists(self, table_name: str) -> bool:
    """Check if a table exists in the database"""
```
All methods use thread-safe DatabaseManager operations internally.

**Common State Keys**:
- `plex_url` - Plex server URL
- `plex_token` - Authentication token
- `selected_anime_library` - Source anime library name
- `selected_toonami_library` - Target Toonami library name
- `platform_type` - "dizquetv", "tunarr", or "combreakdirect"
- `platform_url` - Platform server URL
- `anime_folder` - Local anime directory path
- `bump_folder` - Bump files directory path
- `special_bump_folder` - Special bump files directory path
- `working_folder` - Processing workspace directory
- `cutless_mode_used` - Flag indicating if cutless mode was used for processing
- `docker` - Docker mode flag (from FlagManager)

#### Communication API

**Broadcasting Status Updates**
```python
def _publish_status_update(self, channel: str, message: str) -> None:
    """Publish a message to a channel using the message broker"""

def _broadcast_status_update(self, message: str) -> None:
    """
    Sends real-time status updates to all subscribed UIs
    via the message broker
    """
```

**Subscription Management**
```python
def subscribe_to_status_updates(self, callback: callable) -> None:
    """Register callback for status updates (message broker)"""

def subscribe_to_progress_updates(self, callback: callable) -> None:
    """Register callback for progress updates"""

def subscribe_to_plex_servers(self, callback: callable) -> None:
    """Register callback for Plex server list updates"""

def subscribe_to_plex_libraries(self, callback: callable) -> None:
    """Register callback for Plex library list updates"""

def subscribe_to_filtered_files(self, callback: callable) -> None:
    """Register callback for filtered files updates"""

def subscribe_to_plex_auth_url(self, callback: callable) -> None:
    """Register callback for authentication URL updates"""

def subscribe_to_cutless_state(self, callback: callable) -> None:
    """Register callback for cutless mode state changes"""

def subscribe_to_server_choices(self, callback: callable) -> None:
    """Register callback for Plex server choice notifications"""

def subscribe_to_library_choices(self, callback: callable) -> None:
    """Register callback for Plex library choice notifications"""

def subscribe_to_updates(self, channel: str, callback: callable) -> None:
    """Generic channel-based subscription method for UIs"""

def unsubscribe_from_updates(self, channel: str, callback: callable) -> None:
    """Unsubscribe a callback from a channel"""

**Message Broker Integration**
```python
# In-memory message broker for multi-interface support
def publish_plex_servers(self) -> None:
    """Publishes server list via message broker"""

def publish_plex_auth_url(self, auth_url: str) -> None:
    """Publishes authentication URL via message broker"""

def publish_plex_libraries(self) -> None: 
    """Publishes Plex library list via message broker"""

def publish_filtered_files(self, filtered_files: list) -> None:
    """Publishes the list of filtered files via message broker"""

def publish_cutless_state(self, enabled: bool) -> None:
    """Publishes the cutless mode state ('true' or 'false') via message broker"""
    
```


## ErrorManager API

The `ErrorManager` class in `API/utils/ErrorManager.py` provides a unified way to send error messages throughout the system. It uses the message broker to ensure all UIs receive error messages in a consistent format.

### Getting the ErrorManager

```python
from API.utils.ErrorManager import get_error_manager

class MyModule:
    def __init__(self):
        self.error_manager = get_error_manager()
```

### Error Levels

The system supports four error levels defined in `ErrorLevel`:

- `CRITICAL`: System cannot continue
- `ERROR`: Operation failed but system stable
- `WARNING`: Operation degraded but continuing
- `INFO`: Important non-error information

### Core Methods

```python
def send_error(self, 
              level: str,
              source: str,
              operation: str,
              message: str,
              details: Optional[str] = None,
              suggestion: Optional[str] = None) -> None:
    """
    Send an error message through the message broker.
    
    Args:
        level: Error level (CRITICAL, ERROR, WARNING, INFO)
        source: Component or module generating the error
        operation: Operation that triggered the error
        message: Primary error message
        details: Additional error details (optional)
        suggestion: Suggested resolution (optional)
    """
```

### Convenience Methods

```python
def send_critical(self, source: str, operation: str, message: str, **kwargs) -> None:
    """Send a critical error message"""

def send_error_level(self, source: str, operation: str, message: str, **kwargs) -> None:
    """Send an error level message"""

def send_warning(self, source: str, operation: str, message: str, **kwargs) -> None:
    """Send a warning message"""

def send_info(self, source: str, operation: str, message: str, **kwargs) -> None:
    """Send an info message"""
```

### Error Message Structure

```python
{
    "level": "ERROR",
    "source": "MyTool",
    "operation": "process_file",
    "message": "File not found",
    "details": "The specified file does not exist",
    "suggestion": "Check the file path",
    "timestamp": "2024-03-14T10:30:45"
}
```

### FrontEndLogic Integration

The LogicController provides methods for handling error messages:

```python
def subscribe_to_error_messages(self, callback: callable) -> None:
    """
    Subscribe to error messages from any component.
    
    Args:
        callback: Function to call with error data when an error occurs
    """
```

### Thread Safety

- ErrorManager is thread-safe through MessageBroker
- Can be used from any thread
- No additional synchronization needed

### Rate Limiting

FrontEndLogic automatically rate limits repeated errors:
- 5-second cooldown between identical errors
- Prevents error message spam
- Based on source, operation, and message

### Critical Error Handling

When a critical error occurs:
1. Current operation is stopped
2. Operation queue is cleared
3. UI state is reset
4. System returns to ready state


#### Error Management API

**Error History Methods**
```python
def get_error_history(self, level_filter: Optional[str] = None,
                     source_filter: Optional[str] = None,
                     limit: Optional[int] = None) -> list:
    """Get error history with optional filtering"""

def get_recent_errors(self, count: int = 10) -> list:
    """Get the most recent N errors"""

def get_errors_by_level(self, level: str) -> list:
    """Get all errors of a specific level (CRITICAL, ERROR, WARNING, INFO)"""

def get_critical_errors(self) -> list:
    """Get all critical errors"""

def clear_error_history(self) -> None:
    """Clear the entire error history"""

def get_error_summary(self) -> dict:
    """Get a summary of errors by level"""
```

**Error Subscription Methods**
```python
def subscribe_to_error_messages(self, callback: callable) -> None:
    """Subscribe to error messages. Callback receives (error_data dict)"""

def clear_error_messages(self) -> None:
    """Clear all error messages from all UIs"""
```

---

## S.A.R.A. Validation System API

The S.A.R.A. (System Analysis and Reporting Assistant) validation system provides comprehensive database validation and diagnostics. Located in `/API/validators/`, it consists of a main orchestrator (`DatabaseValidator`), base validator class (`BaseValidator`), 20 specialized validators, and supporting data structures.

**Complete Documentation**: See [S.A.R.A. Validation System](S.A.R.A-Validation-System.md) for full technical details, architecture diagrams, and usage examples.

### DatabaseValidator Class

**Location**: `/API/validators/DatabaseValidator.py`

Main orchestrator for all validation operations.

#### Initialization

```python
from API.validators.DatabaseValidator import DatabaseValidator

# Create validator with status callback
def status_update(message: str):
    print(f"[VALIDATION] {message}")

validator = DatabaseValidator(status_callback=status_update)

# Or without callback
validator = DatabaseValidator()
```

#### Core Methods

```python
def run_full_validation(self) -> Dict[str, Any]:
    """
    Run comprehensive validation of the entire database.

    Executes all 20 validators in pipeline order, consolidates issues,
    generates summary statistics, and broadcasts status updates.

    Returns:
        Dictionary containing:
            - results: List of ValidationResult objects
            - issues: Flat list of consolidated ValidationIssue dicts
            - summary: Summary statistics
            - pipeline_status: PipelineStatus object
            - timestamp: ISO format timestamp

    Example:
        >>> validator = DatabaseValidator(status_callback=print)
        >>> results = validator.run_full_validation()
        >>> print(results['summary']['summary_text'])
        "18/20 steps completed, 16/18 valid | 2 errors | 3 warnings"
        >>> for issue in results['issues']:
        ...     if issue['level'] == 'CRITICAL':
        ...         print(f"{issue['step']}: {issue['message']}")
    """

def get_pipeline_status(self) -> PipelineStatus:
    """
    Get high-level status of the pipeline without full validation.

    Quick check to determine which steps have been completed.
    Uses each validator's has_completed() method for accurate detection.

    Returns:
        PipelineStatus object with:
            - completed_steps: List[str] of completed step names
            - current_step: Optional[str] next incomplete step
            - is_cutless_mode: bool for cutless mode detection
            - total_steps: int total number of validators
            - metadata: Dict with phase info, versions, etc.

    Example:
        >>> status = validator.get_pipeline_status()
        >>> print(f"Pipeline: {status.completion_percentage():.1f}% complete")
        >>> print(f"Mode: {'Cutless' if status.is_cutless_mode else 'Traditional'}")
        >>> print(f"Phase: {status.metadata['phase_info']['current_phase_name']}")
    """

def validate_specific_step(self, step_name: str) -> Optional[ValidationResult]:
    """
    Validate a specific pipeline step by name.

    Args:
        step_name: Name of the step (e.g., "ToonamiChecker", "CommercialBreaker")

    Returns:
        ValidationResult for that step, or None if step not found

    Example:
        >>> result = validator.validate_specific_step("CommercialBreaker")
        >>> if result and not result.is_valid:
        ...     print(f"Commercial detection has {len(result.issues)} issues")
        ...     for issue in result.issues:
        ...         print(f"  - {issue.message}")
    """

def detect_processing_mode(self) -> Dict[str, Any]:
    """
    Detect the processing mode and platform from database state.

    Returns:
        Dictionary with:
            - mode: 'cutless' or 'traditional'
            - platform: 'DizqueTV', 'Tunarr', 'ComBreakDirect', or 'unknown'
            - confidence: 'high', 'medium', 'low'
            - indicators: List[str] of evidence used for detection
            - warnings: List[str] of compatibility warnings

    Example:
        >>> mode_info = validator.detect_processing_mode()
        >>> if mode_info['warnings']:
        ...     for warning in mode_info['warnings']:
        ...         print(f"⚠ {warning}")
    """

def get_step_names(self) -> List[str]:
    """
    Get list of all step names in pipeline order.

    Returns:
        List of step names (e.g., ["PlatformSelection", "PlexAuth", ...])
    """
```

---

### BaseValidator Class

**Location**: `/API/validators/BaseValidator.py`

Abstract base class that all step validators inherit from. Provides common utilities and enforces consistent interface.

#### Creating a Custom Validator

```python
from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel

class MyStepValidator(BaseValidator):
    """Validates MyStep output"""

    @property
    def step_name(self) -> str:
        return "MyStep"

    @property
    def required_tables(self) -> List[str]:
        return ["my_table"]

    @property
    def pipeline_order(self) -> int:
        return 10  # Position in pipeline

    def validate(self) -> ValidationResult:
        result = self.create_result(is_completed=False, is_valid=True)

        # Validate table structure
        if not self.validate_table_structure(
            result,
            "my_table",
            required_columns=["id", "data"],
            min_rows=1
        ):
            return result

        result.is_completed = True

        # Add custom validation logic...

        return result
```

#### Common Validation Utilities

```python
# Table operations
def check_table_exists(self, table_name: str) -> bool:
    """Check if a table exists in the database"""

def get_row_count(self, table_name: str) -> int:
    """Get number of rows in a table"""

def get_column_names(self, table_name: str) -> List[str]:
    """Get list of column names for a table"""

def check_required_columns(self, table_name: str, required_columns: List[str]) -> List[str]:
    """Check if required columns exist. Returns list of missing columns."""

def get_all_rows(self, table_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all rows from a table as dictionaries"""

# Combined validation
def validate_table_structure(self, result: ValidationResult, table_name: str,
                            required_columns: List[str], min_rows: int = 1) -> bool:
    """
    Check table exists, has required columns, and minimum rows.
    Adds issues to result if validation fails.
    Returns True if all checks pass.
    """

# Bump detection (consistent with main tools)
def is_bump(self, file_path: str) -> bool:
    """Check if file path is a bump (not anime). Uses same logic as EpisodeFilter."""

def is_anime(self, file_path: str) -> bool:
    """Check if file path is anime (not a bump). Inverse of is_bump()."""

# Mode and platform detection
def is_cutless_mode(self) -> bool:
    """Detect if database is using cutless mode"""

def get_processing_metadata(self) -> Dict[str, Any]:
    """
    Get cached processing metadata.
    Returns: {platform, is_cutless, mode, requires_bump_calculator}
    """

def get_available_versions(self) -> List[int]:
    """Get list of Toonami versions (e.g., [2, 3, 8, 9])"""
```

#### Issue Management

```python
def create_result(self, is_completed: bool = False, is_valid: bool = True) -> ValidationResult:
    """Create a ValidationResult for this step"""

def add_issue(self, result: ValidationResult, level: ValidationLevel,
             message: str, details: str, suggestion: str,
             table: Optional[str] = None, row_index: Optional[int] = None):
    """Add a validation issue to a result"""

def add_info(self, result: ValidationResult, message: str):
    """Add an informational message"""
```

---

### ValidationResult Class

**Location**: `/API/validators/ValidationResult.py`

Represents the result of validating a single pipeline step.

```python
@dataclass
class ValidationResult:
    step_name: str                     # Which step was validated
    is_valid: bool                     # Overall pass/fail status
    is_completed: bool                 # Whether step has been run
    issues: List[ValidationIssue]      # All validation issues
    metadata: Dict[str, Any]           # Additional info (row counts, etc.)

# Methods
def add_issue(self, issue: ValidationIssue):
    """Add issue. Automatically sets is_valid=False for ERROR/CRITICAL."""

def get_issues_by_level(self, level: ValidationLevel) -> List[ValidationIssue]:
    """Get all issues of a specific severity level"""

def get_issue_counts(self) -> Dict[str, int]:
    """Returns: {'critical': 0, 'error': 2, 'warning': 5, 'info': 3}"""

def get_status_symbol(self) -> str:
    """Returns: ○ (not run), ✗ (failed), ⚠ (warning), ✓ (success)"""

def get_status_description(self) -> str:
    """Human-readable status like 'Failed: 2 critical issue(s)'"""

def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary for JSON serialization"""
```

---

### ValidationIssue Class

**Location**: `/API/validators/ValidationResult.py`

Represents a single validation issue with the five components of good errors.

```python
@dataclass
class ValidationIssue:
    level: ValidationLevel          # INFO, WARNING, ERROR, CRITICAL
    step: str                       # Which validator found this
    message: str                    # User-friendly description
    details: str                    # Technical details
    suggestion: str                 # How to fix it
    table: Optional[str]            # Table name (if applicable)
    row_index: Optional[int]        # Row number (if applicable)
    timestamp: datetime             # When issue was detected

# Methods
def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary for JSON serialization"""

def __str__(self) -> str:
    """Human-readable format: '[ERROR] Step → table: message'"""
```

**Example Issue:**
```python
ValidationIssue(
    level=ValidationLevel.ERROR,
    step="CommercialBreaker",
    message="3 episodes missing commercial break timestamps",
    details="Files: Naruto S01E05.mkv, Naruto S01E06.mkv, Bleach S02E03.mkv",
    suggestion="Re-run CommercialBreaker in normal mode (not low power) to detect breaks",
    table="cuts"
)
```

---

### ValidationLevel Enum

```python
class ValidationLevel(Enum):
    INFO = "INFO"           # ℹ  Informational
    WARNING = "WARNING"     # ⚠  Should be addressed
    ERROR = "ERROR"         # ✗  Significant problem
    CRITICAL = "CRITICAL"   # ⊗  Step cannot proceed

def to_symbol(self) -> str:
    """Get visual symbol (ℹ, ⚠, ✗, ⊗)"""
```

---

### PipelineStatus Class

```python
@dataclass
class PipelineStatus:
    completed_steps: List[str]      # Names of completed steps
    current_step: Optional[str]     # Next incomplete step
    is_cutless_mode: bool           # Cutless mode detected
    total_steps: int                # Total number of validators
    metadata: Dict[str, Any]        # Phase info, versions, etc.

def completion_percentage(self) -> float:
    """Calculate percentage of pipeline completed (0-100)"""

def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary for JSON serialization"""
```

---

### PhaseTracker Class

**Location**: `/API/validators/PhaseTracker.py`

Tracks pipeline progress through logical workflow phases.

```python
from API.validators.PhaseTracker import PhaseTracker

tracker = PhaseTracker()

def get_current_phase(self, completed_steps: List[str]) -> Dict:
    """
    Determine current phase from completed steps.

    Returns dictionary with:
        - If phase complete: {completed_phase, completed_phase_name, status: 'complete'}
        - If in progress: {current_phase, current_phase_name, status: 'in_progress', progress}
        - If not started: {current_phase: 0, status: 'not_started'}
    """

def get_phase_summary(self, phase_num: int, completed_steps: List[str],
                     version_status: Optional[Dict] = None) -> str:
    """Get human-readable summary for a phase with checklist"""

def get_all_phases(self) -> Dict:
    """Get all phase definitions"""
```

**Phase Definitions:**
- **Phase 0**: Platform Setup (PlatformSelection, PlexAuth, FolderMaker)
- **Phase 1**: Content Discovery (ToonamiChecker)
- **Phase 2**: Prepare Uncut Content (LineupPrep, BumpEncoder, UncutEncoder, Multilineup, Merger, EpisodeFilter)
- **Phase 3**: Commercial Detection (CommercialBreaker – GetPlexTimestamps remains an optional tool outside of S.A.R.A.)
- **Phase 4**: Prepare Cut Anime (CommercialInjectorPrep, CommercialInjector, BlockMaker, PostCutBumpFilter, BumpCalculator, CutlessFinalizer)
- **Phase 5**: Optional Tools (ExtraBumps, PlexAutoSplitter, PlexSplitRenamer)
- **Phase 6**: Platform Export (PlexToDizqueTV, PlexToTunarr, ComBreakToComBreakDirect, FlexInjector)

---

### Integration with FrontEndLogic

The S.A.R.A. validation system is integrated into `LogicController` for use by all interfaces.

```python
from API.FrontEndLogic import LogicController

logic = LogicController()

# Run full validation (background thread)
logic.run_full_validation()

# Get quick pipeline status
status = logic.get_pipeline_status()
print(f"{status.completion_percentage():.1f}% complete")
```

**Methods Added to LogicController:**

```python
def run_full_validation(self):
    """
    Run comprehensive database validation.

    Creates DatabaseValidator with status callback for real-time updates.
    Runs validation in background thread.
    Broadcasts results through message broker.
    """

def get_pipeline_status(self) -> PipelineStatus:
    """
    Get quick pipeline status without full validation.

    Returns PipelineStatus object with completion info.
    Used by UI to show progress indicators.
    """
```

---

### Usage Examples

**Full Validation:**
```python
from API.validators.DatabaseValidator import DatabaseValidator

validator = DatabaseValidator(status_callback=print)
results = validator.run_full_validation()

# Check summary
summary = results['summary']
print(f"Completion: {summary['completion_percentage']:.1f}%")
print(f"Valid: {summary['valid_steps']}/{summary['completed_steps']}")
print(f"Issues: {summary['critical_count']} critical, {summary['error_count']} errors")

# Process issues
for issue in results['issues']:
    if issue['level'] in ['CRITICAL', 'ERROR']:
        print(f"\n{issue['level']} in {issue['step']}")
        print(f"  {issue['message']}")
        print(f"  Fix: {issue['suggestion']}")
```

**Quick Status Check:**
```python
validator = DatabaseValidator()
status = validator.get_pipeline_status()

print(f"Pipeline: {status.completion_percentage():.1f}% complete")
print(f"Current step: {status.current_step}")
print(f"Mode: {'Cutless' if status.is_cutless_mode else 'Traditional'}")
print(f"Completed: {', '.join(status.completed_steps)}")
```

**Validate Specific Step:**
```python
result = validator.validate_specific_step("CommercialBreaker")

if result:
    if result.is_completed and result.is_valid:
        print("✓ Commercial detection completed successfully")
    elif result.is_completed:
        print(f"✗ Commercial detection has {len(result.issues)} issues")
    else:
        print("○ Commercial detection not run yet")
```

**Mode Detection:**
```python
mode_info = validator.detect_processing_mode()

print(f"Mode: {mode_info['mode']}")
print(f"Platform: {mode_info['platform']}")
print(f"Confidence: {mode_info['confidence']}")

if mode_info['warnings']:
    print("\n⚠ Warnings:")
    for warning in mode_info['warnings']:
        print(f"  • {warning}")
```

---

### All Step Validators

The system includes 18 step validators and 2 integrity validators:

**Phase 0 (Platform Setup):**
- `PlatformSelectionValidator` - Validates platform type configuration
- `PlexAuthValidator` - Validates Plex authentication (conditional)
- `FolderMakerValidator` - Validates folder paths and permissions

**Phase 1 (Content Discovery):**
- `ToonamiCheckerValidator` - Validates show/episode detection

**Phase 2 (Prepare Uncut Content):**
- `LineupPrepValidator` - Validates bump preparation
- `BumpEncoderValidator` - Validates bump encoding
- `UncutEncoderValidator` - Validates uncut content
- `MultilineupValidator` - Validates multi-show bump organization
- `MergerValidator` - Validates lineup merging (runs twice: uncut + cut)
- `EpisodeFilterValidator` - Validates episode filtering

**Phase 3 (Commercial Detection):**
- `CommercialBreakerValidator` - Validates commercial break detection

**Phase 4 (Prepare Cut Anime):**
- `CommercialInjectorPrepValidator` - Validates injector prep (traditional mode only)
- `CommercialInjectorValidator` - Validates commercial injection
- `BlockMakerValidator` - Validates BLOCK_ID assignment
- `PostCutBumpFilterValidator` - Validates postcut bump filtering (optional)
- `BumpCalculatorValidator` - Validates bump duration calculation (cutless + ComBreakDirect)
- `CutlessFinalizerValidator` - Validates cutless finalization (cutless mode only)

**Integrity Validators:**
- `LineupIntegrityValidator` - Validates bump placement rules
- `ReferentialIntegrityValidator` - Validates cross-table consistency

**Special Validators:**
- `AppDataValidator` - Validates app_data configuration

---

## DatabaseManager API

The `DatabaseManager` class in `API/utils/DatabaseManager.py` provides thread-safe database operations with automatic retry logic, including methods for working with dictionary-based data structures.

### Getting the DatabaseManager

```python
from API.utils.DatabaseManager import get_db_manager

class MyModule:
    def __init__(self):
        self.db_manager = get_db_manager()
```

### Basic Query Methods

```python
def fetchone(self, query: str, params: Optional[Tuple] = None) -> Optional[Tuple]:
    """
    Execute a query and fetch one result as a tuple.

    Args:
        query: SQL query to execute
        params: Optional query parameters

    Returns:
        Tuple of column values or None
    """

def fetchall(self, query: str, params: Optional[Tuple] = None) -> List[Tuple]:
    """
    Execute a query and fetch all results as tuples.

    Args:
        query: SQL query to execute
        params: Optional query parameters

    Returns:
        List of tuples, one per row
    """

def execute(self, query: str, params: Optional[Tuple] = None) -> int:
    """
    Execute a query that doesn't return results.

    Args:
        query: SQL query to execute
        params: Optional query parameters

    Returns:
        Number of rows affected
    """
```

### Dictionary-Based Methods

**These methods return and accept native Python dictionaries.**

```python
def fetchall_as_dicts(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a query and fetch all results as a list of dictionaries.

    Each row is returned as a dictionary with column names as keys.
    This replaces the need for pd.read_sql() in most cases.

    Args:
        query: SQL query to execute
        params: Optional query parameters

    Returns:
        List of dictionaries, one per row
        Empty list if no results

    Example:
        >>> data = db_manager.fetchall_as_dicts("SELECT * FROM shows WHERE active = ?", (True,))
        >>> # Returns: [{"id": 1, "name": "Naruto", "active": True}, ...]
        >>> for row in data:
        >>>     print(row['name'])
    """

def fetchone_as_dict(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
    """
    Execute a query and fetch one result as a dictionary.

    Args:
        query: SQL query to execute
        params: Optional query parameters

    Returns:
        Dictionary with column names as keys, or None if no results

    Example:
        >>> show = db_manager.fetchone_as_dict("SELECT * FROM shows WHERE id = ?", (1,))
        >>> # Returns: {"id": 1, "name": "Naruto", "active": True}
        >>> if show:
        >>>     print(show['name'])
    """

def bulk_insert_dicts(self, table_name: str, data: List[Dict[str, Any]]) -> int:
    """
    Bulk insert a list of dictionaries into a table.

    All dictionaries must have the same keys (columns).
    Uses executemany for efficient bulk insertion.

    Args:
        table_name: Name of the table to insert into
        data: List of dictionaries with column names as keys

    Returns:
        Number of rows inserted

    Raises:
        ValueError: If data is empty or dictionaries have inconsistent keys

    Example:
        >>> rows = [
        >>>     {"show": "Naruto", "season": 1, "episodes": 220},
        >>>     {"show": "Bleach", "season": 1, "episodes": 366}
        >>> ]
        >>> count = db_manager.bulk_insert_dicts("anime_info", rows)
        >>> print(f"Inserted {count} rows")
    """

def create_table_from_dicts(self, table_name: str, data: List[Dict[str, Any]],
                            if_exists: str = 'fail') -> None:
    """
    Create a table from a list of dictionaries with automatic type inference.

    Column types are inferred from the first row:
    - int values → INTEGER
    - float values → REAL
    - all others → TEXT

    Args:
        table_name: Name of the table to create
        data: List of dictionaries (must have at least one element)
        if_exists: What to do if table exists:
            - 'fail': Raise error (default)
            - 'replace': Drop existing table and create new one
            - 'append': Insert data into existing table

    Raises:
        ValueError: If data is empty or if_exists is invalid
        Exception: If table exists and if_exists='fail'

    Example:
        >>> data = [
        >>>     {"name": "Naruto", "episodes": 220, "rating": 8.3},
        >>>     {"name": "Bleach", "episodes": 366, "rating": 7.9}
        >>> ]
        >>> db_manager.create_table_from_dicts("anime_stats", data, if_exists='replace')
        >>> # Creates table: name TEXT, episodes INTEGER, rating REAL

    Note:
        - All rows are normalized to have the same columns (missing values filled with None)
        - Type inference uses the first row's values
        - NULL/None values are allowed after the first row
    """

def replace_table_data(self, table_name: str, data: List[Dict[str, Any]]) -> None:
    """
    Replace all data in a table with new data.

    This is a convenience method that:
    1. Drops the table if it exists
    2. Creates a new table with the same schema
    3. Inserts the new data

    Equivalent to create_table_from_dicts(table_name, data, if_exists='replace')

    Args:
        table_name: Name of the table
        data: List of dictionaries with new data

    Example:
        >>> # Load, transform, and save back
        >>> data = db_manager.fetchall_as_dicts("SELECT * FROM shows")
        >>> for row in data:
        >>>     row['normalized_name'] = row['name'].lower()
        >>> db_manager.replace_table_data("shows", data)
    """

def drop_table(self, table_name: str) -> None:
    """
    Drop a table if it exists.

    Args:
        table_name: Name of the table to drop

    Example:
        >>> db_manager.drop_table("temporary_processing_table")
    """
```

### CRUD Operations

```python
def insert(self, table_name: str, data: Dict[str, Any]) -> int:
    """
    Insert a single row into a table.

    Args:
        table_name: Name of the table
        data: Dictionary with column names as keys

    Returns:
        ID of inserted row (lastrowid)
    """

def update(self, table_name: str, data: Dict[str, Any],
          where: str, params: Tuple) -> int:
    """
    Update rows in a table.

    Args:
        table_name: Name of the table
        data: Dictionary with columns to update
        where: WHERE clause (without 'WHERE' keyword)
        params: Parameters for WHERE clause

    Returns:
        Number of rows updated
    """

def delete(self, table_name: str, where: str, params: Tuple) -> int:
    """
    Delete rows from a table.

    Args:
        table_name: Name of the table
        where: WHERE clause (without 'WHERE' keyword)
        params: Parameters for WHERE clause

    Returns:
        Number of rows deleted
    """
```

### Utility Methods

```python
def table_exists(self, table_name: str) -> bool:
    """Check if a table exists in the database"""

def get_table_schema(self, table_name: str) -> List[Tuple]:
    """Get the schema information for a table"""

def get_table_names(self) -> List[str]:
    """Get a list of all table names in the database"""
```

### Transaction Management

```python
def transaction(self) -> ContextManager:
    """
    Context manager for database transactions.

    Automatically commits on success, rolls back on exception.

    Example:
        >>> with db_manager.transaction() as conn:
        >>>     cursor = conn.cursor()
        >>>     cursor.execute("INSERT INTO table1 VALUES (?, ?)", (val1, val2))
        >>>     cursor.execute("UPDATE table2 SET col = ? WHERE id = ?", (val3, id))
        >>>     # Automatically commits when context exits successfully
        >>>     # Automatically rolls back if any exception occurs
    """
```

### Thread Safety

- Each thread gets its own database connection automatically
- All methods use automatic retry logic for database locks
- Exponential backoff with configurable max attempts
- No manual connection management required

### Performance Considerations

- **Dict lists are better for**: Small to medium datasets (< 10,000 rows), simple transformations
- **Pandas would be better for**: Very large datasets (> 100,000 rows), complex aggregations
- **For CommercialBreaker**: Dict lists provide lower memory footprint and simpler code for typical use cases

## NetworkUtils API

The `NetworkUtils` module in `API/utils/NetworkUtils.py` provides stdlib-based HTTP operations using curl subprocess.

### Module Overview

This module provides:
- **CurlHttpClient**: HTTP client using system curl via subprocess
- **CurlResponse**: Response object mimicking requests.Response interface
- **WikipediaTableParser**: Regex-based HTML table parser
- **Exception Classes**: Compatible with requests library exceptions

### CurlHttpClient

Drop-in replacement for basic `requests` operations using system curl.

```python
from API.utils.NetworkUtils import CurlHttpClient

class MyTool:
    def fetch_data(self):
        # GET request
        response = CurlHttpClient.get(
            "https://api.example.com/data",
            headers={"User-Agent": "MyApp/1.0"},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return data
```

#### Methods

```python
@staticmethod
def get(url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 30) -> CurlResponse:
    """
    Perform HTTP GET request using curl subprocess.

    Args:
        url: Target URL (must be valid HTTP/HTTPS URL)
        headers: Optional dictionary of HTTP headers
        params: Optional dictionary of query parameters (appended to URL)
        timeout: Timeout in seconds (default: 30)

    Returns:
        CurlResponse object with status_code, text, and json() method

    Raises:
        Timeout: If request exceeds timeout duration
        ConnectionError: If curl cannot connect to the server
        RequestException: For other curl errors (exit codes 1-99)

    Example:
        >>> response = CurlHttpClient.get(
        >>>     "https://en.wikipedia.org/api/rest_v1/page/html/List_of_programs_broadcast_by_Toonami",
        >>>     headers={"User-Agent": "CommercialBreaker/1.0"},
        >>>     timeout=10
        >>> )
        >>> if response.status_code == 200:
        >>>     html = response.text
    """

@staticmethod
def post(url: str,
         json_data: Optional[Dict] = None,
         data: Optional[Union[Dict, str]] = None,
         headers: Optional[Dict[str, str]] = None,
         timeout: int = 30) -> CurlResponse:
    """
    Perform HTTP POST request using curl subprocess.

    Args:
        url: Target URL
        json_data: Optional dictionary to send as JSON body (sets Content-Type: application/json)
        data: Optional data to send as form data (dict) or raw body (str)
        headers: Optional dictionary of HTTP headers
        timeout: Timeout in seconds (default: 30)

    Returns:
        CurlResponse object

    Raises:
        Timeout: If request exceeds timeout
        ConnectionError: If curl cannot connect
        RequestException: For other curl errors

    Example:
        >>> response = CurlHttpClient.post(
        >>>     "https://api.example.com/endpoint",
        >>>     json_data={"key": "value"},
        >>>     headers={"Authorization": "Bearer token"}
        >>> )
        >>> print(response.status_code)
    """
```

### CurlResponse

Response object that mimics the `requests.Response` interface for compatibility.

```python
class CurlResponse:
    """
    Response object mimicking requests.Response interface.

    Attributes:
        text (str): Response body as string
        status_code (int): HTTP status code
        _content (bytes): Raw response content
    """

    @property
    def text(self) -> str:
        """
        Get response body as string.

        Returns:
            Response body decoded as UTF-8
        """

    @property
    def status_code(self) -> int:
        """
        Get HTTP status code.

        Returns:
            HTTP status code (200, 404, 500, etc.)
        """

    def json(self) -> Any:
        """
        Parse response body as JSON.

        Returns:
            Parsed JSON data (dict, list, etc.)

        Raises:
            json.JSONDecodeError: If response is not valid JSON

        Example:
            >>> response = CurlHttpClient.get("https://api.example.com/data")
            >>> data = response.json()
            >>> print(data['key'])
        """

    def raise_for_status(self) -> None:
        """
        Raise HTTPError if status code indicates an error (4xx or 5xx).

        Raises:
            HTTPError: If status code >= 400

        Example:
            >>> response = CurlHttpClient.get(url)
            >>> response.raise_for_status()  # Raises if error
            >>> data = response.json()  # Safe to proceed
        """
```

### WikipediaTableParser

Regex-based HTML table parser for extracting tabular data from Wikipedia pages.

```python
from API.utils.NetworkUtils import WikipediaTableParser

class MyTool:
    def parse_wikipedia_table(self, html):
        parser = WikipediaTableParser(html)
        tables = parser.extract_tables()

        for table in tables:
            for row in table['rows']:
                # Process row data
                pass
```

#### Methods

```python
def __init__(self, html: str):
    """
    Initialize parser with HTML content.

    Args:
        html: HTML content containing tables
    """

def extract_tables(self) -> List[Dict[str, Any]]:
    """
    Extract all tables from HTML using regex patterns.

    Returns:
        List of table dictionaries, each containing:
        - 'rows': List of row dictionaries with column data
        - Additional metadata as needed

    Example:
        >>> html = response.text
        >>> parser = WikipediaTableParser(html)
        >>> tables = parser.extract_tables()
        >>> for table in tables:
        >>>     print(f"Found table with {len(table['rows'])} rows")
        >>>     for row in table['rows']:
        >>>         print(row)  # Dict with column names as keys
    """
```

### Exception Classes

Compatible exception hierarchy matching the requests library.

```python
class RequestException(Exception):
    """
    Base exception for all network request errors.

    All other NetworkUtils exceptions inherit from this.
    """

class HTTPError(RequestException):
    """
    Exception raised for HTTP error status codes (4xx, 5xx).

    Raised by CurlResponse.raise_for_status() when status code >= 400.
    """

class Timeout(RequestException):
    """
    Exception raised when request exceeds timeout duration.

    Raised when curl subprocess times out (exit code 28).
    """

class ConnectionError(RequestException):
    """
    Exception raised for connection errors.

    Raised when curl cannot connect to server (exit codes 6, 7).
    """
```

### Usage Examples

#### Basic GET Request with Error Handling

```python
from API.utils.NetworkUtils import CurlHttpClient, Timeout, ConnectionError, HTTPError

def fetch_with_retry(url, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            response = CurlHttpClient.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Timeout:
            print(f"Attempt {attempt + 1}: Timeout")
            if attempt == max_attempts - 1:
                raise
        except ConnectionError as e:
            print(f"Attempt {attempt + 1}: Connection error - {e}")
            if attempt == max_attempts - 1:
                raise
        except HTTPError as e:
            print(f"HTTP error: {e}")
            raise  # Don't retry on HTTP errors
```

#### Wikipedia API Integration

```python
def fetch_toonami_shows(self):
    """Fetch Toonami shows from Wikipedia."""
    url = "https://en.wikipedia.org/api/rest_v1/page/html/List_of_programs_broadcast_by_Toonami"
    headers = {"User-Agent": "CommercialBreaker/1.0 (github.com/yourrepo)"}

    try:
        response = CurlHttpClient.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        parser = WikipediaTableParser(response.text)
        tables = parser.extract_tables()

        for table in tables:
            for row in table['rows']:
                show_name = row.get('show_name', '')
                # Process show data

    except Timeout:
        print("Wikipedia request timed out")
    except ConnectionError:
        print("Cannot connect to Wikipedia")
    except Exception as e:
        print(f"Error fetching data: {e}")
```

#### POST Request with JSON

```python
def send_platform_config(self, config_data):
    """Send configuration to DizqueTV/Tunarr."""
    url = f"{self.platform_url}/api/channels"

    response = CurlHttpClient.post(
        url,
        json_data=config_data,
        headers={"Content-Type": "application/json"},
        timeout=30
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed with status {response.status_code}")
        return None
```

### System Requirements

- **curl must be installed** on the system
  - macOS/Linux: Usually pre-installed
  - Windows: Included in Windows 10+ by default
  - Docker: Added to Dockerfile with `apt-get install curl`

### Migration from requests

The NetworkUtils module provides a compatible interface for basic requests usage:

**Old (requests):**
```python
import requests

response = requests.get(url, headers=headers, timeout=30)
if response.status_code == 200:
    data = response.json()
```

**New (NetworkUtils):**
```python
from API.utils.NetworkUtils import CurlHttpClient

response = CurlHttpClient.get(url, headers=headers, timeout=30)
if response.status_code == 200:
    data = response.json()
```

**Key Differences:**
- NetworkUtils uses system curl (subprocess) instead of Python HTTP libraries
- No persistent session support (each request is independent)
- No SSL certificate verification control (uses curl defaults)
- No cookie jar support
- Simpler interface suitable for CommercialBreaker's use cases

### Performance Notes

- Each request spawns a curl subprocess (minimal overhead)
- No persistent connections between requests
- Suitable for infrequent API calls (Wikipedia scraping, platform integration)
- Not suitable for high-frequency API polling

#### Workflow API



**Phase 1: Plex Authentication**
```python
def login_to_plex(self) -> None:
    """
    Initiates Plex authentication flow:
    1. Creates PlexServerList instance
    2. Handles OAuth-style authentication
    3. Publishes auth URL for browser opening
    4. Fetches available servers
    5. Broadcasts server choices to UIs
    """

def on_server_selected(self, selected_server: str) -> None:
    """Trigger library fetch after a server is chosen"""

def fetch_libraries(self, selected_server: str) -> None:
    """
    Fetches libraries for selected Plex server:
    1. Creates PlexLibraryManager and PlexLibraryFetcher
    2. Retrieves server URL and library list
    3. Broadcasts library choices to UIs
    """
```

**Phase 1b: Cut-less / Platform Check**
```python
def check_dizquetv_compatibility(self) -> bool:
    """Ask FlagManager whether cut-less mode is allowed for current platform"""
```

**Phase 1c: Continue Buttons**
```python
def on_continue_first(self, selected_anime_library: str, selected_toonami_library: str, 
                     platform_url: str, platform_type: str = 'dizquetv') -> None:
    """
    Completes initial setup phase:
    1. Stores library and platform selections
    2. Evaluates platform compatibility for cutless mode
    3. Updates cutless mode flags accordingly
    """

def on_continue_second(self, selected_anime_library: str, selected_toonami_library: str,
                      plex_url: str, plex_token: str, platform_url: str, 
                      platform_type: str = 'dizquetv') -> None:
    """
    Alternative setup for manual Plex configuration:
    1. Validates and stores manual Plex credentials
    2. Stores library and platform selections
    3. Evaluates platform compatibility
    """

def on_continue_third(self, anime_folder: str, bump_folder: str, 
                     special_bump_folder: str, working_folder: str) -> None:
    """
    Configures local directory paths:
    1. Validates folder paths
    2. Stores folder configurations
    3. Prepares working directory structure
    """

def on_continue_fourth(self) -> None:
    """Placeholder for future workflow phase"""

def on_continue_fifth(self) -> None:
    """Placeholder for future workflow phase"""

def on_continue_sixth(self) -> None:
    """Placeholder for future workflow phase"""

def on_continue_seventh(self) -> None:
    """Placeholder for future workflow phase"""
```

**Event Helpers**
```python
def is_filtered_complete(self) -> bool:
    """Check if filtered files processing is complete"""

def reset_filter_event(self) -> None:
    """Reset filter event state"""

def set_filter_event(self) -> None:
    """Set filter event state"""
```

**Phase 2: Content Preparation**
```python
def prepare_content(self, display_show_selection: callable) -> None:
    """
    Prepares content for processing:
    1. Creates working folder structure
    2. Runs ToonamiChecker to identify valid shows
    3. Calls display_show_selection callback for user choice
    4. Processes selected shows and creates uncut lineup
    5. Prepares bump encoding and multi-lineup processing
    
    Args:
        display_show_selection: Callback function that presents show choices
                               and returns user selections
    """

def move_filtered(self, prepopulate: bool = False) -> None:
    """
    Handles filtered show processing:
    
    Args:
        prepopulate: If True, prepares files for selection without moving
                    If False, moves files to toonami_filtered folder (legacy)
    """

def get_plex_timestamps(self) -> None:
    """
    Retrieves Plex "Skip Intro" timestamps:
    1. Connects to Plex server
    2. Extracts intro timestamps for all shows
    3. Creates plex_timestamps.txt files for CommercialBreaker
    """
```

**Phase 3: Cut Anime Preparation**
```python
def prepare_cut_anime(self) -> None:
    """
    Prepares cut anime for lineup generation:
    1. Runs CommercialInjectorPrep (traditional) or skips (cutless)
    2. Executes CommercialInjector for commercial injection planning
    3. Creates block IDs for show organization
    4. Runs ShowScheduler merger for all lineup variants
    5. Handles CutlessFinalizer for virtual cut processing (if enabled)
    """
```

**Phase 3b: Plex Library Preparation and Optional Bump Injection**

```python
def create_prepare_plex(self) -> None:
    """
    Prepares Plex library for channel creation:
    1. Splits merged Plex items using PlexAutoSplitter
    2. Updates show titles using PlexLibraryUpdater
    3. Ensures proper show separation and naming
    """

def add_special_bumps(self) -> None:
    """Add special bump files to the Plex library"""
```

**Phase 4: Line-up / Channel Generation**
```python
def prepare_toonami_channel(self, start_from_last_episode: bool,
                            toonami_version: str) -> None:
    """Generate continuation tables before channel creation"""

def create_toonami_channel(self, toonami_version: str, channel_number: str,
                          flex_duration: str, start_from_last_episode: bool = False) -> None:
    """
    Creates the final Toonami channel:
    1. Configures lineup parameters
    2. Creates channel using PlexToDizqueTV, PlexToTunarr, or ComBreakToComBreakDirect
    3. Handles channel numbering and flex timing
    4. Manages episode continuation logic
    5. Automatically starts ComBreakDirect server if platform is "combreakdirect"
    """

def create_toonami_channel_cont(self, toonami_version: str,
                                channel_number: str, flex_duration: str) -> None:
    """Create a continuation channel using previously generated tables"""

def add_flex(self, channel_number: str, duration: str) -> None:
    """
    Adds commercial break flex to DizqueTV channels:
    1. Injects flexible programming between segments
    2. Creates authentic commercial break experience
    """
```

**ComBreakDirect Server Management**
```python
def _ensure_combreakdirect_server(self) -> None:
    """
    Ensures ComBreakDirect server is running:
    1. Checks if server is already running via health check
    2. If not running, starts server in background thread
    3. Waits for server to become ready (max 30 seconds)
    4. Raises exception if server fails to start
    """

def _is_combreakdirect_running(self) -> bool:
    """
    Checks if ComBreakDirect server is responding:
    - Queries {CBDIRECT_BASE_URL}/status endpoint
    - Returns True if server responds with status 200
    - Returns False if connection fails or timeout
    """

def _wait_for_combreakdirect_server(self, timeout: int = 30) -> bool:
    """
    Waits for ComBreakDirect server to become ready:
    - Polls server status endpoint every second
    - Returns True if server becomes ready within timeout
    - Returns False if timeout expires

    Args:
        timeout: Maximum seconds to wait (default: 30)
    """
```

```

**Cutless Mode Management**
```python
def _on_cutless_change(self, enabled: bool) -> None:
    """
    Callback for cutless mode state changes:
    1. Updates internal cutless flags
    2. Broadcasts state change to subscribed UIs
    3. Handles platform compatibility warnings
    """
```

**Threading Support**
```python
# All long-running operations are executed in background threads
# Examples from the codebase:

def login_to_plex(self):
    def login_thread():
        # Long-running authentication logic
        pass
    
    thread = threading.Thread(target=login_thread)
    thread.start()
```

## Plex Client API

The Plex client implementation provides OAuth authentication, account management, and server operations. Located in `API/utils/`, it uses Python's standard library `urllib` and `CurlHttpClient`.

### PlexClient Module (`API/utils/PlexClient.py`)

#### Class: PlexAuthClient

Handles Plex OAuth authentication using the PIN flow.

```python
from API.utils.PlexClient import PlexAuthClient

auth_client = PlexAuthClient()
```

**Methods:**

```python
def start_auth(self) -> tuple[str, str]:
    """
    Initiate OAuth PIN authentication flow.

    Returns:
        tuple: (auth_url, pin_id)
            - auth_url: URL for user to visit and approve access
            - pin_id: PIN identifier for polling

    Example:
        auth_url, pin_id = auth_client.start_auth()
        print(f"Visit: {auth_url}")
    """

def poll_for_token(self, pin_id: str, timeout: int = 120) -> str | None:
    """
    Poll for authentication token after user approval.

    Args:
        pin_id: PIN identifier from start_auth()
        timeout: Maximum seconds to wait (default: 120)

    Returns:
        str: Plex authentication token, or None if timeout

    Example:
        token = auth_client.poll_for_token(pin_id, timeout=120)
        if token:
            print("Authentication successful!")
    """

def get_token(self) -> str | None:
    """
    Complete authentication flow convenience method.
    Combines start_auth() and poll_for_token().

    Returns:
        str: Authentication token or None

    Example:
        token = auth_client.get_token()
    """
```

#### Class: PlexAccountClient

Manages Plex account operations and server discovery.

```python
from API.utils.PlexClient import PlexAccountClient

account = PlexAccountClient(token)
```

**Methods:**

```python
def get_resources(self) -> list['PlexResource']:
    """
    Retrieve all Plex resources (servers, players, etc.) for the account.

    Returns:
        list[PlexResource]: List of resources with connection info

    Example:
        resources = account.get_resources()
        for resource in resources:
            if resource.provides == 'server':
                print(f"Server: {resource.name}")
                for conn in resource.connections:
                    print(f"  URL: {conn['uri']}")
    """

def get_servers(self) -> list['PlexResource']:
    """
    Get only server resources (filters out players, etc.).

    Returns:
        list[PlexResource]: Server resources only

    Example:
        servers = account.get_servers()
        server_names = [s.name for s in servers]
    """
```

#### Class: PlexResource

Represents a Plex server or device resource.

**Attributes:**
```python
class PlexResource:
    name: str                    # Resource name
    client_identifier: str       # Unique identifier
    provides: str               # Resource type ('server', 'player', etc.)
    owned: bool                 # Whether user owns this resource
    connections: list[dict]     # List of connection URLs and metadata
```

**Example Usage:**
```python
resources = account.get_resources()
for resource in resources:
    if resource.provides == 'server' and resource.owned:
        print(f"Server: {resource.name}")
        print(f"ID: {resource.client_identifier}")
        for conn in resource.connections:
            print(f"  {conn['uri']} (local: {conn['local']})")
```

### PlexServer Module (`API/utils/PlexServer.py`)

#### Class: SimplePlexServer

Minimal Plex Media Server client.

```python
from API.utils.PlexServer import SimplePlexServer

server = SimplePlexServer(base_url, token, client_identifier=None)
```

**Methods:**

```python
def get_libraries(self) -> list['SimplePlexLibrary']:
    """
    Get all libraries on the server.

    Returns:
        list[SimplePlexLibrary]: List of library objects

    Example:
        libraries = server.get_libraries()
        for lib in libraries:
            print(f"Library: {lib.title} (type: {lib.type})")
    """

def get_library_by_name(self, name: str) -> 'SimplePlexLibrary' | None:
    """
    Get library by name.

    Args:
        name: Library name to find

    Returns:
        SimplePlexLibrary or None if not found
    """
```

#### Class: SimplePlexLibrary

Represents a Plex library.

**Attributes:**
- `title`: Library name
- `type`: Library type ('movie', 'show', etc.)
- `key`: Library key

**Methods:**

```python
def get_sections(self) -> list['SimplePlexSection']:
    """Get all sections in this library"""

def get_section_by_title(self, title: str) -> 'SimplePlexSection' | None:
    """Get section by title"""
```

#### Class: SimplePlexSection

Represents a library section.

**Methods:**

```python
def get_shows(self) -> list['SimplePlexShow']:
    """Get all TV shows in this section"""

def get_show_by_title(self, title: str) -> 'SimplePlexShow' | None:
    """Get show by title"""
```

#### Class: SimplePlexShow

Represents a TV show.

**Attributes:**
- `title`: Show title
- `rating_key`: Plex rating key
- `key`: Show key

**Methods:**

```python
def get_episodes(self) -> list['SimplePlexEpisode']:
    """
    Get all episodes for this show.

    Returns:
        list[SimplePlexEpisode]: All episodes across all seasons
    """
```

#### Class: SimplePlexEpisode

Represents an episode.

**Attributes:**
- `title`: Episode title
- `rating_key`: Plex rating key
- `key`: Episode key
- `index`: Episode number
- `parent_index`: Season number
- `media`: List of media parts

### PlexConnectionHelper Module (`API/utils/PlexConnectionHelper.py`)

#### Class: PlexConnectionHelper

Smart connection management with automatic retry logic.

```python
from API.utils.PlexConnectionHelper import PlexConnectionHelper

helper = PlexConnectionHelper(token)
```

**Methods:**

```python
def discover_servers(self) -> list['PlexResource']:
    """
    Discover all available Plex servers for the authenticated account.

    Returns:
        list[PlexResource]: List of server resources

    Example:
        servers = helper.discover_servers()
        print(f"Found {len(servers)} servers")
    """

def connect_smart(self, resource: 'PlexResource') -> 'SimplePlexServer' | None:
    """
    Smart connect to a Plex resource with automatic URL retry.

    Tries connection URLs in this order:
    1. Local network URLs (fastest)
    2. Direct connections
    3. Relay URLs (fallback)

    Args:
        resource: PlexResource object from discover_servers()

    Returns:
        SimplePlexServer or None if all connections fail

    Example:
        servers = helper.discover_servers()
        for server_resource in servers:
            server = helper.connect_smart(server_resource)
            if server:
                print(f"Connected to {server_resource.name}")
                break
    """

def connect_with_server_name(self, server_name: str) -> 'SimplePlexServer' | None:
    """
    Discover and connect to a server by name.
    Convenience method that combines discovery and smart connection.

    Args:
        server_name: Name of the Plex server

    Returns:
        SimplePlexServer or None if server not found or connection fails

    Example:
        server = helper.connect_with_server_name("My Plex Server")
        if server:
            libraries = server.get_libraries()
    """
```

**Connection Strategy:**

The `connect_smart()` method implements intelligent connection retry:

1. Sorts connections by preference (local > direct > relay)
2. Attempts each connection URL with timeout
3. Returns first successful connection
4. Logs all connection attempts for debugging

**Example: Complete Authentication Flow:**

```python
from API.utils.PlexClient import PlexAuthClient
from API.utils.PlexConnectionHelper import PlexConnectionHelper

# 1. Authenticate
auth = PlexAuthClient()
token = auth.get_token()  # User visits auth URL and approves

# 2. Connect to server
helper = PlexConnectionHelper(token)
server = helper.connect_with_server_name("My Server")

# 3. Access libraries
if server:
    libraries = server.get_libraries()
    for lib in libraries:
        if lib.type == 'show':
            sections = lib.get_sections()
            for section in sections:
                shows = section.get_shows()
                print(f"Found {len(shows)} shows in {section.title}")
```

## ToonamiTools Module APIs

### Authentication Classes

#### PlexServerList
```python
class PlexServerList:
    def __init__(self):
        """Initialize Plex authentication"""
    
    def run(self) -> None:
        """Execute authentication flow"""
    
    def set_auth_url_callback(self, callback: callable) -> None:
        """Set callback for auth URL handling"""
```

#### PlexLibraryManager
```python
class PlexLibraryManager:
    def __init__(self, server_name: str, token: str):
        """Initialize with server and token"""
    
    def run(self) -> str:
        """Returns Plex server URL"""
```

#### PlexLibraryFetcher  
```python
class PlexLibraryFetcher:
    def __init__(self, plex_url: str, token: str):
        """Initialize with server URL and token"""
    
    def run(self) -> None:
        """Fetches library list, populates self.libraries"""
```

### Content Processing Classes

#### ToonamiChecker
```python
class ToonamiChecker:
    def __init__(self, anime_folder: str):
        """Initialize with anime directory path"""
    
    def prepare_episode_data(self) -> tuple[list, list]:
        """Returns (unique_show_names, toonami_episodes)"""
    
    def process_selected_shows(self, selected_shows: list, episodes: list) -> None:
        """Process user-selected shows for inclusion"""
```

#### MediaProcessor (LineupPrep)
```python
class MediaProcessor:
    def __init__(self, bump_folder: str):
        """Initialize with bumps directory"""

    def run(self) -> None:
        """Process and catalog bump files"""
```

### DizqueTV Helper Functions

The `ToonamiTools/utils/DizqueTVHelpers.py` module provides utility functions for creating DizqueTV-compatible data structures from Plex media items.

#### create_program_dict_from_plex_item
```python
def create_program_dict_from_plex_item(
    plex_item,
    plex_server,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> dict:
    """
    Create a DizqueTV program dictionary from a PlexAPI item.

    Args:
        plex_item: PlexAPI Video, Movie, Episode, or Track object
        plex_server: PlexAPI PlexServer object
        start_time: Optional start time in milliseconds (for cutless mode)
        end_time: Optional end time in milliseconds (for cutless mode)

    Returns:
        Dictionary containing program data in DizqueTV format with keys:
        - title: Program title
        - key: Plex item key
        - ratingKey: Plex rating key (as string)
        - icon: Full URL to thumbnail image
        - type: Item type ('episode', 'movie', 'track')
        - duration: Duration in milliseconds
        - summary: Program description
        - rating: Content rating (e.g., 'TV-PG', 'PG-13')
        - date: Original air date (YYYY-MM-DD format)
        - year: Release year
        - plexFile: Plex media part key
        - file: Full file path on Plex server
        - serverKey: Plex server friendly name

        For episodes, additional keys:
        - showTitle: Series name
        - episode: Episode number (int)
        - season: Season number (int)
        - episodeIcon: Episode thumbnail URL
        - seasonIcon: Season poster URL
        - showIcon: Series poster URL

        For cutless mode:
        - seekPosition: Start time in milliseconds (if start_time provided)
        - endPosition: End time in milliseconds (if end_time provided)

    Raises:
        ValueError: If media parts cannot be found for the Plex item

    Example:
        from plexapi.server import PlexServer
        from ToonamiTools.utils.DizqueTVHelpers import create_program_dict_from_plex_item

        plex = PlexServer('http://localhost:32400', token='your_token')
        episode = plex.library.section('TV Shows').get('Cowboy Bebop').episodes()[0]

        # Standard program entry
        program = create_program_dict_from_plex_item(episode, plex)

        # Cutless mode with custom start/end times (in milliseconds)
        program = create_program_dict_from_plex_item(
            episode,
            plex,
            start_time=5000,      # Start at 5 seconds
            end_time=1380000      # End at 23 minutes
        )
    """
```

**Implementation Notes:**
- Automatically detects item type (episode, movie, track) from PlexAPI object
- Handles date formatting consistently (YYYY-MM-DD)
- Constructs authenticated URLs with Plex tokens for thumbnails/icons
- Supports cutless mode via optional start_time/end_time parameters
- Gracefully handles missing metadata fields with empty strings

#### create_default_channel_settings
```python
def create_default_channel_settings(channel_number: int, channel_name: str) -> dict:
    """
    Create default channel settings for DizqueTV.

    Args:
        channel_number: Channel number (e.g., 1, 2, 101)
        channel_name: Channel display name (e.g., 'Toonami')

    Returns:
        Dictionary containing default DizqueTV channel configuration with:
        - number: Channel number
        - name: Channel name
        - programs: Empty list (populate with program dicts)
        - icon: Channel icon URL (empty by default)
        - disableFillerOverlay: False (show filler overlays)
        - startTime: 0 (start immediately)
        - offline: Offline mode configuration (clip mode by default)
        - fallback: Empty fallback content list
        - fillerCollections: Empty filler collections list
        - scheduleBackup: Empty schedule backup list
        - transcoding: Default transcoding settings
            - targetResolution: "1920x1080"
            - videoBitrate: 3000 kbps
            - videoBufSize: 1000
        - watermark: Watermark configuration (disabled by default)
            - enabled: False
            - width: 10%
            - margins: 1% vertical/horizontal
            - duration: 0 (always show)
            - fixedSize: False
            - position: "bottom-right"
            - url: Empty

    Example:
        from ToonamiTools.utils.DizqueTVHelpers import create_default_channel_settings

        # Create a new Toonami channel
        channel = create_default_channel_settings(101, "Toonami")

        # Customize settings
        channel['icon'] = 'https://example.com/toonami_logo.png'
        channel['transcoding']['videoBitrate'] = 5000  # Increase bitrate
        channel['watermark']['enabled'] = True
        channel['watermark']['url'] = 'https://example.com/watermark.png'

        # Add programs (created with create_program_dict_from_plex_item)
        channel['programs'].append(program1)
        channel['programs'].append(program2)
    """
```

**Usage in Pipeline:**
These helper functions are used by `PlexToDizqueTV` to convert Plex media items and lineup data into DizqueTV channel configurations. They abstract away the complexity of DizqueTV's data format and ensure consistency across the codebase.

**Best Practices:**
- Always use these helpers instead of manually constructing DizqueTV dictionaries
- Verify Plex server connectivity before calling `create_program_dict_from_plex_item`
- Customize channel settings after creation rather than modifying defaults
- For cutless mode, ensure start_time < end_time and both are within video duration

## ComBreak Module APIs

### CommercialBreakerLogic
```python
class CommercialBreakerLogic:
    def __init__(self):
        """Initialize commercial detection system"""
    
    def detect_commercials(self, input_paths: list, output_dir: str, **kwargs) -> None:
        """
        Detect commercial breaks in videos
        
        Args:
            input_paths: List of video file paths
            output_dir: Directory for timestamp files
            **kwargs: Mode flags (fast_mode, low_power_mode, etc.)
        """
    
    def cut_videos(self, input_paths: list, output_dir: str, **kwargs) -> None:
        """
        Cut videos at detected break points
        
        Args:
            input_paths: List of video file paths  
            output_dir: Directory for cut files
            **kwargs: Mode flags (destructive_mode, cutless_mode, etc.)
        """
```

### EnhancedInputHandler
```python
class EnhancedInputHandler:
    def __init__(self):
        """Initialize input management system"""
    
    def add_files(self, file_paths: list) -> None:
        """Add individual files to processing queue"""
    
    def add_folder(self, folder_path: str) -> None:
        """Add all videos in folder to processing queue"""
    
    def get_consolidated_paths(self) -> list:
        """Get unified list of all files to process"""
```

## Platform Integration APIs

### DizqueTV Integration
```python
class PlexToDizqueTV:
    def __init__(self, plex_url: str, plex_token: str, dizquetv_url: str, 
                 library_name: str):
        """Initialize DizqueTV channel creator"""
    
    def create_channel(self, lineup_table: str, channel_number: str) -> None:
        """Create channel from lineup table"""
```

### Tunarr Integration
```python
class PlexToTunarr:
    def __init__(self, plex_url: str, plex_token: str, tunarr_url: str,
                 library_name: str):
        """Initialize Tunarr channel creator"""

    def create_channel_with_flex(self, lineup_table: str, channel_number: str,
                                flex_duration: str) -> None:
        """Create channel with integrated flex scheduling"""
```

### ComBreakDirect Integration
```python
class ComBreakToComBreakDirect:
    def __init__(self, table: str | None, channel_number: int | None,
                 flex_duration: str | int | None, *,
                 network: str | None = None, base_url: str | None = None,
                 create_channel: bool = True, commercial_folder: str | None = None,
                 infinite: bool = False, infinite_meta: dict | None = None):
        """
        Initialize ComBreakDirect channel creator

        Args:
            table: Cutless lineup table name (e.g., "lineup_v8_cutless")
            channel_number: Channel number for the stream
            flex_duration: Commercial break length (milliseconds or "MM:SS")
            network: Network name (e.g., "Toonami")
            base_url: ComBreakDirect server URL
            create_channel: When False, only verify the server is reachable
            commercial_folder: Path to commercial break video files
            infinite: When True, include `infinite=True` and `infinite_meta`
                in the POST payload so LoadingDock arms a LineupExtender
                watchdog for the channel. Set by
                ``FrontEndLogic.create_toonami_channel`` for every
                ComBreakDirect channel.
            infinite_meta: Dict passed through to the channel's
                ``_infinite_meta`` block. Should contain
                ``toonami_version`` (key into ``TOONAMI_CONFIG_CONT``),
                ``cutless_enabled``, and optionally ``commercial_folder``.
        """

    def run(self) -> bool:
        """
        Push lineup to ComBreakDirect server:
        1. Wait for server health
        2. Load lineup rows via ``load_lineup_rows``
        3. If ``infinite=True``, call ``_seed_episode_cursor`` to populate
           ``last_used_episode_block`` from the initial lineup BEFORE POSTing
        4. POST payload to /channels endpoint
        """

    def _seed_episode_cursor(self, lineup: list[dict]) -> None:
        """
        Pre-populate ``last_used_episode_block`` from the initial channel's
        BLOCK_IDs so the very first extension picks up at E+1 of each show
        instead of treating the channel as a fresh ShowScheduler run.

        Show keys are derived via
        ``show_name_mapper.clean(show_name_mapper.map(name), mode='matching')``
        to match ShowScheduler's exact internal format. Existing cursor
        entries are merged with max-by-BLOCK_ID — never rolls a cursor
        backwards.
        """


def load_lineup_rows(table: str, db_manager=None) -> list[dict]:
    """
    Module-level helper. Load and normalize lineup rows from a SQLite
    lineup table. Shared by ComBreakToComBreakDirect (initial channel
    creation) and InfiniteChannelExtender (each extension chunk lives in
    its own table).

    Returns a list of normalized dicts:
        {block_id, file_path, code, start_time, end_time, duration}
    """


class InfiniteChannelExtender:
    """One-shot orchestrator that builds a single extension chunk.

    Called by ``ComBreakDirect.docks.LineupExtender`` whenever its timer
    fires. Runs ShowScheduler with ``continue_from_last_used_episode_block=True``
    against a per-extension SQLite table, then CutlessFinalizer for cutless
    channels, then returns the rows for LoadingDock to format.
    """

    def generate_chunk(self, channel_number: int,
                       infinite_meta: dict) -> tuple[list[dict], str | None]:
        """
        Build a new lineup chunk.

        Args:
            channel_number: Used in the per-extension table name to avoid
                cross-channel collisions.
            infinite_meta: The channel's ``_infinite_meta`` dict. Required
                key: ``toonami_version``. Optional: ``cutless_enabled``
                (default True), ``extension_seq`` (current count of
                completed extensions).

        Returns:
            (rows, output_table) where rows are in ``load_lineup_rows``
            shape. Returns ``([], output_table)`` when ShowScheduler
            produces an empty chunk (caller treats this as a soft failure
            and disables infinite mode).

        Raises:
            RuntimeError on configuration error, missing output table,
            or CutlessFinalizer failure.
        """
```

### ComBreakDirect Server-Side Infinite Extension
```python
class LineupExtender:
    """Per-channel ``threading.Timer``-based scheduler.

    Spawned by ``FactoryFloor._maybe_spawn_extender`` for any channel
    with ``_infinite_meta.enabled=True``. Arms a single timer for
    ``(channel_end - now) - INFINITE_EXTEND_LEAD_MS`` (clamped to 0), and
    reschedules itself after each extension.

    Wall-clock based — fires whether anyone is streaming or not.
    """

    DEFAULT_EXTEND_LEAD_MS = 3 * 60 * 60 * 1000  # 3 hours
    DEFAULT_MIN_FREE_DISK_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB
    RETRY_AFTER_FAILURE_MS = 5 * 60 * 1000  # 5 min
    MAX_CONSECUTIVE_FAILURES = 3

    def __init__(self, factory_floor: "FactoryFloor", channel_number: int):
        """Stores only the FactoryFloor reference (NOT LoadingDock — see
        the ``loading_dock`` property for the lazy-lookup rationale)."""

    @property
    def loading_dock(self):
        """Lazy lookup via ``self.factory_floor.loading_dock``. Avoids
        the bootstrap race where FactoryFloor.__init__ spawns watchdogs
        before LoadingDock.__init__ has finished assigning
        ``self.factory_floor``."""

    def start(self) -> None:
        """Compute the next extension time and arm the timer.
        Same name as the prior ``threading.Thread.start`` for backward
        compatibility with FactoryFloor's spawn site."""

    def cancel(self) -> None:
        """Cancel any pending timer. Idempotent."""

    def is_active(self) -> bool:
        """Whether a future extension is still scheduled."""


# FactoryFloor additions for infinite channels
class FactoryFloor:
    def extend_channel(self, channel_number: int,
                       new_programs: list[dict]) -> int | None:
        """Append-only growth path used by LineupExtender.

        Takes the factory lock, calls ``programs.extend(new_programs)``
        (never replaces or reorders — the Studio thread reads the same
        list reference live), bumps ``_infinite_meta.extension_seq``,
        stamps ``last_extension_at``, resets ``consecutive_failures``,
        persists ``channels.json``.

        Returns the new total program count, or ``None`` if the channel
        no longer exists (e.g., deleted between extension build and
        append).
        """

    def _maybe_spawn_extender(self, channel_data: dict) -> None:
        """Spawn a LineupExtender if the channel has
        ``_infinite_meta.enabled=True`` and FactoryFloor has a LoadingDock
        back-reference. Idempotent — won't double-spawn. Called by
        ``store_channel`` and ``_load_channels``."""


# LoadingDock additions for infinite extension
class LoadingDock:
    def format_extension(self, lineup_data: list[dict],
                         existing_channel_data: dict) -> list[dict]:
        """Format a lineup chunk as program dicts whose ``start``/``stop``
        ISO timestamps pick up immediately after the existing channel's
        last program. Used by LineupExtender to splice extension chunks
        onto a running channel without breaking timeline continuity.

        Reuses ``_inject_commercials`` (with the channel's saved
        ``flex_duration_ms``) and ``_format_programs`` (with anchor_time
        set to the existing tail's stop time).
        """

    def _format_programs(self, lineup_data: list[dict],
                         anchor_time: datetime) -> list[dict]:
        """Inner program-builder extracted from ``_format_for_streaming``
        so ``format_extension`` can reuse the timing/seek logic while
        anchoring at an arbitrary moment instead of "now"."""


# CutlessFinalizer addition for per-chunk finalization
class CutlessFinalizer:
    def run_for_table(self, input_table: str, output_table: str) -> bool:
        """Finalize a single lineup table to a specified cutless output
        table. Used by InfiniteChannelExtender to finalize one extension
        chunk without touching the rest of the project's lineup tables.

        Returns True on success, False on skip/failure (e.g., missing
        input table, validation failure, transient finalization error).
        Existing ``run()`` behavior is unchanged — it still scans every
        ``lineup_v*`` table when called with no args.
        """


# Merger fix — first-time continuation cursor init
# In ShowScheduler.__init__, when continue_from_last_used_episode_block=True
# AND the last_used_episode_block table does NOT exist, the dict is now
# initialized to {} (was previously left uninitialized, causing AttributeError
# on first call to get_next_episode_block). This is the fix for the documented
# "must run prepare twice the first time" quirk in the README FAQ.
```

## Configuration APIs

### FlagManager
```python
class FlagManager:
    @classmethod
    def evaluate_platform_compatibility(cls, platform_type: str, platform_url: str) -> None:
        """
        Evaluates whether cutless mode is compatible with the selected platform
        Updates cls.cutless flag accordingly
        """
    
    @classmethod  
    def register_cutless_callback(cls, callback: callable) -> None:
        """Register callback for cutless state changes"""
```

## Error Handling

### Common Exception Patterns

```python
try:
    logic.login_to_plex()
except PlexAuthenticationError as e:
    # Handle authentication failures
    pass
except NetworkError as e:
    # Handle network connectivity issues  
    pass
except Exception as e:
    # Handle unexpected errors
    logic._broadcast_status_update(f"Error: {str(e)}")
```

### Status Broadcasting

All major operations provide real-time status updates:

```python
# Status messages you might see:
"Logging in to Plex..."
"Plex login successful. Fetching servers..."
"Fetching libraries for ServerName..."
"Libraries fetched successfully!"
"Preparing bumps..."
"Content preparation complete!"
"Creating your lineup..."
"Channel creation complete!"
```

## Integration Examples

### TOM GUI Integration
```python
class Page1(ttk.Frame):
    def __init__(self, parent, controller, logic):
        self.logic = logic  # LogicController instance
        # Subscribe to updates via message broker
        self.logic.subscribe_to_updates('status_updates', self.update_status_label)
        self.logic.subscribe_to_updates('plex_servers', self.handle_plex_servers_update)
        self.logic.subscribe_to_updates('plex_libraries', self.handle_plex_libraries_update)
        self.logic.subscribe_to_updates('plex_auth_url', self.handle_plex_auth_url_update)
        self.logic.subscribe_to_updates('new_server_choices', self.handle_new_server_choices_update)
        self.logic.subscribe_to_updates('new_library_choices', self.handle_new_library_choices_update)
        # ...
```

### Absolution Web Interface Integration
```python
class Page1(BasePage):
    def __init__(self, app, *args, **kwargs):
        self.logic = LogicController()
        # Subscribe to updates via message broker
        self.logic.subscribe_to_status_updates(self.update_status_display)
        self.logic.subscribe_to_plex_servers(self.handle_plex_servers_update)
        self.logic.subscribe_to_plex_libraries(self.handle_plex_libraries_update)
        self.logic.subscribe_to_plex_auth_url(self.handle_plex_auth_url)
        self.logic.subscribe_to_server_choices(self.handle_new_server_choices)
        self.logic.subscribe_to_library_choices(self.handle_new_library_choices)
        # ...
```

### Clydes CLI Integration
```python
class ClydesApp:
    def __init__(self):
        self.logic = LogicController()
        self.logic.subscribe_to_updates('status_updates', self.handle_status_updates)
        self.logic.subscribe_to_updates('cutless_state', self.handle_cutless_state_update)
        # ...
```

This unified API design allows multiple user interfaces to provide identical functionality while maintaining consistent state and providing real-time feedback to users.

---

## Network Configuration API

Runtime network switching is supported across TOM, Absolution, and Clydes. The active network changes UI labels and the database file name (`<network>.db`). Validation checks Wikipedia for a broadcast list page.

**Networkless Mode**: Setting `network = "Networkless"` bypasses Wikipedia validation entirely, allowing use of any custom content collection without requiring a Wikipedia broadcast list page. When using Networkless mode, all bump files must be named with the "Networkless" prefix (e.g., `Networkless 2 0 ShowName back 4 red.mp4`).

### LogicController additions

```python
def validate_network(self, network_name: str) -> bool:
    """Validate against Wikipedia's list-of-programs pages; broadcasts status and error messages"""

def apply_network(self, network_name: str) -> bool:
    """Persist the network to config.py after validation and broadcast a 'restart required' status"""

def reset_network(self) -> bool:
    """Reset to 'Toonami' (calls apply_network)"""
```

- Behavior: `apply_network` rewrites `config.py` and UIs trigger a full process restart (re-exec) to load the new config consistently across modules.
- Status/Error handling: Uses the existing MessageBroker + ErrorManager channels so all UIs display uniform feedback.

### Module: `API/utils/NetworkManager.py`

```python
def validate_network_name(network_name: str) -> tuple[bool, str]:
    """Return (is_valid, message) by probing Wikipedia with a custom User-Agent.

    Special case: "Networkless" (case-insensitive) bypasses Wikipedia validation
    and returns True immediately, allowing use of all shows in the library.

    Tries these page patterns for standard networks:
    - List_of_programs_broadcast_by_<Network>
    - List_of_programs_broadcast_on_<Network>
    """

def update_config_network(config_path: str, new_network: str) -> None:
    """Rewrite the `network = "..."` line in config.py"""
```

Implementation notes:
- Uses urllib (HEAD with fallback to GET) with a custom `User-Agent` to avoid 403s.
- Multi-word names are supported (spaces converted to underscores only for page probing).
- **Networkless mode**: When `network_name.lower() == "networkless"`, validation is skipped and returns success immediately.
- If offline, callers can skip validation in CLI flows; UIs default to validation-first.
