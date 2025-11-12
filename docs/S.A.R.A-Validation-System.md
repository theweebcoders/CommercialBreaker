# S.A.R.A. Validation System

## Overview

The **S.A.R.A. (System Analysis and Reporting Assistant)** validation system provides comprehensive database validation for CommercialBreaker & Toonami Tools. It verifies the integrity of all pipeline steps, detects configuration issues, validates data quality, and ensures cross-table consistency.

S.A.R.A. follows the project's core philosophy: **"Validate everything, trust nothing."** Every pipeline step, database table, and processing decision is verified against expected rules and patterns.

### What S.A.R.A. Validates

- **Pipeline Completion**: Which steps have been executed and completed successfully
- **Data Integrity**: All database tables have correct structure, required columns, and valid data
- **Cross-Table Consistency**: References between tables are valid (shows match episodes, BLOCK_IDs exist, etc.)
- **Bump Placement Rules**: Lineup sequences follow correct Toonami bump placement patterns
- **Mode Compatibility**: Platform and mode settings are compatible (cutless mode, DizqueTV vs Tunarr)
- **File Existence**: Referenced files actually exist on disk
- **Configuration Validity**: Folder paths, platform selection, and processing modes are correctly configured

### When to Use S.A.R.A.

- **After Initial Setup**: Verify platform configuration and folder structure
- **After Content Preparation**: Check that all content was processed correctly
- **After Commercial Detection**: Verify break points were detected properly
- **Before Channel Creation**: Ensure database is ready for platform export
- **When Troubleshooting**: Diagnose issues when something doesn't work as expected
- **After Errors**: Understand what went wrong and get actionable suggestions

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    DatabaseValidator                        │
│               (Main Orchestration Layer)                    │
├─────────────────────────────────────────────────────────────┤
│ • Coordinates all validators                                │
│ • Runs full validation workflow                             │
│ • Consolidates issues intelligently                         │
│ • Broadcasts status updates                                 │
│ • Reports to ErrorManager                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    BaseValidator                            │
│            (Abstract Base for All Validators)               │
├─────────────────────────────────────────────────────────────┤
│ • Database access utilities                                 │
│ • Table existence checking                                  │
│ • Row counting and column validation                        │
│ • Bump vs anime detection (consistent with main tools)     │
│ • Mode detection (cutless vs traditional)                   │
│ • Platform detection (DizqueTV, Tunarr, ComBreakDirect)    │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Step Validators│ │  Integrity   │ │   Support    │
│  (18 total)   │ │ Validators   │ │  Components  │
│               │ │  (2 total)   │ │              │
├──────────────┤ ├──────────────┤ ├──────────────┤
│Phase 0:       │ │Lineup        │ │Validation    │
│ Platform Setup│ │Integrity     │ │Result        │
│• Platform     │ │              │ │              │
│• PlexAuth     │ │Referential   │ │Validation    │
│• FolderMaker  │ │Integrity     │ │Issue         │
│               │ │              │ │              │
│Phase 1:       │ │              │ │Validation    │
│ Prep Content  │ │              │ │Level         │
│• ToonamiCheck │ │              │ │              │
│• LineupPrep   │ │              │ │Pipeline      │
│• BumpEncoder  │ │              │ │Status        │
│• UncutEncoder │ │              │ │              │
│• Multilineup  │ │              │ │PhaseTracker  │
│• Merger       │ │              │ │              │
│• EpisodeFilter│ │              │ │              │
│               │ │              │ │              │
│Phase 2:       │ │              │ │              │
│ Commercial    │ │              │ │              │
│ Detection     │ │              │ │              │
│• CommercialBr │ │              │ │              │
│               │ │              │ │              │
│Phase 3:       │ │              │ │              │
│ Prep Cut      │ │              │ │              │
│ Lineup        │ │              │ │              │
│• ComInjPrep   │ │              │ │              │
│• ComInjector  │ │              │ │              │
│• BlockMaker   │ │              │ │              │
│• PostCutBump  │ │              │ │              │
│• BumpCalc     │ │              │ │              │
│• CutlessFinal │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Data Flow

```
User Initiates Validation (Page8, API call)
           │
           ▼
┌───────────────────────────────────┐
│   DatabaseValidator.              │
│   run_full_validation()           │
└───────────────┬───────────────────┘
                │
                ▼ For each validator...
┌───────────────────────────────────┐
│   Individual Validator.validate() │
│   • Check table existence         │
│   • Validate table structure      │
│   • Check data quality            │
│   • Verify relationships          │
│   • Detect platform/mode issues   │
└───────────────┬───────────────────┘
                │
                ▼ Returns ValidationResult
┌───────────────────────────────────┐
│   Consolidate Issues              │
│   • Group by (step, level)        │
│   • Version-based consolidation   │
│   • List-item consolidation       │
│   • Generic numbered list         │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│   Report to ErrorManager          │
│   • Broadcast to all interfaces   │
│   • User sees real-time updates   │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│   Return Validation Summary       │
│   • Pipeline status               │
│   • Issue counts by severity      │
│   • Actionable suggestions        │
│   • Completion percentage         │
└───────────────────────────────────┘
```

---

## Core Classes

### DatabaseValidator

**Location**: `/API/validators/DatabaseValidator.py`

The main orchestrator for all validation operations. Manages validator instances, coordinates validation workflow, consolidates issues, and provides high-level status checking.

**Key Methods:**

```python
def __init__(self, status_callback: Optional[Callable[[str], None]] = None):
    """
    Initialize the database validator.

    Args:
        status_callback: Optional callback for real-time status updates
    """
```

