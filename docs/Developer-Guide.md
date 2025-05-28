# Developer Guide

This guide provides information for developers who want to contribute to CommercialBreaker & Toonami Tools or understand the codebase structure.

## Architecture Overview

### Orchestrator Pattern

The codebase uses a central orchestrator pattern where `API/FrontEndLogic.py` serves as the API layer for all user interfaces:

```
```
┌─────────────────┬─────────────────┬─────────────────┐
│   TOM.py        │ Absolution.py   │   clydes.py     │
│   (Tkinter)     │ (Web/REMI)      │   (CLI)         │
└─────────┬───────┴─────────┬───────┴─────────┬───────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐      ┌──────────────────────────────┐
│        FrontEndLogic.py (Orchestrator/API)                  │      │   Supporting API Modules     │
│  • LogicController class                                    │======│ ───────────────────────────  │
│  • State management via SQLite                              │      │  FlagManager.py              │
│  • Threading for background operations                      │      │   • Platform compatibility   │
└─────────────────────────────────────────────────────────────┘      │   • Global flags             │
                         │                                           │  message_broker.py           │
                         ▼                                           │   • In-memory pub/sub        │
┌─────────────────────────────────────────────────────────────┐      │   • Real-time communication  │
│        ToonamiTools & ComBreak Modules (Core Logic)         │      └──────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```
*Supporting modules are used by FrontEndLogic for platform checks and real-time updates, but are not intermediary layers between the orchestrator and the core processing modules.*
```
*Supporting modules are used by FrontEndLogic for platform checks and real-time updates, but are not intermediary layers between the orchestrator and the core processing modules.*

### Key Design Principles

1. **Single Source of Truth**: FrontEndLogic.LogicController manages all application state
2. **Interface Agnostic**: Same API works for GUI, web, and CLI interfaces
3. **Real-time Updates**: Status broadcasting keeps all UIs synchronized via the message broker
4. **Background Processing**: Long operations run in threads with progress updates
5. **Platform Compatibility**: Automatic evaluation of features like cutless mode

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
│   └── components/         # Supporting components
│       ├── FlagManager.py      # Global flag management
│       └── MessageBroker.py    # In-memory pub/sub for real-time updates
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
│   ├── LoginToPlex.py      # Plex authentication
│   ├── toonamichecker.py   # Show validation
│   ├── commercialinjector.py # Bump insertion
│   └── ...
└── ExtraTools/             # Case use utilities
```

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
import sqlite3
import config

class YourNewTool:
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
        self.db_path = f'{config.network}.db'
    
    def run(self):
        # Your tool logic
        with sqlite3.connect(self.db_path) as conn:
            # Database operations
            pass
        
        return result
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
3. **Database Connections**: Use context managers

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

1. **Status Updates Not Appearing**: Check message broker configuration
2. **Threading Issues**: Ensure UI updates only via broadcasts
3. **Database Locks**: Use shorter connection contexts
4. **Platform Compatibility**: Verify FlagManager.cutless evaluation

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

## Advanced Topics

### Custom UI Development

To create a new interface:

1. **Implement LogicController Integration**:
```python
class CustomInterface:
    def __init__(self):
        self.logic = LogicController()
        self.logic.subscribe_to_status_updates(self.handle_status)
    
    def handle_status(self, message):
        # Update your interface
        pass
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
