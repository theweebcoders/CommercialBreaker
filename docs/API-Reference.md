# API Reference

This document provides detailed information about the internal APIs used throughout the CommercialBreaker & Toonami Tools system.

## FrontEndLogic Orchestrator API

The `LogicController` class in `GUI/FrontEndLogic.py` serves as the central orchestrator API for all user interfaces. It provides a unified interface for workflow management, state persistence, and real-time communication via an in-memory message broker.

### Core Architecture

```python
from GUI import LogicController

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

#### State Management API

**Database Operations**
```python
def _set_data(self, key: str, value: str) -> None:
    """Persist data to SQLite database"""

def _get_data(self, key: str) -> str | None:
    """Retrieve data from SQLite database"""
```

**Common State Keys**:
- `plex_url` - Plex server URL
- `plex_token` - Authentication token
- `selected_anime_library` - Source anime library name
- `selected_toonami_library` - Target Toonami library name
- `platform_type` - "dizquetv" or "tunarr"
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
    2. Executes LineupLogic for commercial injection planning
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
    2. Creates channel using PlexToDizqueTV or PlexToTunarr
    3. Handles channel numbering and flex timing
    4. Manages episode continuation logic
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
