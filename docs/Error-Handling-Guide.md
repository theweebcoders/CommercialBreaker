# Error Handling Guide

This guide provides best practices and examples for using the error messaging infrastructure in CommercialBreaker & Toonami Tools.

## Overview

The error messaging system provides a unified way to communicate errors, warnings, and important information to users across all interfaces (GUI, Web, CLI). It ensures consistent error presentation while maintaining clean architecture and avoiding circular dependencies.

## Error Levels

The system supports four error levels:

1. **CRITICAL**: System cannot continue (missing dependencies, corrupted database)
   - Automatically stops current operation
   - Clears operation queue
   - Resets UI state
   - Example: Database corruption, missing critical files

2. **ERROR**: Operation failed but system stable (file not found, API error)
   - Operation fails but system remains functional
   - Example: Network timeout, invalid file format

3. **WARNING**: Operation degraded but continuing (using defaults, missing optional data)
   - Operation continues with reduced functionality
   - Example: Using default values, skipping optional steps

4. **INFO**: Important non-error information
   - System status updates
   - Example: Operation completed, configuration loaded

## Using ErrorManager

### Basic Usage

```python
from API.utils.ErrorManager import get_error_manager

class MyTool:
    def __init__(self):
        self.error_manager = get_error_manager()
    
    def process_file(self, filename):
        try:
            # Process file
            if not os.path.exists(filename):
                self.error_manager.send_error(
                    level="ERROR",
                    source="MyTool",
                    operation="process_file",
                    message=f"File not found: {filename}",
                    details="The specified file does not exist in the expected location",
                    suggestion="Check the file path and ensure the file exists"
                )
                return
        except Exception as e:
            self.error_manager.send_critical(
                source="MyTool",
                operation="process_file",
                message=f"Unexpected error processing {filename}",
                details=str(e)
            )
```

### Convenience Methods

The ErrorManager provides convenience methods for each error level:

```python
# Critical error
error_manager.send_critical(
    source="MyTool",
    operation="process_file",
    message="Database connection failed",
    details="Could not connect to SQLite database",
    suggestion="Check database file permissions and disk space"
)

# Error level
error_manager.send_error_level(
    source="MyTool",
    operation="process_file",
    message="Invalid file format",
    details="File is not a valid video format",
    suggestion="Convert file to MP4 or MKV format"
)

# Warning
error_manager.send_warning(
    source="MyTool",
    operation="process_file",
    message="Using default settings",
    details="Configuration file not found",
    suggestion="Create config.json to customize settings"
)

# Info
error_manager.send_info(
    source="MyTool",
    operation="process_file",
    message="Processing complete",
    details="Successfully processed 100 files"
)
```

## Best Practices

### 1. Error Message Structure

- **Source**: Use the component/module name
- **Operation**: Use the specific function/method name
- **Message**: Clear, concise description of the issue
- **Details**: Technical details for debugging
- **Suggestion**: Actionable steps to resolve the issue

### 2. Error Level Selection

- Use **CRITICAL** only for system-stopping issues
- Use **ERROR** for operation failures
- Use **WARNING** for degraded functionality
- Use **INFO** for status updates

### 3. Thread Safety

- ErrorManager is thread-safe through MessageBroker
- No need for additional synchronization
- Can be used from any thread

### 4. Rate Limiting

- FrontEndLogic automatically rate limits repeated errors
- 5-second cooldown between identical errors
- Prevents error message spam

## Error Recovery

### 1. Critical Error Handling

When a critical error occurs:
1. Current operation is stopped
2. Operation queue is cleared
3. UI state is reset
4. System returns to ready state

### 2. Operation Thread Management

Long-running operations should:
1. Check `self._should_stop` periodically
2. Clean up resources on exit
3. Handle exceptions properly

Example:
```python
def long_operation(self):
    try:
        for item in items:
            if self._should_stop:
                self.error_manager.send_warning(
                    source="MyTool",
                    operation="long_operation",
                    message="Operation stopped by user"
                )
                return
            # Process item
    finally:
        # Cleanup
        self._cleanup_resources()
```

## UI Integration

### 1. TOM (Tkinter)