```python
def run_full_validation(self) -> Dict[str, Any]:
    """
    Run comprehensive validation of the entire database.

    Executes all 20 validators in pipeline order, consolidates issues,
    generates summary statistics, and broadcasts status updates.

    Returns:
        Dictionary containing:
            - results: List of ValidationResult objects
            - issues: Flat list of all ValidationIssue objects (consolidated)
            - summary: Summary statistics (completion %, issue counts)
            - pipeline_status: PipelineStatus object with phase info
            - timestamp: ISO format timestamp

    Example:
        >>> validator = DatabaseValidator(status_callback=print)
        >>> validation_data = validator.run_full_validation()
        >>> print(validation_data['summary']['summary_text'])
        "18/20 steps completed, 16/18 valid | 2 errors | 3 warnings"
    """
```

```python
def get_pipeline_status(self) -> PipelineStatus:
    """
    Get high-level status of the pipeline without full validation.

    Quick check to determine which steps have been completed.
    Uses each validator's has_completed() method for accurate detection.
    Includes phase-aware tracking.

    Returns:
        PipelineStatus object containing:
            - completed_steps: List of completed step names
            - current_step: Name of next incomplete step
            - is_cutless_mode: Boolean for cutless mode detection
            - total_steps: Total number of validators
            - metadata: Phase info, available versions, etc.

    Example:
        >>> status = validator.get_pipeline_status()
        >>> print(f"Pipeline: {status.completion_percentage():.1f}% complete")
        >>> print(f"Current step: {status.current_step}")
        >>> print(f"Mode: {'Cutless' if status.is_cutless_mode else 'Traditional'}")
    """
```

```python
def validate_specific_step(self, step_name: str) -> Optional[ValidationResult]:
    """
    Validate a specific pipeline step by name.

    Args:
        step_name: Name of the step to validate (e.g., "ToonamiChecker")

    Returns:
        ValidationResult for that step, or None if step not found

    Example:
        >>> result = validator.validate_specific_step("CommercialBreaker")
        >>> if not result.is_valid:
        >>>     print(f"Commercial detection has {len(result.issues)} issues")
    """
```

```python
def detect_processing_mode(self) -> Dict[str, Any]:
    """
    Detect the processing mode and platform from database state.

    Returns:
        Dict with keys:
            - mode: 'cutless' or 'traditional'
            - platform: 'DizqueTV', 'Tunarr', 'ComBreakDirect', or 'unknown'
            - confidence: 'high', 'medium', 'low'
            - indicators: List of evidence used for detection
            - warnings: List of compatibility warnings

    Example:
        >>> mode_info = validator.detect_processing_mode()
        >>> if mode_info['warnings']:
        >>>     for warning in mode_info['warnings']:
        >>>         print(f"Warning: {warning}")
    """
```

**Issue Consolidation:**

DatabaseValidator intelligently consolidates multiple related issues to prevent overwhelming the user with repetitive error messages. Three consolidation strategies are used:

1. **Version-Based Consolidation**: Issues from CutlessFinalizer that follow "Version X: error" pattern
2. **List-Item Consolidation**: Similar issues (missing folders, files) consolidated with bullet points
3. **Generic Consolidation**: Other multiple issues shown as numbered list

---

### BaseValidator

**Location**: `/API/validators/BaseValidator.py`

Abstract base class that all step validators inherit from. Provides common utilities, enforces consistent interface, and ensures validators follow the same patterns.

**Abstract Properties (Must Be Implemented):**

```python
@property
@abstractmethod
def step_name(self) -> str:
    """
    Human-readable name of the pipeline step.
    Example: "ToonamiChecker", "LineupPrep", "BumpEncoder"
    """

@property
@abstractmethod
def required_tables(self) -> List[str]:
    """
    List of database tables that MUST exist for this step to be considered complete.
    Example: ["Toonami_Episodes", "Toonami_Shows"]
    """

@abstractmethod
def validate(self) -> ValidationResult:
    """
    Run validation for this pipeline step.
    Returns: ValidationResult containing status, issues, and metadata
    """
```

**Optional Properties:**

```python
@property
def optional_tables(self) -> List[str]:
    """
    Tables that MAY exist (mode-dependent or optional features).
    Default: empty list
    """

@property
def pipeline_order(self) -> int:
    """
    Position in pipeline (1-20). Used for ordering validation results.
    Default: 999 (end of pipeline)
    """

def has_completed(self) -> bool:
    """
    Check if this pipeline step has completed.
    Default implementation checks if required_tables exist with data.
    Override for custom completion logic (e.g., dynamic table detection).
    """
```

**Common Validation Utilities:**

```python
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

def validate_table_structure(self, result: ValidationResult, table_name: str,
                            required_columns: List[str], min_rows: int = 1) -> bool:
    """
    Common validation pattern: check table exists, has required columns, and minimum rows.
    Adds issues to result if validation fails.
    Returns True if all checks pass.
    """
```

**Bump Detection (Consistent with Main Tools):**

```python
def is_bump(self, file_path: str) -> bool:
    """
    Check if file path represents a bump (not anime).
    Uses same logic as EpisodeFilter, LineupPrep, Plex modules.
    """

def is_anime(self, file_path: str) -> bool:
    """
    Check if file path represents anime episode (not a bump).
    Inverse of is_bump() for readability.
    """
```

**Mode and Platform Detection:**

```python
def is_cutless_mode(self) -> bool:
    """
    Detect if database is using cutless mode.
    Checks for cutless-specific tables and timing columns.
    """

def get_processing_metadata(self) -> Dict[str, Any]:
    """
    Get cached processing metadata (platform, mode, flags).
    Returns:
        - platform: 'dizquetv', 'tunarr', 'combreakdirect', or 'unknown'
        - is_cutless: bool
        - mode: 'cutless' or 'traditional'
        - requires_bump_calculator: bool (cutless + ComBreakDirect)
    """

def get_available_versions(self) -> List[int]:
    """
    Get list of Toonami versions that have data in database.
    Returns: List of version numbers (e.g., [2, 3, 8, 9])
    """
```

**Issue Management:**

