# Developer Guide

This guide provides information for developers who want to contribute to CommercialBreaker & Toonami Tools or understand the codebase structure.

### Key Design Principles

1. **Single Source of Truth**: FrontEndLogic.LogicController manages all application state
2. **Interface Agnostic**: Same API works for GUI, web, and CLI interfaces
3. **Real-time Updates**: Status broadcasting keeps all UIs synchronized via the message broker
4. **Singleton DatabaseManager**: Centralized database access ensures thread safety and automatic retry logic
5. **Modular Architecture**: Components are organized into logical modules (ComBreak, ToonamiTools, etc.) and have a single purpose
6. **Background Processing**: Long operations run in threads with progress updates
7. **Status Bars Never Lie**: All status updates are broadcasted to all interfaces, ensuring users see real-time progress, we don't *estimate* completion times or provide false information
8. **Platform Compatibility**: Automatic evaluation of features like cutless mode

## Development Environment Setup

### Prerequisites

```bash
# Python 3.11+ required
python --version

# Install dependencies
pip install -r requirements.txt

# For GUI development (optional)
pip install -r requirements/graphics.txt
```

### Project Structure

```
CommercialBreaker/
├── main.py                 # Entry point - interface selection
├── API/                    # Orchestration and API modules
│   ├── FrontEndLogic.py    # Central orchestrator API (LogicController)
│   └── utils/              # Supporting utilities
│       ├── FlagManager.py      # Global flag management
│       ├── MessageBroker.py    # In-memory pub/sub for real-time updates
│       ├── DatabaseManager.py  # Thread-safe database operations
│       └── ErrorManager.py     # Centralized error handling and history
├── GUI/                    # User interfaces
│   ├── TOM.py              # Primary Tkinter GUI
│   ├── Absolution.py       # Web interface (REMI)
│   └── CommercialBreaker.py # Standalone GUI for ComBreak
├── CLI/                    # Command-line interfaces
│   ├── clydes.py           # Interactive CLI
│   └── CommercialBreakerCLI.py
├── ComBreak/               # Commercial detection system
│   ├── CommercialBreakerLogic.py   # Main orchestrator
│   ├── ChapterExtractor.py         # Chapter-based detection
│   ├── SilentBlackFrameDetector.py # Audio/video detection
│   ├── VideoCutter.py              # File cutting operations
│   ├── VirtualCut.py               # Cutless mode operations
│   └── ...
├── ToonamiTools/           # Toonami-specific automation
│   ├── utils/              # ToonamiTools utilities
│   │   └── ShowNameMapper.py   # Centralized show name mapping
│   ├── LoginToPlex.py      # Plex authentication
│   ├── toonamichecker.py   # Show validation
│   ├── commercialinjector.py # Bump insertion
│   └── ...
└── ExtraTools/             # Case use utilities
```

## Database Operations

All database access in CommercialBreaker uses the centralized `DatabaseManager` from `API.utils.DatabaseManager`. This ensures thread-safe operations and automatic retry logic for database locks.

### Getting the DatabaseManager

```python
from API.utils.DatabaseManager import get_db_manager

class MyModule:
    def __init__(self):
        self.db_manager = get_db_manager()
```

### Common Operations

```python
# Simple queries
result = self.db_manager.fetchone("SELECT * FROM table WHERE id = ?", (1,))
all_results = self.db_manager.fetchall("SELECT * FROM table")

# Insert data
self.db_manager.insert("table_name", {"column1": "value1", "column2": "value2"})

# Update data
self.db_manager.update("table_name", {"column1": "new_value"}, "id = ?", (1,))

# Delete data
self.db_manager.delete("table_name", "id = ?", (1,))

# Check if table exists
if self.db_manager.table_exists("my_table"):
    # Process table
```

### Using Transactions

For multiple operations that must succeed or fail together:

```python
with self.db_manager.transaction() as conn:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO table1 ...")
    cursor.execute("UPDATE table2 ...")
    # Automatically commits on success, rolls back on exception
```

### Working with Pandas

When using pandas DataFrames with the database:

```python
with self.db_manager.transaction() as conn:
    # Read data
    df = pd.read_sql("SELECT * FROM table", conn)
    
    # Process dataframe
    processed_df = process_data(df)
    
    # Write back to database
    processed_df.to_sql("processed_table", conn, if_exists="replace", index=False)
```

### Important Notes

