# Error History System

## Overview

The error history system allows users to view previously displayed error messages even after they have been dismissed. This is useful for troubleshooting and debugging when error messages are cleared quickly or when users need to reference past errors.

## Features

### Error Storage
- Stores the last 100 error messages in memory
- Includes all error details: level, source, operation, message, timestamp, details, and suggestions
- Automatically managed with a circular buffer (oldest errors are removed when limit is reached)

### Error Levels
- **CRITICAL**: Severe errors that may require immediate attention
- **ERROR**: Standard errors that need resolution
- **WARNING**: Warnings that should be noted but may not require immediate action
- **INFO**: Informational messages

### Filtering Options
- Filter by error level (CRITICAL, ERROR, WARNING, INFO)
- Filter by source component
- Limit the number of results returned
- Get most recent errors

## User Interface

### Error Bar Enhancements
The error bar now includes a history button (📋) that allows users to:
- View all past error messages
- Filter errors by level
- Clear the entire error history
- See error summaries

### Error History Modal
The error history modal provides:
- Chronological list of all errors (most recent first)
- Color-coded display based on error level
- Detailed information for each error including timestamp, source, operation, and suggestions
- Filter dropdown to show only specific error levels

## API Reference

### ErrorManager Methods

#### `get_error_history(level_filter=None, source_filter=None, limit=None)`
Get error history with optional filtering.

**Parameters:**
- `level_filter` (str, optional): Filter by error level
- `source_filter` (str, optional): Filter by source component  
- `limit` (int, optional): Maximum number of errors to return

**Returns:**
- List of error dictionaries

#### `get_recent_errors(count=10)`
Get the most recent N errors.

**Parameters:**
- `count` (int): Number of recent errors to retrieve

**Returns:**
- List of recent error dictionaries

#### `get_errors_by_level(level)`
Get all errors of a specific level.

**Parameters:**
- `level` (str): Error level to filter by

**Returns:**
- List of error dictionaries

#### `get_critical_errors()`
Get all critical errors.

**Returns:**
- List of critical error dictionaries

#### `clear_error_history()`
Clear the entire error history.

#### `get_error_summary()`
Get a summary of errors by level.

**Returns:**
- Dictionary with error counts by level

### LogicController Methods

The LogicController exposes the same methods as ErrorManager with additional error handling:

- `get_error_history(level_filter=None, source_filter=None, limit=None)`
- `get_recent_errors(count=10)`
- `get_errors_by_level(level)`
- `get_critical_errors()`
- `clear_error_history()`
- `get_error_summary()`

## Usage Examples

### Generating Errors
```python
from API.utils.ErrorManager import get_error_manager, ErrorLevel

error_manager = get_error_manager()

# Send a critical error
error_manager.send_critical(
    source="MyModule",
    operation="FileOperation",
    message="Critical file system error",
    details="Unable to write to disk",
    suggestion="Check disk space and permissions"
)

# Send a warning
error_manager.send_warning(
    source="MyModule", 
    operation="ConfigLoad",
    message="Configuration file not found, using defaults"
)
```

### Retrieving Error History
```python
from API import LogicController

logic = LogicController()

# Get all errors
all_errors = logic.get_error_history()

# Get only critical errors
critical_errors = logic.get_critical_errors()

# Get recent 5 errors
recent_errors = logic.get_recent_errors(5)

# Get error summary
summary = logic.get_error_summary()
print(f"Critical: {summary['CRITICAL']}, Errors: {summary['ERROR']}")
```

### GUI Integration
The error history is automatically integrated into the Absolution page template. Users can:

1. Click the 📋 button in the error bar to view history
2. Filter errors by level using the dropdown
3. Close the modal with the ✕ button

## Implementation Details

### Memory Management
- Uses `collections.deque` with `maxlen=100` for efficient circular buffer
- Automatic cleanup of oldest errors when limit is reached
- Minimal memory footprint with structured error data

### Thread Safety
- Error storage is thread-safe through the MessageBroker system
- All error operations go through the centralized ErrorManager
- No direct manipulation of error history from multiple threads

### Performance
- O(1) insertion of new errors
- O(n) filtering operations where n is the number of stored errors
- Efficient JSON serialization for UI data transfer

## Future Enhancements

Potential improvements for the error history system:
- Persistent storage to disk for error history across sessions
- Export functionality for error logs
- Advanced filtering options (date range, regex patterns)
- Error grouping and deduplication
- Integration with external logging systems