```python
def create_result(self, is_completed: bool = False, is_valid: bool = True) -> ValidationResult:
    """Create a ValidationResult for this step with default values"""

def add_issue(self, result: ValidationResult, level: ValidationLevel,
             message: str, details: str, suggestion: str,
             table: Optional[str] = None, row_index: Optional[int] = None):
    """Add a validation issue to a result"""

def add_info(self, result: ValidationResult, message: str):
    """Add an informational message to validation result"""
```

---

### ValidationResult

**Location**: `/API/validators/ValidationResult.py`

Represents the result of validating a single pipeline step.

**Structure:**

```python
@dataclass
class ValidationResult:
    step_name: str                           # Which step was validated
    is_valid: bool                           # Overall pass/fail status
    is_completed: bool                       # Whether step has been run
    issues: List[ValidationIssue]            # All validation issues found
    metadata: Dict[str, Any]                 # Additional info (row counts, etc.)
```

**Key Methods:**

```python
def add_issue(self, issue: ValidationIssue):
    """
    Add a validation issue to this result.
    Automatically sets is_valid=False if ERROR or CRITICAL issue added.
    """

def get_issues_by_level(self, level: ValidationLevel) -> List[ValidationIssue]:
    """Get all issues of a specific severity level"""

def get_issue_counts(self) -> Dict[str, int]:
    """
    Get counts of issues by severity level.
    Returns: {'critical': 0, 'error': 2, 'warning': 5, 'info': 3}
    """

def get_status_symbol(self) -> str:
    """
    Get a visual symbol for overall status.
    Returns: ○ (not run), ✗ (failed), ⚠ (warning), ✓ (success)
    """

def get_status_description(self) -> str:
    """
    Get human-readable status description.
    Examples:
        - "Not completed"
        - "Failed: 2 critical issue(s)"
        - "Completed with 3 warning(s)"
        - "Completed successfully"
    """
```

---

### ValidationIssue

**Location**: `/API/validators/ValidationResult.py`

Represents a single validation issue. Follows the **five components of good errors**:

1. **Where**: `step`, `table`, `row_index`
2. **What**: `message` (user-friendly description)
3. **Why**: `details` (technical explanation)
4. **How to fix**: `suggestion` (actionable guidance)
5. **When**: `timestamp`

**Structure:**

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
```

**Example Issues:**

```python
# CRITICAL issue - step cannot proceed
ValidationIssue(
    level=ValidationLevel.CRITICAL,
    step="ToonamiChecker",
    message="Table 'Toonami_Episodes' does not exist",
    details="The ToonamiChecker step has not created this required table",
    suggestion="Run ToonamiChecker to create this table",
    table="Toonami_Episodes"
)

# ERROR issue - data quality problem
ValidationIssue(
    level=ValidationLevel.ERROR,
    step="CommercialBreaker",
    message="Episode missing commercial break timestamps",
    details="File: Naruto - S01E05.mkv has no timestamps in cuts table",
    suggestion="Re-run CommercialBreaker with normal mode (not low power)",
    table="cuts"
)

# WARNING issue - non-critical but should be addressed
ValidationIssue(
    level=ValidationLevel.WARNING,
    step="LineupIntegrity",
    message="Multibump not followed by anime",
    details="Row 42: 'Toonami 2 0 Now Naruto Next Bleach...' → Generic bump",
    suggestion="This may affect lineup flow. Check bump placement rules.",
    table="lineup_v2"
)

# INFO issue - useful information
ValidationIssue(
    level=ValidationLevel.INFO,
    step="LineupIntegrity",
    message="Episode repeated in lineup",
    details="Naruto - S01E05 appears 3 times in lineup",
    suggestion="This may be intentional for marathon format"
)
```

---

### ValidationLevel

**Location**: `/API/validators/ValidationResult.py`

Enumeration of severity levels for validation issues.

```python
class ValidationLevel(Enum):
    INFO = "INFO"           # ℹ  Informational message
    WARNING = "WARNING"     # ⚠  Should be addressed but not critical
    ERROR = "ERROR"         # ✗  Significant problem, step may fail
    CRITICAL = "CRITICAL"   # ⊗  Step cannot proceed, must be fixed
```

**Level Meanings:**

- **INFO**: Useful information that doesn't indicate a problem (e.g., "3 versions detected", "Cutless mode active")
- **WARNING**: Non-critical issues that should be reviewed (e.g., "Episode repeated 3 times", "Unusual bump placement")
- **ERROR**: Significant problems that will likely cause processing to fail (e.g., "Missing required columns", "Invalid BLOCK_ID format")
- **CRITICAL**: Fatal issues that prevent the step from functioning (e.g., "Required table does not exist", "Zero episodes found")

---

### PipelineStatus

**Location**: `/API/validators/ValidationResult.py`

Overall status of the entire Toonami Tools pipeline, providing a high-level view of progress.

**Structure:**

```python
@dataclass
class PipelineStatus:
    completed_steps: List[str]      # Names of completed steps
    current_step: Optional[str]     # Next incomplete step
    is_cutless_mode: bool           # Cutless mode detected
    total_steps: int                # Total number of validators
    metadata: Dict[str, Any]        # Phase info, versions, etc.
```

**Key Methods:**

```python
def completion_percentage(self) -> float:
    """Calculate percentage of pipeline completed (0-100)"""