1. **Never use `sqlite3.connect()` directly** - Always use `get_db_manager()`
2. **Thread Safety** - Each thread gets its own connection automatically
3. **Auto-retry** - Database locks are handled with exponential backoff
4. **Transactions** - Use the `transaction()` context manager for atomic operations
5. **Resource Cleanup** - Connections are managed automatically per thread

## Error Handling

All modules in CommercialBreaker must use the centralized `ErrorManager` for consistent error handling across all interfaces.

### Getting the ErrorManager

```python
from API.utils.ErrorManager import get_error_manager, ErrorLevel

class MyModule:
    def __init__(self):
        self.error_manager = get_error_manager()
```

### Basic Error Handling Pattern

```python
def process_file(self, file_path):
    try:
        # Validate inputs
        if not os.path.exists(file_path):
            self.error_manager.send_error(
                level=ErrorLevel.ERROR,
                source="MyModule",
                operation="process_file",
                message=f"File not found: {file_path}",
                details="The specified file does not exist",
                suggestion="Check the file path and ensure the file exists"
            )
            return None
            
        # Process file
        result = self._do_processing(file_path)
        
        # Success info
        self.error_manager.send_info(
            source="MyModule",
            operation="process_file",
            message=f"Successfully processed {file_path}"
        )
        
        return result
        
    except PermissionError as e:
        self.error_manager.send_error(
            level=ErrorLevel.ERROR,
            source="MyModule",
            operation="process_file",
            message=f"Permission denied: {file_path}",
            details=str(e),
            suggestion="Check file permissions or run with appropriate privileges"
        )
        
    except Exception as e:
        self.error_manager.send_critical(
            source="MyModule",
            operation="process_file",
            message=f"Unexpected error processing {file_path}",
            details=str(e),
            suggestion="Please report this error to the developers"
        )
        raise  # Re-raise for debugging
```

### Error Levels

- **CRITICAL**: System cannot continue (corrupted data, missing dependencies)
- **ERROR**: Operation failed but system stable (file not found, network error)
- **WARNING**: Operation degraded but continuing (using defaults, skipping optional)
- **INFO**: Important non-error information (completion notices, statistics)

### Integration with FrontEndLogic

When integrating modules with the orchestrator, errors are automatically handled:

```python
# In FrontEndLogic.py
def your_new_feature(self):
    def feature_thread():
        try:
            self._broadcast_status_update("Starting feature...")
            
            tool = YourNewTool()
            # Errors from the tool are automatically captured
            result = tool.run()
            
            self._broadcast_status_update("Feature completed!")
            
        except Exception as e:
            # Critical errors stop the operation
            self.error_manager.send_critical(
                source="LogicController",
                operation="your_new_feature",
                message="Feature failed",
                details=str(e)
            )
```

### Best Practices

1. **Always provide suggestions** for how users can resolve the error
2. **Use appropriate error levels** - don't use CRITICAL for recoverable errors
3. **Include context** in the operation parameter (method names)
4. **Keep messages user-friendly** - technical details go in the details field
5. **Don't spam errors** - the system includes rate limiting for repeated errors

For more details, see the Error Handling Guide.

## Show Name Mapping

ToonamiTools now includes a centralized `ShowNameMapper` utility that handles all show name normalization and mapping operations.

### Using ShowNameMapper

```python
from ToonamiTools.utils import show_name_mapper

# Basic mapping
mapped_name = show_name_mapper.map("Attack on Titan", strategy='all')

# Different strategies
first_match = show_name_mapper.map("One Piece", strategy='first_match')
first_only = show_name_mapper.map("Naruto", strategy='first')

# Clean text for different purposes
clean_for_matching = show_name_mapper.clean("ATTACK ON TITAN!", mode='matching')
clean_for_display = show_name_mapper.clean("attack on titan", mode='display')

# Convert to BLOCK_ID format
block_id = show_name_mapper.to_block_id("My Hero Academia")  # Returns "MY_HERO_ACADEMIA"

# Apply to filenames
filename = "Attack on Titan - S01E01.mkv"
mapped_filename = show_name_mapper.apply_to_filename(filename)
```

### Mapping Strategies

- **'all'**: Apply all three mapping dictionaries sequentially (default)
- **'first'**: Only use the first mapping dictionary
- **'first_match'**: Stop at the first dictionary that contains a match

### Cleaning Modes

- **'standard'**: Basic normalization (unidecode, lowercase, remove special chars)
- **'matching'**: For comparison (remove all non-alphanumeric, lowercase)
- **'display'**: For display (proper capitalization)