```python
class MyPage(ttk.Frame):
    def __init__(self, parent, controller, logic):
        self.logic = logic
        self.logic.subscribe_to_error_messages(self.handle_error)
    
    def handle_error(self, error_data):
        # Update UI with error message
        self.status_label.configure(
            text=error_data['message'],
            foreground=self.get_error_color(error_data['level'])
        )
```

### 2. Absolution (Web)

```python
class MyPage(BasePage):
    def __init__(self, app, *args, **kwargs):
        self.logic = LogicController()
        self.logic.subscribe_to_error_messages(self.handle_error)
    
    def handle_error(self, error_data):
        # Update web UI with error message
        self.error_div.style['display'] = 'block'
        self.error_div.style['background-color'] = self.get_error_color(error_data['level'])
        self.error_message.set_text(error_data['message'])
```

### 3. Clydes (CLI)

```python
class MyCLI:
    def __init__(self):
        self.logic = LogicController()
        self.logic.subscribe_to_error_messages(self.handle_error)
    
    def handle_error(self, error_data):
        # Print colored error message
        color = self.get_error_color(error_data['level'])
        print(f"{color}[{error_data['level']}] {error_data['message']}{Style.RESET_ALL}")
```

## Common Error Patterns

### 1. File Operations

```python
def process_file(self, filename):
    try:
        if not os.path.exists(filename):
            self.error_manager.send_error(
                source="FileProcessor",
                operation="process_file",
                message=f"File not found: {filename}",
                details="The specified file does not exist",
                suggestion="Check the file path and permissions"
            )
            return
    except PermissionError:
        self.error_manager.send_error(
            source="FileProcessor",
            operation="process_file",
            message=f"Permission denied: {filename}",
            details="Insufficient permissions to access the file",
            suggestion="Run with elevated privileges or check file permissions"
        )
```

### 2. Network Operations

```python
def fetch_data(self, url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        self.error_manager.send_error(
            source="DataFetcher",
            operation="fetch_data",
            message=f"Request timed out: {url}",
            details="Server did not respond within 10 seconds",
            suggestion="Check network connection and server status"
        )
    except requests.HTTPError as e:
        self.error_manager.send_error(
            source="DataFetcher",
            operation="fetch_data",
            message=f"HTTP error: {url}",
            details=f"Server returned {e.response.status_code}",
            suggestion="Verify the URL and server status"
        )
```

### 3. Database Operations

```python
def update_database(self, query, params):
    try:
        self.db_manager.execute(query, params)
    except sqlite3.OperationalError as e:
        self.error_manager.send_critical(
            source="DatabaseManager",
            operation="update_database",
            message="Database operation failed",
            details=str(e),
            suggestion="Check database schema and connection"
        )
```

## Testing Error Handling

### 1. Unit Tests

```python
def test_error_handling(self):
    error_manager = get_error_manager()
    
    # Test error sending
    error_manager.send_error(
        level="ERROR",
        source="TestTool",
        operation="test_operation",
        message="Test error",
        details="Test details",
        suggestion="Test suggestion"
    )
    
    # Verify error was published
    error_data = self.message_broker.get_last_message('error_messages')
    self.assertEqual(error_data['level'], "ERROR")
    self.assertEqual(error_data['message'], "Test error")
```

### 2. Integration Tests

```python
def test_critical_error_recovery(self):
    # Start long operation
    self.logic.start_operation()
    
    # Simulate critical error
    self.error_manager.send_critical(
        source="TestTool",
        operation="test_operation",
        message="Test critical error"
    )
    
    # Verify operation was stopped
    self.assertFalse(self.logic._current_operation_thread.is_alive())
    self.assertTrue(self.logic._should_stop)
```

## Troubleshooting

### 1. Common Issues

- **Missing Error Messages**: Check if ErrorManager is properly initialized
- **Duplicate Messages**: Check rate limiting settings
- **UI Not Updating**: Verify subscription to error messages
- **Thread Not Stopping**: Ensure `_should_stop` is checked periodically

### 2. Debugging Tips

- Use `send_info()` for debugging messages
- Check error message format in UI
- Verify error level appropriateness
- Monitor error rate limiting

## Future Enhancements

1. Error persistence to database
2. Error analytics and reporting
3. Automatic error recovery actions
4. Error message internationalization
5. Error message templates
6. Error message search and filtering 