```

**Metadata Contents:**

```python
{
    "available_versions": [2, 3, 8, 9],
    "phase_info": {
        "completed_phase": 1,
        "completed_phase_name": "Prepare Content",
        "status": "complete",
        "automated": True
    },
    "version_status": {
        "phase_1_uncut": [2, 3, 8, 9],
        "phase_3_cut": [2, 3, 8, 9]
    }
}
```

---

### PhaseTracker

**Location**: `/API/validators/PhaseTracker.py`

Tracks pipeline progress through logical workflow phases. Maps individual step validators to broader phases and provides phase-aware status information.

**Phase Definitions:**

- **Phase 0 (Platform Setup)**: PlatformSelection, PlexAuth, FolderMaker
- **Phase 1 (Prepare Content)**: ToonamiChecker, LineupPrep, BumpEncoder, UncutEncoder, Multilineup, Merger, EpisodeFilter
- **Phase 2 (Commercial Detection)**: CommercialBreaker (GetPlexTimestamps remains an optional tool outside of S.A.R.A.)
- **Phase 3 (Prepare Cut Lineup)**: CommercialInjectorPrep, CommercialInjector, BlockMaker, PostCutBumpFilter, BumpCalculator, CutlessFinalizer

**Note**: Optional tools (ExtraBumps, PlexAutoSplitter, PlexSplitRenamer) and platform export steps (PlexToDizqueTV, PlexToTunarr, ComBreakToComBreakDirect, FlexInjector) occur after validation and are not tracked as phases.

**Key Methods:**

```python
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
    """
    Get human-readable summary for a phase.
    Includes completion status and step checklist.
    """