## Core Development Patterns

### 1. FrontEndLogic Integration

When adding new functionality, integrate with the orchestrator:

```python
# API/FrontEndLogic.py
class LogicController:
    def new_feature(self):
        def feature_thread():
            self._broadcast_status_update("Starting new feature...")
            
            # Your logic here
            tool = ToonamiTools.NewTool()
            result = tool.run()
            
            self._broadcast_status_update("Feature completed!")
            
        thread = threading.Thread(target=feature_thread)
        thread.start()
```

### 2. UI Implementation

All UIs should use the same LogicController API and subscribe to updates via the message broker:

```python
# For TOM (Tkinter)
class NewPage(ttk.Frame):
    def __init__(self, parent, controller, logic):
        self.logic = logic  # LogicController instance
        
        # Subscribe to updates via message broker
        self.logic.subscribe_to_updates('status_updates', self.update_status)
        
        # Button handler
        button = ttk.Button(self, command=self.logic.new_feature)

# For Absolution (Web)
class NewPage(BasePage):
    def __init__(self, app, *args, **kwargs):
        self.logic = LogicController()
        
        # Subscribe to updates via message broker
        self.logic.subscribe_to_status_updates(self.update_status_display)
        
        # Same API call
        button.onclick.connect(self.logic.new_feature)
```

### 3. Status Broadcasting

Provide user feedback for all operations using the message broker:

```python
def long_running_operation(self):
    self._broadcast_status_update("Initializing...")
    
    for i, item in enumerate(items):
        self._broadcast_status_update(f"Processing {i+1}/{len(items)}: {item}")
        # Process item
        
    self._broadcast_status_update("Operation completed!")
```

### 4. Error Handling

Use consistent error handling with user feedback:

```python
def risky_operation(self):
    try:
        self._broadcast_status_update("Starting operation...")
        # Risky code here
        self._broadcast_status_update("Operation successful!")
        
    except SpecificException as e:
        error_msg = f"Known error occurred: {str(e)}"
        self._broadcast_status_update(error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        self._broadcast_status_update(error_msg)
        raise  # Re-raise for debugging
```

## Module Development

### Adding New ToonamiTools

1. Create your tool class:

```python
# ToonamiTools/YourNewTool.py
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager, ErrorLevel
from .utils import show_name_mapper
import config

class YourNewTool:
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()
    
    def run(self):
        try:
            # Validate parameters
            if not self.param1:
                self.error_manager.send_error(
                    level=ErrorLevel.ERROR,
                    source="YourNewTool",
                    operation="run",
                    message="Missing required parameter",
                    suggestion="Provide param1 in configuration"
                )
                return None
            
            # Use DatabaseManager for all database operations
            with self.db_manager.transaction() as conn:
                df = pd.read_sql("SELECT * FROM shows", conn)
                
            # Use show_name_mapper for name normalization
            for show in shows:
                normalized = show_name_mapper.map(show, strategy='all')
                # Process normalized name
            
            return result
            
        except Exception as e:
            self.error_manager.send_critical(
                source="YourNewTool",
                operation="run",
                message="Tool execution failed",
                details=str(e)
            )
            raise
```

2. Add to ToonamiTools/__init__.py:

```python
from .YourNewTool import YourNewTool
```

3. Integrate with FrontEndLogic:

```python
# API/FrontEndLogic.py
def use_your_new_tool(self):
    def tool_thread():
        self._broadcast_status_update("Running your new tool...")
        
        param1 = self._get_data("some_config")
        param2 = self._get_data("other_config")
        
        tool = ToonamiTools.YourNewTool(param1, param2)
        result = tool.run()
        
        self._broadcast_status_update("Tool completed!")
        
    thread = threading.Thread(target=tool_thread)
    thread.start()
```

### Adding ComBreak Components

Follow the existing component architecture:

```python
# ComBreak/YourComponent.py
class YourComponent:
    def __init__(self, config_params):
        self.config = config_params
    
    def process(self, input_data):
        # Component-specific logic
        return processed_data
    
    def cleanup(self):
        # Resource cleanup
        pass
```

Integrate with CommercialBreakerLogic:

```python
# ComBreak/CommercialBreakerLogic.py
def enhanced_detection(self, files, output_dir):
    component = YourComponent(self.config)
    
    for file in files:
        result = component.process(file)
        # Handle result
    
    component.cleanup()
```