```

---

## Step Validators (18 Total)

All step validators inherit from `BaseValidator` and validate a specific pipeline step's output.

### Phase 0: Platform Setup

#### PlatformSelectionValidator
**Location**: `/API/validators/steps/PlatformSelectionValidator.py`
**Pipeline Order**: 0
**Required Tables**: `app_data`

**Validates:**
- Platform type is set in app_data (DizqueTV, Tunarr, or ComBreakDirect)
- Platform selection is valid
- Platform is compatible with other settings (e.g., cutless mode requires DizqueTV)

#### PlexAuthValidator
**Location**: `/API/validators/steps/PlexAuthValidator.py`
**Pipeline Order**: 1
**Required Tables**: `app_data`
**Conditional**: Only required for DizqueTV and Tunarr platforms

**Validates:**
- Plex authentication token exists in app_data
- Token is non-empty
- Platform compatibility (skipped for ComBreakDirect)

#### FolderMakerValidator
**Location**: `/API/validators/steps/FolderMakerValidator.py`
**Pipeline Order**: 2
**Required Tables**: `app_data`

**Validates:**
- All required folder paths are configured in app_data
- Folder paths are non-empty
- Folders actually exist on disk
- Folders are accessible (read/write permissions)

**Required Folders:**
- ANIME_FOLDER_PATH
- BUMPS_FOLDER_PATH
- WORKING_FOLDER_PATH
- SPECIAL_BUMPS_FOLDER_PATH (optional)

---

### Phase 1: Prepare Content

This phase combines content discovery (ToonamiChecker) with uncut lineup preparation (LineupPrep through EpisodeFilter).

#### ToonamiCheckerValidator
**Location**: `/API/validators/steps/ToonamiCheckerValidator.py`
**Pipeline Order**: 3
**Required Tables**: `Toonami_Episodes`, `Toonami_Shows`

**Validates:**
- Tables exist with required columns
- Tables have data (at least 1 episode, 1 show)
- Episode files follow naming convention (SxxExx pattern)
- File paths are properly stored
- Show/episode relationship is valid (all shows have episodes)
- Episodes are anime (not bumps)

**Data Quality Checks:**
- Missing file paths
- Invalid naming patterns
- Missing show titles
- Shows without episodes

---

#### LineupPrepValidator
**Location**: `/API/validators/steps/LineupPrepValidator.py`
**Pipeline Order**: 4
**Required Tables**: `lineup_prep_out`

**Validates:**
- Table has required columns (FULL_FILE_PATH, PLACEMENT_2, BLOCK_ID, etc.)
- All entries are bumps (not anime episodes)
- Placement types are valid (back, to ads, intro, generic, etc.)
- BLOCK_IDs follow correct format (UPPERCASE_WITH_UNDERSCORES)
- File paths reference actual bump files
- Version assignments are correct

#### BumpEncoderValidator
**Location**: `/API/validators/steps/BumpEncoderValidator.py`
**Pipeline Order**: 5
**Required Tables**: `lineup_prep_out`

**Validates:**
- All bumps have Code assigned (encoding complete)
- Code format is valid (e.g., "GUN_BAC" format)
- No duplicate codes within same version
- Code matches BLOCK_ID and placement type

#### UncutEncoderValidator
**Location**: `/API/validators/steps/UncutEncoderValidator.py`
**Pipeline Order**: 6
**Required Tables**: `uncut_content_v{X}` (version-specific)

**Validates:**
- Tables exist for each version with bump data
- All anime episodes have uncut entries
- BLOCK_IDs are assigned correctly
- Episode sequence is maintained
- No bumps appear in uncut content (anime only)

#### MultilineupValidator
**Location**: `/API/validators/steps/MultilineupValidator.py`
**Pipeline Order**: 7
**Required Tables**: `multibumps_v{X}_data`, `multibumps_v{X}_data_reordered`

**Validates:**
- Tables exist for versions with multi-show bumps
- Data tables have required columns
- Reordered tables have correct sequence
- Multi-show bumps (2-show, 3-show) are properly categorized
- Show names in bump codes match configured shows

#### MergerValidator
**Location**: `/API/validators/steps/MergerValidator.py`
**Pipeline Order**: 8
**Required Tables**: `lineup_v{X}_uncut`, `lineup_v{X}` (or `lineup_v{X}_cutless`)

**Validates:**
- Uncut lineups exist for all versions (Phase 1)
- Cut lineups exist for all versions (Phase 3, after commercial detection)
- Cutless lineups exist (lineup_vX_cutless) whenever cutless mode is active
- Lineups have both anime and bumps interleaved
- Sequence numbers are valid and continuous
- BLOCK_IDs are consistent across lineup

**Note**: Merger runs twice - once for uncut content (Phase 1), once for cut content (Phase 3)

#### EpisodeFilterValidator
**Location**: `/API/validators/steps/EpisodeFilterValidator.py`
**Pipeline Order**: 9
**Required Tables**: `pure_anime_episodes`

**Validates:**
- Table exists with anime episodes only (no bumps)
- All entries are actual anime (SxxExx pattern)
- File paths are valid
- Episodes match those from ToonamiChecker
- No bump files leaked through

---

### Phase 2: Commercial Detection

#### CommercialBreakerValidator
**Location**: `/API/validators/steps/CommercialBreakerValidator.py`
**Pipeline Order**: 11
**Required Tables**: `cuts`, `file_path_log`

**Validates:**
- Cuts table exists with timestamp data
- All anime episodes have commercial break points detected
- Timestamps are valid (positive, increasing order)
- Detection method is recorded (chapter, silence, plex)
- No episodes are missing from detection
- Timestamp gaps are reasonable (actual commercial breaks, not false positives)

---

### Phase 3: Prepare Cut Lineup

#### CommercialInjectorPrepValidator
**Location**: `/API/validators/steps/CommercialInjectorPrepValidator.py`
**Pipeline Order**: 12
**Required Tables**: `commercial_injector_prep`
**Mode Dependent**: Traditional mode only (skipped in cutless mode)

**Validates:**
- Table exists with cut episode segments
- Segments have correct naming (_part1, _part2, etc.)
- Start and end times are valid
- No timing overlaps within same episode
- Segment order is correct

#### CommercialInjectorValidator
**Location**: `/API/validators/steps/CommercialInjectorValidator.py`
**Pipeline Order**: 13
**Required Tables**: `commercial_injector_final`

**Validates:**
- Table has episode segments with BLOCK_IDs
- BLOCK_IDs are valid format
- File paths reference correct segments
- Episode sequence is maintained
- No missing segments between parts

#### BlockMakerValidator
**Location**: `/API/validators/steps/BlockMakerValidator.py`
**Pipeline Order**: 14
**Required Tables**: `commercial_injector_final`

**Validates:**
- All entries have BLOCK_IDs assigned
- BLOCK_IDs follow naming convention
- Show names are normalized correctly
- No episodes missing BLOCK_IDs

#### PostCutBumpFilterValidator
**Location**: `/API/validators/steps/PostCutBumpFilterValidator.py`
**Pipeline Order**: 14a (optional step)
**Required Tables**: `lineup_prep_out_postcut`

**Validates:**
- If postcut bump filtering was run, table exists
- Postcut bumps are properly categorized
- No anime episodes in postcut bump table

#### BumpCalculatorValidator
**Location**: `/API/validators/steps/BumpCalculatorValidator.py`
**Pipeline Order**: 16a
**Required Tables**: `bump_durations`
**Mode Dependent**: Cutless mode + ComBreakDirect only

**Validates:**
- Table exists with bump duration data
- All bumps have duration calculated
- Durations are positive and reasonable
- Required for ComBreakDirect platform in cutless mode

#### CutlessFinalizerValidator
**Location**: `/API/validators/steps/CutlessFinalizerValidator.py`
**Pipeline Order**: 16
**Required Tables**: `lineup_v{X}_cutless`
**Mode Dependent**: Cutless mode only

**Validates:**
- Cutless lineup tables exist for all versions
- Tables have timing columns (startTime, endTime)
- Original file paths are preserved
- Start times are non-negative
- End times are greater than start times
- BLOCK_IDs are assigned correctly
- Timing data is complete (no nulls)

---

## Integrity Validators (2 Total)

Integrity validators perform cross-table validation to ensure data consistency across the entire database.

### LineupIntegrityValidator

**Location**: `/API/validators/integrity/LineupIntegrityValidator.py`
**Pipeline Order**: 20
**Required Tables**: Dynamic (checks for `lineup_v{X}`)

**Validates Bump Placement Rules:**

1. **Multibumps → Anime**: Bumps with Code (multi-show bumps) must be followed by anime
2. **Intro → Anime**: Intro bumps must be followed by anime with same BLOCK_ID
3. **Back → Anime**: "Back" bumps must be followed by anime
4. **Anime → To Ads**: "To ads" bumps must be preceded by anime
5. **Chain Continuity**: Lineup sequence follows logical flow
6. **Version Consistency**: Bumps match version in lineup

**Placement Rule Examples:**

✅ **Correct:**
```
[Multibump: Now Naruto Next Bleach] → [Naruto S01E05]
[Naruto intro bump] → [Naruto S01E05]
[Naruto S01E05] → [Naruto back bump]
[Naruto S01E05] → [Naruto to ads bump]
```

❌ **Incorrect:**
```
[Multibump: Now Naruto Next Bleach] → [Generic bump]  # Should be anime
[Naruto intro bump] → [Bleach S01E01]  # Wrong show
[Bleach back bump] → [Naruto S01E05]  # Back before anime
```

---

### ReferentialIntegrityValidator

**Location**: `/API/validators/integrity/ReferentialIntegrityValidator.py`
**Pipeline Order**: 21
**Required Tables**: Dynamic (checks relationships across tables)

**Validates Cross-Table Consistency:**

1. **Episodes in lineup exist in Toonami_Episodes**: No orphaned episodes
2. **BLOCK_IDs in lineup exist in lineup_prep_out**: All bumps are defined
3. **Show names are consistent**: Same show has same BLOCK_ID across tables
4. **File paths are consistent**: Same file doesn't have conflicting metadata
5. **Version assignments match**: Bumps in lineup_v2 are version 2 bumps

---

## Helper Utilities

### Bump Detection Functions

**Location**: `/API/validators/utils/helpers.py`

These functions ensure validators use the **same logic** as main processing tools (EpisodeFilter, LineupPrep, Plex modules) for bump vs anime detection.

```python
def is_bump(file_path: str) -> bool:
    """
    Check if file path represents a bump (not anime).

    Logic:
    1. Files with SxxExx pattern are anime (always)
    2. Files starting with network name (e.g., "Toonami") are bumps
    3. Files matching generic bump keywords are bumps
    4. Everything else is anime

    Examples:
        >>> is_bump("/app/bump/Toonami 2 0 Naruto back 4.mp4")
        True
        >>> is_bump("/app/anime/Naruto - S01E05 - Episode Title.mkv")
        False
    """

def is_anime(file_path: str) -> bool:
    """
    Check if file path represents anime episode (not a bump).
    Inverse of is_bump() for readability.
    """

def is_generic_bump(file_path: str) -> bool:
    """
    Check if file path represents a generic bump.
    Generic bumps can appear anywhere without violating placement rules.
    """
```

### Validation Constants

**Location**: `/API/validators/utils/config.py`

```python
# BLOCK_ID pattern: UPPERCASE_WITH_UNDERSCORES
BLOCK_ID_PATTERN = re.compile(r'^[A-Z_]+$')

# Generic bump keywords
GENERIC_BUMP_KEYWORDS = [
    "generic", "robot", "show lineup", "toonami game review",
    "tom", "sara", "absolution", "space", "stars"
]

# Version indicators for bump file detection
VERSION_INDICATORS = {
    2: ["moltar", "ghost planet"],
    3: ["tom 3", "tom3"],
    8: ["tom 4", "tom4"],
    9: ["tom 5", "tom5"]
}

# Timestamp tolerance for float comparison (seconds)
TIMESTAMP_TOLERANCE_SEC = 0.1
```

---

## Integration with FrontEndLogic

The validation system integrates with the main application through `LogicController` in `API/FrontEndLogic.py`.

**Methods Added:**

```python
def run_full_validation(self):
    """
    Run comprehensive database validation.

    Creates DatabaseValidator with status callback for real-time updates.
    Runs validation in background thread.
    Broadcasts results through message broker.
    """
    def validation_thread():
        try:
            validator = DatabaseValidator(
                status_callback=lambda msg: self._broadcast_status_update(msg)
            )

            validation_results = validator.run_full_validation()

            # Broadcast completion
            self._broadcast_status_update("Validation complete!")

        except Exception as e:
            self.error_manager.send_critical(
                source="LogicController",
                operation="run_full_validation",
                message="Validation failed",
                details=str(e)
            )

    thread = threading.Thread(target=validation_thread)
    thread.start()

def get_pipeline_status(self) -> PipelineStatus:
    """
    Get quick pipeline status without full validation.

    Returns PipelineStatus object with completion info.
    Used by UI to show progress indicators.
    """
    validator = DatabaseValidator()
    return validator.get_pipeline_status()
```

---

## Page8 Diagnostics Interface

S.A.R.A. validation is accessed through **Page8** in both TOM (Tkinter) and Absolution (REMI) interfaces.

### Accessing Page8

**Three Methods:**

1. **Navigation Menu**: Select "S.A.R.A. Diagnostics" from interface menu
2. **Panic Button**: Click any page title **5 times in 2 seconds** (hidden feature for quick access)
3. **Direct API Call**: `logic_controller.run_full_validation()`

### Page8 Features

**Pipeline Status Section:**
- Shows which steps have been completed (✓ or ✗)
- Displays current processing phase (0-6)
- Shows completion percentage
- Indicates cutless vs traditional mode
- Lists available Toonami versions

**Validation Controls:**
- **Run Full Validation**: Execute comprehensive validation
- **Refresh Status**: Update pipeline status without full validation
- **Copy All Results**: Copy validation results to clipboard (for bug reports)

**Validation Results Display:**
- Shows issues grouped by severity (CRITICAL, ERROR, WARNING, INFO)
- Each issue shows:
  - Which step found the issue
  - User-friendly message
  - Technical details
  - Actionable suggestion
- Collapsible sections (in Absolution) for better readability
- Real-time updates during validation

### Hidden Panic Button

**Implementation Details:**

The panic button is a **hidden diagnostic access feature** implemented across all interface pages (except Page5 in TOM due to layout complexity).

**How It Works:**
1. User clicks on page title label
2. System tracks click count and timestamps
3. If 5 clicks occur within 2 seconds → navigate to Page8
4. If more than 2 seconds pass between clicks → counter resets

**Why It Exists:**

Provides quick access to diagnostics:
- Emergency access when critical error breaks navigation
- Quick validation without navigating through menus
- Fast access without memorizing menu structure

**Code Pattern (TOM):**

```python
def add_panic_button_to_label(self, label, clicks_needed=5, time_window=2.0):
    """
    Add panic button functionality to a label.

    Args:
        label: Tkinter Label widget
        clicks_needed: Number of clicks required (default: 5)
        time_window: Time window in seconds (default: 2.0)
    """
    label.click_count = 0
    label.last_click_time = 0

    def on_label_click(event):
        current_time = time.time()
        if current_time - label.last_click_time > time_window:
            label.click_count = 0

        label.click_count += 1
        label.last_click_time = current_time

        if label.click_count >= clicks_needed:
            label.click_count = 0
            self.show_page("Page8")

    label.bind("<Button-1>", on_label_click)
```

---

## Usage Examples

### Running Full Validation from Python

```python
from API.validators.DatabaseValidator import DatabaseValidator

# Create validator with status callback
def status_update(message):
    print(f"[VALIDATION] {message}")

validator = DatabaseValidator(status_callback=status_update)

# Run full validation
results = validator.run_full_validation()

# Check summary
summary = results['summary']
print(f"Completion: {summary['completion_percentage']:.1f}%")
print(f"Issues: {summary['critical_count']} critical, {summary['error_count']} errors")

# Examine issues
for issue_dict in results['issues']:
    if issue_dict['level'] in ['CRITICAL', 'ERROR']:
        print(f"\n{issue_dict['level']} in {issue_dict['step']}")
        print(f"  Message: {issue_dict['message']}")
        print(f"  Suggestion: {issue_dict['suggestion']}")
```

### Getting Quick Pipeline Status

```python
from API.validators.DatabaseValidator import DatabaseValidator