## Performance Considerations

### Threading Best Practices

1. **Long Operations**: Always run in background threads
2. **UI Updates**: Use broadcast messages, not direct UI manipulation
3. **Resource Management**: Implement proper cleanup in finally blocks

```python
def resource_intensive_operation(self):
    def operation_thread():
        resource = None
        try:
            self._broadcast_status_update("Acquiring resources...")
            resource = acquire_expensive_resource()
            
            self._broadcast_status_update("Processing...")
            result = process_with_resource(resource)
            
            self._broadcast_status_update("Operation completed!")
            
        except Exception as e:
            self._broadcast_status_update(f"Error: {str(e)}")
            
        finally:
            if resource:
                resource.cleanup()
    
    thread = threading.Thread(target=operation_thread)
    thread.start()
```

### Memory Management

1. **Large Files**: Process in chunks
2. **Temporary Files**: Clean up promptly
3. **Database Connections**: Handled automatically by DatabaseManager

```python
def process_large_file(self, file_path):
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)  # 8KB chunks
                if not chunk:
                    break
                process_chunk(chunk)
                
    except IOError as e:
        self._broadcast_status_update(f"File error: {e}")
```

## Platform Compatibility

### Cutless Mode Development

When adding features that support cutless mode:

```python
def feature_with_cutless_support(self):
    cutless_enabled = FlagManager.cutless
    
    if cutless_enabled:
        # Virtual processing path
        self.create_virtual_entries()
    else:
        # Traditional file processing path
        self.process_physical_files()
```

### Platform-Specific Code

Use the FlagManager for platform compatibility:

```python
def platform_specific_feature(self):
    platform_type = self._get_data("platform_type")
    
    if platform_type == "dizquetv":
        self.dizquetv_implementation()
    elif platform_type == "tunarr":
        self.tunarr_implementation()
    else:
        raise ValueError(f"Unsupported platform: {platform_type}")
```

## Debugging Guidelines

### Logging Best Practices

Use the broadcast system for user-visible logs:

```python
def debug_operation(self):
    self._broadcast_status_update("Debug: Starting operation")
    
    # For developer debugging
    print(f"Debug: Internal state = {self.internal_state}")
    
    # For user feedback
    self._broadcast_status_update("Processing step 1 of 3...")
```

### Common Debugging Scenarios

1. **Status Updates Not Appearing**: Check message broker subscription
2. **Threading Issues**: Ensure UI updates only via broadcasts
3. **Database Locks**: DatabaseManager handles retries automatically
4. **Platform Compatibility**: Verify FlagManager.cutless evaluation
5. **Show Name Issues**: Check ShowNameMapper mapping dictionaries

## Contribution Workflow

### Code Style

Follow Python conventions:
- Use type hints where practical
- Document classes and complex functions
- Keep methods focused and single-purpose
- Use descriptive variable names

### Pull Request Process

1. **Fork and Branch**: Create feature branch from main
2. **Implement**: Follow architecture patterns
3. **Test**: Add unit tests for new functionality
4. **Document**: Update relevant documentation
5. **Review**: Submit PR with clear description

### Documentation Updates

When adding features:
1. Update API-Reference.md for new orchestrator methods
2. Update Component-Documentation.md for new tools
3. Update User-Guides.md for new UI features
4. Add FAQ entries for common questions

## Testing Guide

### Testing with S.A.R.A.

S.A.R.A. is a comprehensive testing framework that validates the entire ToonamiTools workflow using simulated data.

### What S.A.R.A. Does

S.A.R.A. executes a complete workflow test that includes:
- Content preparation and filtering
- Simulated commercial detection using fake timestamps
- Cutless mode processing
- Database operations
- Complete Lineup creation logic

The test suite uses zero-byte files to simulate your media library structure, making it fast and resource-efficient while still testing all critical code paths.

### Running S.A.R.A.

To run the S.A.R.A. test suite, ensure you have `pytest` installed and execute the following command in your terminal from the root of the project:

```bash
pytest tests/test_sara_automatic.py -v
```

For more detailed output with S.A.R.A.'s transmission logs:

```bash
pytest tests/test_sara_automatic.py -v -s
```

### Setting Up Test Data

S.A.R.A. requires a `sample.txt` file that defines your simulated media library structure. This file should be placed at `tests/fixtures/sample.txt`.

#### Generating sample.txt

The `sample.txt` file contains a hierarchical listing of your media library structure. You can generate this from an existing media library:

**On macOS/Linux:**
```bash
# Navigate to your media library root
cd /path/to/your/media/library
# Generate the file listing
tree -fi > sample.txt
# Or if tree is not installed, use find:
find . -type f -name "*.mkv" | sort > sample.txt
```

**On Windows:**
```powershell
# PowerShell command
Get-ChildItem -Path "C:\path\to\your\media\library" -Recurse -File -Filter "*.mkv" | 
    ForEach-Object { $_.FullName.Replace("C:\path\to\your\media\library\", ".\") } | 
    Sort-Object | Out-File sample.txt
```

#### Sample Format

Your `sample.txt` should follow this format:

```
.
./Anime
./Anime/Death Note
./Anime/Death Note/Season 1
./Anime/Death Note/Season 1/Death Note - S01E01 - Rebirth.mkv
./Anime/Death Note/Season 1/Death Note - S01E02 - Confrontation.mkv
./Anime/Death Note/Season 1/Death Note - S01E03 - Dealings.mkv
./Anime/Attack on Titan/Season 1
./Anime/Attack on Titan/Season 1/Attack on Titan - S01E01 - To You, in 2000 Years - The Fall of Shiganshina (1).mkv
./Anime/Attack on Titan/Season 1/Attack on Titan - S01E02 - That Day - The Fall of Shiganshina (2).mkv
```

The fixture system (`conftest.py`) will automatically create zero-byte files matching this structure in a temporary directory during test execution.

### How S.A.R.A. Works

1. **Setup**: Creates a temporary file structure based on `sample.txt`
2. **Content Preparation**: Simulates content filtering and selection
3. **Commercial Detection**: Uses `FakeCommercialDetector` to generate realistic timestamp files
4. **Cut List Processing**: Tests the cutless mode workflow and verifies the final database entries
5. **Timing Information**: Records and reports the duration of each major step
6. **Cleanup**: Removes temporary files and resets state

### Test Coverage

S.A.R.A. validates:
- ✅ File system operations
- ✅ Database creation and queries
- ✅ Content filtering logic
- ✅ Commercial detection integration
- ✅ Cut list processing
- ✅ Error handling
- ✅ Final database state
- ✅ Status update propagation
- ✅ Multi-threaded operations

### Extending S.A.R.A.

To add new test scenarios:

1. Create additional test methods in `TestSaraAutomatic`
2. Use the `self._log_progress()` method for S.A.R.A.-themed logging
3. Leverage the existing fixtures and helper methods
4. Follow the pattern of checking status updates with `wait_for_status()`

Example:
```python
def test_specific_feature(self):
    self._log_progress("Testing specific feature...")
    # Your test logic here
    assert self.wait_for_status("Expected Status", "Feature Name", timeout=30)
```

### Troubleshooting

If S.A.R.A. tests fail:

1. Check that `sample.txt` exists and is properly formatted
2. Ensure you have write permissions in the test directory
3. Verify no leftover test databases exist though they should be cleaned up automatically
4. Run with `-s` flag to see detailed S.A.R.A. transmissions
5. Check for filename length limitations on your OS though S.A.R.A. should skip excessively long paths by default

### CI/CD Integration

S.A.R.A. is designed to run in CI/CD pipelines. The test suite:
- Requires no external dependencies beyond Python packages
- Creates and cleans up its own test data
- Provides clear pass/fail results clearly marked where the point of failure occurred

## Advanced Topics

### Custom UI Development

To create a new interface:

1. **Implement LogicController Integration with Error Handling**:
```python
class CustomInterface:
    def __init__(self):
        self.logic = LogicController()
        self.logic.subscribe_to_status_updates(self.handle_status)
        self.logic.subscribe_to_error_messages(self.handle_error)
        
        # UI elements for error display
        self.error_bar = None
    
    def handle_status(self, message):
        # Update your interface
        pass
    
    def handle_error(self, error_data):
        # Display error in your UI
        if self.error_bar:
            self.error_bar.show_error(error_data)
    
    def show_error_history(self):
        # Get error history from LogicController
        errors = self.logic.get_error_history()
        # Display in modal or dedicated view
```

2. **Add to main.py**:
```python
def main():
    parser.add_argument('--custom', action='store_true')
    
    if args.custom:
        from CustomInterface import run_custom_interface
        run_custom_interface()
```

This architecture enables flexible extension while maintaining consistency across the codebase.