validator = DatabaseValidator()
status = validator.get_pipeline_status()

print(f"Pipeline {status.completion_percentage():.1f}% complete")
print(f"Current step: {status.current_step}")
print(f"Mode: {'Cutless' if status.is_cutless_mode else 'Traditional'}")
print(f"Completed steps: {', '.join(status.completed_steps)}")

# Check phase information
phase_info = status.metadata.get('phase_info', {})
if phase_info:
    print(f"\nCurrent phase: {phase_info.get('current_phase_name', 'Unknown')}")
    print(f"Phase status: {phase_info.get('status', 'Unknown')}")
```

### Validating Specific Step

```python
from API.validators.DatabaseValidator import DatabaseValidator

validator = DatabaseValidator()

# Validate only CommercialBreaker
result = validator.validate_specific_step("CommercialBreaker")

if result:
    if result.is_completed:
        if result.is_valid:
            print("✓ Commercial detection completed successfully")
        else:
            print(f"✗ Commercial detection has {len(result.issues)} issues:")
            for issue in result.issues:
                print(f"  - {issue.message}")
    else:
        print("○ Commercial detection not run yet")
else:
    print("Step not found")
```

### Detecting Processing Mode

```python
from API.validators.DatabaseValidator import DatabaseValidator

validator = DatabaseValidator()
mode_info = validator.detect_processing_mode()

print(f"Mode: {mode_info['mode']}")
print(f"Platform: {mode_info['platform']} (confidence: {mode_info['confidence']})")

if mode_info['indicators']:
    print("\nEvidence:")
    for indicator in mode_info['indicators']:
        print(f"  • {indicator}")

if mode_info['warnings']:
    print("\nWarnings:")
    for warning in mode_info['warnings']:
        print(f"  ⚠ {warning}")
```

### Creating Custom Validator

```python
from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel

class MyCustomValidator(BaseValidator):
    """Validates my custom processing step"""

    @property
    def step_name(self) -> str:
        return "MyCustomStep"

    @property
    def required_tables(self) -> list:
        return ["my_custom_table"]

    @property
    def pipeline_order(self) -> int:
        return 99  # End of pipeline

    def validate(self) -> ValidationResult:
        result = self.create_result(is_completed=False, is_valid=True)

        # Check table existence
        if not self.validate_table_structure(
            result,
            "my_custom_table",
            required_columns=["id", "data"],
            min_rows=1
        ):
            return result

        result.is_completed = True

        # Custom validation logic
        rows = self.get_all_rows("my_custom_table")
        for i, row in enumerate(rows):
            data = row.get("data", "")
            if not data:
                self.add_issue(
                    result,
                    ValidationLevel.ERROR,
                    f"Row {i} missing data",
                    f"Found empty data field at row {i}",
                    "Ensure all rows have valid data",
                    table="my_custom_table",
                    row_index=i
                )

        return result
```

---

## Testing Validation System

### Test File Location

**Location**: `/tests/test_validator_scenarios.py`

Comprehensive test suite for all validators including:
- Database mutation testing
- Platform compatibility scenarios
- Missing table detection
- Issue consolidation testing
- Cross-table validation

### Running Validator Tests

```bash
# Run all validator tests
pytest tests/test_validator_scenarios.py -v

# Run specific test
pytest tests/test_validator_scenarios.py::test_commercial_breaker_validation -v

# Run with detailed output
pytest tests/test_validator_scenarios.py -v -s
```

### Test Patterns

**1. Table Mutation Testing:**

Tests create incomplete/invalid data scenarios to ensure validators detect issues.

```python
def test_missing_table():
    """Test validator detects missing required table"""
    db_manager = get_db_manager()

    # Ensure table doesn't exist
    db_manager.execute("DROP TABLE IF EXISTS Toonami_Episodes")

    # Run validator
    validator = ToonamiCheckerValidator()
    result = validator.validate()

    # Should be marked incomplete
    assert not result.is_completed
    assert not result.is_valid

    # Should have critical issue
    critical_issues = result.get_issues_by_level(ValidationLevel.CRITICAL)
    assert len(critical_issues) > 0
    assert "does not exist" in critical_issues[0].message
```

**2. Data Quality Testing:**

Tests verify validators catch data quality issues.

```python
def test_invalid_episode_naming():
    """Test validator detects episodes without SxxExx pattern"""
    db_manager = get_db_manager()

    # Create table with invalid naming
    db_manager.execute("""
        CREATE TABLE Toonami_Episodes (
            Title TEXT,
            Full_File_Path TEXT
        )
    """)
    db_manager.execute("""
        INSERT INTO Toonami_Episodes VALUES
        ('Naruto', '/anime/Naruto - Episode 5.mkv')  -- Missing SxxExx
    """)

    validator = ToonamiCheckerValidator()
    result = validator.validate()

    # Should have warning about naming
    warnings = result.get_issues_by_level(ValidationLevel.WARNING)
    assert any("non-standard naming" in w.message for w in warnings)
```

**3. Cross-Table Validation Testing:**

Tests ensure referential integrity validators work correctly.

```python
def test_orphaned_block_ids():
    """Test validator detects BLOCK_IDs in lineup that don't exist in lineup_prep"""
    db_manager = get_db_manager()

    # Create lineup with unknown BLOCK_ID
    db_manager.execute("""
        INSERT INTO lineup_v2 (FULL_FILE_PATH, BLOCK_ID)
        VALUES ('/anime/Naruto.mkv', 'UNKNOWN_SHOW')
    """)

    validator = ReferentialIntegrityValidator()
    result = validator.validate()

    # Should detect orphaned BLOCK_ID
    errors = result.get_issues_by_level(ValidationLevel.ERROR)
    assert any("BLOCK_ID" in e.message and "not found" in e.details for e in errors)
```

---

## Troubleshooting

### Common Validation Errors

#### "Table does not exist" (CRITICAL)

**Cause**: Step has not been run yet, or step failed to create table.

**Solution**:
1. Check which step is failing by looking at step name
2. Run that step from the interface
3. Check error history for failures during that step
4. If step completed but table still missing, check database path configuration

#### "Table has insufficient data" (ERROR)

**Cause**: Step created table but didn't populate it with data.

**Solution**:
1. Re-run the step to repopulate data
2. Check that input folders contain required files
3. For episode/show tables: ensure anime library has properly named files
4. For bump tables: ensure bump folders contain Toonami bumps

#### "Missing required columns" (ERROR)

**Cause**: Table schema is outdated or corrupted.

**Solution**:
1. Re-run the step to rebuild table with correct schema
2. If issue persists, may need to delete table and recreate:
   ```python
   from API.utils.DatabaseManager import get_db_manager
   db = get_db_manager()
   db.execute("DROP TABLE IF EXISTS table_name")
   # Then re-run the step
   ```

#### "Cutless mode active but platform is Tunarr" (WARNING)

**Cause**: Platform incompatibility - Tunarr doesn't support cutless mode.

**Solution**:
1. Change platform to DizqueTV (requires custom fork) or ComBreakDirect
2. Or disable cutless mode and re-run content preparation
3. Note: Cutless mode only works with DizqueTV (custom fork) and ComBreakDirect

#### "Stale cutless/traditional tables detected" (WARNING)

**Cause**: Database contains tables from previous run with different mode.

**Solution**:
1. These are old tables from previous processing
2. Can be safely ignored if not using that mode
3. Or delete stale tables:
   ```sql
   DROP TABLE IF EXISTS lineup_v2_cutless;
   DROP TABLE IF EXISTS lineup_v3_cutless;
   -- etc.
   ```

#### "Multibump not followed by anime" (WARNING)

**Cause**: Lineup placement rule violation.

**Solution**:
1. Check if this is in uncut vs cut lineup
2. Re-run Merger to rebuild lineup with correct placement
3. May indicate issue with bump preparation or episode filtering

### Validation Performance

**Full Validation Time:**
- Small database (1-2 shows): ~2-5 seconds
- Medium database (5-10 shows): ~5-15 seconds
- Large database (20+ shows): ~15-30 seconds

**Quick Status Check Time:**
- Any database size: <1 second

**When to Use Full Validation vs Quick Status:**
- **Full Validation**: After completing major steps, before channel creation, when troubleshooting
- **Quick Status**: Frequent progress checks, UI updates, monitoring completion

---

## Development Notes

### Adding New Validators

When adding a new pipeline step, create a corresponding validator:

1. **Create validator file**: `/API/validators/steps/YourStepValidator.py`
2. **Inherit from BaseValidator**
3. **Implement required properties**: `step_name`, `required_tables`, `pipeline_order`
4. **Implement validate() method**
5. **Add to DatabaseValidator._initialize_validators()**
6. **Write tests**: Add test cases to `/tests/test_validator_scenarios.py`

**Template:**

```python
from API.validators.BaseValidator import BaseValidator
from API.validators.ValidationResult import ValidationResult, ValidationLevel

class YourStepValidator(BaseValidator):
    """Validates YourStep output"""

    @property
    def step_name(self) -> str:
        return "YourStep"

    @property
    def required_tables(self) -> list:
        return ["your_table"]

    @property
    def pipeline_order(self) -> int:
        return 10  # Choose appropriate order

    def validate(self) -> ValidationResult:
        result = self.create_result(is_completed=False, is_valid=True)

        # Validate table structure
        if not self.validate_table_structure(
            result,
            "your_table",
            required_columns=["col1", "col2"],
            min_rows=1
        ):
            return result

        result.is_completed = True

        # Add custom validation logic here

        return result
```

### Validation Philosophy

**Key Principles:**

1. **Read-Only**: Validators NEVER modify data, only read and analyze
2. **Non-Intrusive**: Validation can run at any time without affecting processing
3. **Comprehensive**: Check structure, data quality, and relationships
4. **Actionable**: Every issue includes a suggestion for how to fix it
5. **Consistent**: Use same logic as main tools (especially for bump detection)
6. **Performance**: Cache metadata, avoid redundant queries
7. **User-Friendly**: Clear messages, grouped issues, avoid technical jargon

**Error Message Quality:**

Every validation issue must have:
- **Clear Message**: User understands what's wrong without being a developer
- **Technical Details**: Developer can debug if needed
- **Actionable Suggestion**: User knows exactly what to do next
- **Context**: Which step, table, and row (if applicable)

❌ **Bad Error:**
```
"Invalid data"
```

✅ **Good Error:**
```
Message: "3 episodes missing commercial break timestamps"
Details: "Files: Naruto S01E05.mkv, Naruto S01E06.mkv, Bleach S02E03.mkv"
Suggestion: "Re-run CommercialBreaker in normal mode (not low power) to detect breaks"
```

### Integration Points

**Error Manager:**
- All validation issues are reported to ErrorManager
- Broadcasts to all interfaces in real-time
- Allows users to see validation progress

**Message Broker:**
- Status updates broadcast through message broker
- UI subscribes to updates for progress display
- Enables real-time feedback during validation

**Database Manager:**
- All database access through DatabaseManager singleton
- Thread-safe operations
- Schema refresh before cross-thread checks

**Phase Tracker:**
- Maps validators to logical workflow phases
- Provides high-level progress information
- Helps users understand "where am I in the pipeline"

---

## See Also

- [Architecture Overview](Architecture-Overview.md) - System architecture with validation layer
- [API Reference](API-Reference.md) - Complete API documentation including validation APIs
- [Error Handling Guide](Error-Handling-Guide.md) - Error management patterns used by validators
- [Developer Guide](Developer-Guide.md) - Development patterns and best practices
- [Troubleshooting](Troubleshooting.md) - Common issues and solutions
