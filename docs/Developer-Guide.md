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
9. **Explicit Restart on Config Changes**: When changing `config.network`, UIs re‑exec the process to ensure a clean reload

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
│       ├── ErrorManager.py     # Centralized error handling and history
│       ├── NetworkManager.py   # Network validation & config persistence
│       ├── PlexClient.py       # Custom Plex OAuth and account client
│       ├── PlexServer.py       # Lightweight Plex Media Server client
│       └── PlexConnectionHelper.py # Smart connection retry logic
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

## Plex Client Architecture

CommercialBreaker includes a Plex client implementation that uses minimal dependencies and provides reliable connection handling through smart retry logic.

### Architecture Overview

The Plex integration consists of three main components:

1. **PlexClient.py** - OAuth authentication and account management
2. **PlexServer.py** - Minimal Plex Media Server client
3. **PlexConnectionHelper.py** - Smart connection retry logic

### Design Rationale

- **Minimal Dependencies**: Uses Python stdlib `urllib` and `CurlHttpClient`
- **Focused Implementation**: Only includes features actually used by CommercialBreaker
- **Connection Reliability**: Smart retry logic automatically tries all available URLs (local, relay, direct)
- **Stability**: Direct control over Plex API interactions
- **Performance**: Lightweight implementation with minimal overhead

### Component Details

#### PlexClient.py

Handles Plex authentication and account management:

```python
from API.utils.PlexClient import PlexAuthClient, PlexAccountClient

# OAuth authentication
auth_client = PlexAuthClient()
auth_url, pin_id = auth_client.start_auth()
# User visits auth_url and approves

# Poll for token
token = auth_client.poll_for_token(pin_id)

# Account management
account = PlexAccountClient(token)
resources = account.get_resources()  # Returns list of PlexResource objects

for resource in resources:
    if resource.provides == 'server':
        print(f"Server: {resource.name}")
        print(f"  Connections: {resource.connections}")
```

**Key Classes:**
- `PlexAuthClient`: Handles OAuth PIN flow
- `PlexAccountClient`: Manages account operations and server discovery
- `PlexResource`: Represents Plex servers/devices with connection info

#### PlexServer.py

Minimal Plex Media Server client with only needed functionality:

```python
from API.utils.PlexServer import SimplePlexServer

# Connect to server
server = SimplePlexServer(base_url, token)

# Get libraries
libraries = server.get_libraries()

# Get library sections
for library in libraries:
    sections = library.get_sections()
    for section in sections:
        print(f"Section: {section.title}")

        # Get shows
        shows = section.get_shows()
        for show in shows:
            # Get episodes
            episodes = show.get_episodes()
```

**Key Classes:**
- `SimplePlexServer`: Main server interface
- `SimplePlexLibrary`: Library container
- `SimplePlexSection`: Library section (TV Shows, Movies, etc.)
- `SimplePlexShow`: TV show with episode access
- `SimplePlexEpisode`: Individual episode with metadata

#### PlexConnectionHelper.py

Smart connection logic with automatic URL retry:

```python
from API.utils.PlexConnectionHelper import PlexConnectionHelper

# Initialize helper
helper = PlexConnectionHelper(token)

# Smart connect - tries all URLs automatically
server = helper.connect_smart(plex_resource)
# Returns SimplePlexServer or None if all connections fail

# Connect by server name
server = helper.connect_with_server_name(server_name)
# Discovers server, tries all URLs, returns working connection
```

**Connection Strategy:**
1. Try local network URLs first (fastest)
2. Fall back to direct connections
3. Use relay URLs as last resort
4. Returns first successful connection
5. Logs all attempts for debugging

### Usage in ToonamiTools

The custom Plex client is integrated throughout ToonamiTools:

```python
# In LoginToPlex.py
from API.utils.PlexClient import PlexAuthClient, PlexAccountClient
from API.utils.PlexConnectionHelper import PlexConnectionHelper

# Authenticate
auth_client = PlexAuthClient()
token = auth_client.get_token()

# Get servers with smart connection
helper = PlexConnectionHelper(token)
server = helper.connect_with_server_name(server_name)

# Use server
libraries = server.get_libraries()
```

### Migration from plexapi

**Old Code:**
```python
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

account = MyPlexAccount(token)
server = account.resource(server_name).connect()
```

**New Code:**
```python
from API.utils.PlexConnectionHelper import PlexConnectionHelper

helper = PlexConnectionHelper(token)
server = helper.connect_with_server_name(server_name)
```

### HTTP Client Layer

All HTTP operations use `CurlHttpClient` from ToonamiTools:

```python
from ToonamiTools.CurlHttpClient import CurlHttpClient

client = CurlHttpClient()
response = client.get(url, headers=headers)
data = response.json()
```

**Benefits:**
- Consistent HTTP handling across the codebase
- Uses Python stdlib for HTTP operations
- Built-in error handling and retry logic

### Debugging Tips

**Connection Issues:**
```python
# Enable verbose logging to see all connection attempts
import logging
logging.basicConfig(level=logging.DEBUG)

# The connection helper logs each URL attempt
helper = PlexConnectionHelper(token)
server = helper.connect_smart(resource)  # Check logs for failures
```

**Authentication Issues:**
```python
# Manually test token
from API.utils.PlexClient import PlexAccountClient

account = PlexAccountClient(token)
resources = account.get_resources()
print(f"Found {len(resources)} resources")
```

### Testing

The Plex client can be tested independently:

```python
# Test authentication flow
from API.utils.PlexClient import PlexAuthClient

auth = PlexAuthClient()
url, pin_id = auth.start_auth()
print(f"Visit: {url}")
# After approving...
token = auth.poll_for_token(pin_id, timeout=120)
print(f"Token: {token}")

# Test connection helper
from API.utils.PlexConnectionHelper import PlexConnectionHelper

helper = PlexConnectionHelper(token)
servers = helper.discover_servers()
print(f"Discovered {len(servers)} servers")

for server in servers:
    connected = helper.connect_smart(server)
    print(f"{server.name}: {'Connected' if connected else 'Failed'}")
```

### ComBreakDirect Streaming Architecture (Alpha)

The ComBreakDirect stack uses **Studio → FIFO → Broadcast FFmpeg → BroadcastTower** architecture for continuous MPEG-TS streaming with multi-client support.

- **ComBreakDirectServer.py**
  - Flask entry point that wires REST endpoints.
  - `/playlist.m3u8`, `/api/xmltv.xml` use FactoryFloor generators.
  - `/video/channel/<number>` connects an Antenna to the BroadcastTower and streams chunks.

- **docks/UnloadingDock.py**
  - **Studio Thread** (`build_stream`): Calculates channel position, spawns FFmpeg per program with normalization (H.264 1080p 30fps, AAC stereo 48kHz, CBR 5.4 Mbps), writes MPEG-TS to FIFO (`/tmp/studio_ch{N}.fifo`)
  - **Broadcast FFmpeg** (`start_broadcast_ffmpeg`): Reads FIFO with `-fflags +genpts+discardcorrupt`, creates continuous stream by regenerating PTS, rate limits broadcasting (13ms per chunk)
  - **Lifecycle Management** (`ensure_channel_ready`): Creates FIFO, starts studio thread, starts broadcast FFmpeg, creates BroadcastTower
  - **Client Connection** (`connect_client`): Creates Antenna for client, returns iterator yielding chunks

- **utilities/BroadcastTower.py**
  - `BroadcastTower.broadcast(chunk)`: Sends chunk to ALL connected antennas immediately (no tower buffering)
  - `BroadcastTower.connect_antenna(client_id)`: Creates new Antenna with 132-chunk buffer
  - `Antenna.__iter__()`: Yields chunks with 13ms rate limiting to prevent client buffering ahead
  - `BroadcastTower.has_antennas()`: Used by broadcast FFmpeg to detect when no clients connected

- **Concurrency & Efficiency**
  - **Single studio FFmpeg** transcodes per channel (regardless of client count)
  - **Single broadcast FFmpeg** creates continuous stream per channel
  - **BroadcastTower distributes** to unlimited clients with minimal CPU overhead
  - **Auto lifecycle**: Studio and broadcast FFmpeg only run when clients connected
  - **Multi-client support**: Each client gets dedicated Antenna with independent buffer
  - **Critical fix**: Broadcast FFmpeg's `+genpts` prevents transition freezing in Jellyfin/Plex

### Channel Ingestion Pipeline (Loading Dock → Factory Floor → Streaming)

1. **`POST /channels`** (Flask handler in `ComBreakDirectServer.py`)
   - Validates payload, extracts metadata (`channel_number`, `flex_duration`, optional `commercial_folder`, optional `infinite` + `infinite_meta`).
   - Hands off to `LoadingDock.process_lineup`.
2. **`LoadingDock.process_lineup`**
   - Caches the current commercial folder; swaps libraries if a payload override is provided.
   - `_inject_commercials` looks for consecutive bump items (based on network name or `/bump/` path) and reserves pre-rendered breaks via `CommercialBreakRenderer.plan_break`.
   - `_prime_initial_breaks` calls `CommercialBreakRenderer.pre_render_window` to warm the cache for the first hour of upcoming breaks.
   - `_format_for_streaming` normalises timelines, assigns fallback `block_id`s, and emits a channel dictionary with ISO timestamps. The inner program-builder is extracted as `_format_programs(lineup_data, anchor_time)` so extension chunks can reuse it.
   - When the payload has `infinite: true`, LoadingDock stashes a fully populated `channel_data['_infinite_meta']` block before handing to FactoryFloor.
3. **`FactoryFloor.store_channel`**
   - Writes the channel into `channels.json` (under `CBDIRECT_DATA_ROOT`), guarded by a threading lock.
   - Successive `GET /playlist.m3u8` and `GET /api/xmltv.xml` calls read the cached data via `generate_playlist` / `generate_xmltv`.
   - Calls `_maybe_spawn_extender(channel_data)` so infinite channels get their `LineupExtender` armed immediately.
4. **Break Rendering (`utilities/CommercialBreakRenderer.py`)**
   - `plan_break` reserves `_pre_rendered_breaks/<break_id>.ts`.
   - `get_or_build_break` renders with ffmpeg, selecting audio tracks through `AudioTrackSelector`.
   - `start_background_renderer` (invoked at server start if channels already exist) keeps the cache warm by scanning active channels.
   - `_load_existing_breaks` hardened to skip files that vanish between `listdir()` and `stat()` (race condition with `CleanupManager`/concurrent renders that previously crashed the subprocess on boot).
5. **Serving clients**
   - Plex/Jellyfin hit `/video/channel/{N}` which connects an Antenna to the BroadcastTower
   - Flask generator iterates Antenna chunks and yields to client
   - Studio thread calculates position, starts FFmpeg, writes to FIFO
   - Broadcast FFmpeg reads FIFO, creates continuous stream, broadcasts to tower
   - BroadcastTower distributes to all Antennas simultaneously

#### Infinite Channel Extension Pattern

For any channel with `_infinite_meta.enabled=True`, a `LineupExtender` (in `docks/LineupExtender.py`) runs alongside it:

1. `FactoryFloor._maybe_spawn_extender(channel_data)` constructs a `LineupExtender(self, channel_number)` at `store_channel` time and again for each loaded channel during `_load_channels` startup. The extender is keyed in `FactoryFloor._extenders` to prevent double-spawn.
2. `LineupExtender.start()` calls `_schedule_next()`, which arms a `threading.Timer(delay, self._on_timer_fire)` where `delay = max(0, (channel_end_iso - now_utc).total_seconds() - lead_s)`. Channels shorter than the lead window (or already past their end) fire immediately.
3. When the timer fires:
   - Race-check the channel still exists; cancel if not.
   - Bail if `_infinite_meta.enabled` was flipped off externally, or if `consecutive_failures` has hit `MAX_CONSECUTIVE_FAILURES` (3).
   - Disk-space gate: skip with retry if `< INFINITE_MIN_FREE_DISK_BYTES` free in the storage partition.
   - Call `_build_extension(channel_data, meta)`, which delegates to `ToonamiTools.InfiniteChannelExtender.generate_chunk(channel_number, meta)`:
     - `ShowScheduler(continue_from_last_used_episode_block=True)` runs against a new per-extension table named `{merger_out}_inf_ch{channel}_ext{seq}`.
     - `CutlessFinalizer.run_for_table(input, output_cutless)` produces the cutless companion.
     - Returns `(rows, output_table)` for the caller.
   - `loading_dock.format_extension(rows, channel_data)` formats the new programs with `anchor_time = channel_data['programs'][-1]['stop']` so timestamps stay contiguous.
   - `factory_floor.extend_channel(channel_number, new_programs)` appends (under the factory lock), bumps `extension_seq`, persists `channels.json`.
   - `_schedule_next()` recomputes the new channel-end and arms a fresh timer.

**Append-only invariant**: never replace `channel_data['programs']` with a new list. The Studio thread reads `programs[current_index % len(programs)]` continuously; appending is safe under the GIL, replacing would break the live read. `FactoryFloor.extend_channel` uses `programs.extend()` deliberately.

**Lazy LoadingDock lookup**: `LineupExtender` holds the FactoryFloor reference and accesses `factory_floor.loading_dock` via a `@property` on demand. Constructed with `LoadingDock` directly would AttributeError on watchdog respawn during `_load_channels`, because at that exact moment `LoadingDock.__init__` is still mid-assignment of `self.factory_floor = FactoryFloor(...)`.

**Failure handling**: recoverable failures (transient disk pressure, single build error) bump `_infinite_meta.consecutive_failures` and retry in `RETRY_AFTER_FAILURE_MS` (5 min). Three failures in a row trigger `_disable(channel_data, reason)` which sets `_infinite_meta.enabled=False`, persists, surfaces via `ErrorManager`, and cancels the watchdog. The Studio's modulo loop keeps playing existing programs so the channel doesn't die — it just stops growing.

**Wall-clock not playback**: the trigger condition is `(last_program.stop - now_utc) < lead_ms`. Studio's `current_index` (only updated while a client is connected) is deliberately NOT consulted. This is what makes channels keep growing while idle.

#### Debugging Tips

- **Studio Thread**: Look for `[STUDIO]` prefix in logs - shows program transitions, FIFO writes, BrokenPipeError on disconnect
- **Broadcast FFmpeg**: Look for `[BROADCAST_FFMPEG]` prefix - shows startup, broadcasting, stop on no clients
- **BroadcastTower**: Look for `[BROADCAST_TOWER]` prefix - shows antenna connections/disconnections, active count
- **Antenna**: Look for `[ANTENNA]` prefix - shows chunks received, "lost signal" when buffer overflows
- **LineupExtender**: Look for `[LINEUP_EXTENDER]` prefix - shows timer scheduling (`next extension in X.X min`), watchdog spawn, extension success (`appended N programs`), and any retries/disables
- **FactoryFloor extension**: Look for `[FACTORY_FLOOR] Armed LineupExtender for channel N` and `[FACTORY_FLOOR] Extended channel N by M programs`
- **Cursor inspection**: `sqlite3 Toonami.db 'SELECT * FROM last_used_episode_block'` shows per-show BLOCK_ID cursors. After the first extension fires this table should be populated.
- **Per-extension tables**: extension chunks live at `lineup_v{N}_cont_inf_ch{ch}_ext{seq}` and `lineup_v{N}_cont_inf_ch{ch}_ext{seq}_cutless`. List them with `SELECT name FROM sqlite_master WHERE name LIKE 'lineup_v%_inf_ch%'`.
- **FIFO Issues**: Check `/tmp/studio_ch{N}.fifo` exists when streaming, verify both studio and broadcast FFmpeg running
- **Transition Freezing**: Ensure broadcast FFmpeg has `+genpts` flag - critical for continuous stream
- When editing the streaming stack, rebuild/restart the Docker container so the running server picks up changes:

```bash
docker compose build
docker compose up -d
docker compose logs -f
```
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

### Working with Dictionary-Based Data

All database operations return native Python data structures (lists of dictionaries). This approach eliminates heavy dependencies while maintaining excellent performance for typical dataset sizes.

#### Reading Data as Dictionaries

```python
# Read all rows as list of dictionaries
data = self.db_manager.fetchall_as_dicts("SELECT * FROM shows")
# Returns: [{"id": 1, "name": "Naruto", "active": True}, {"id": 2, "name": "Bleach", "active": True}]

# Read single row as dictionary
row = self.db_manager.fetchone_as_dict("SELECT * FROM shows WHERE id = ?", (1,))
# Returns: {"id": 1, "name": "Naruto", "active": True} or None if not found

# With parameters
active_shows = self.db_manager.fetchall_as_dicts(
    "SELECT * FROM shows WHERE active = ?",
    (True,)
)
```

#### Filtering and Transforming Data

```python
# Filter using list comprehensions
active_shows = [row for row in data if row['active'] == True]
recent_episodes = [row for row in data if row['season'] > 1]

# Transform data by modifying dictionaries in place
for row in data:
    row['normalized_name'] = row['name'].lower()
    row['full_title'] = f"{row['name']} Season {row['season']}"

# Chain filters
filtered = [
    row for row in data
    if row['status'] == 'active' and row.get('episodes', 0) > 10
]
```

#### Sorting Data

```python
# Sort by single key
data.sort(key=lambda x: x['name'])

# Sort by multiple keys
data.sort(key=lambda x: (x['season'], x['episode']))

# Sort in reverse
data.sort(key=lambda x: x['episode_count'], reverse=True)
```

#### Saving Data

```python
# Bulk insert list of dictionaries
new_rows = [
    {"name": "One Piece", "season": 1, "active": True},
    {"name": "Gundam", "season": 2, "active": True}
]
self.db_manager.bulk_insert_dicts("shows", new_rows)

# Create table from data (with type inference)
self.db_manager.create_table_from_dicts("new_table", data, if_exists='replace')

# Replace all data in existing table
processed_data = process(data)
self.db_manager.replace_table_data("shows", processed_data)

# Drop table if needed
self.db_manager.drop_table("temporary_table")
```

#### Checking for None/Empty Values

```python
# Check for None or empty string
if row.get('column') is None or row.get('column') == '':
    # Handle missing/empty value
    pass

# Safe access with default
value = row.get('optional_column', 'default_value')

# Filter out rows with missing data
valid_data = [
    row for row in data
    if row.get('required_field') and row['required_field'] != ''
]
```

#### Deduplication

```python
# Deduplicate by key, keeping last occurrence
seen = {}
for row in data:
    seen[row['unique_key']] = row
deduplicated = list(seen.values())

# Deduplicate by multiple columns
seen = {}
for row in data:
    key = (row['show'], row['season'], row['episode'])
    seen[key] = row
deduplicated = list(seen.values())
```

#### Grouping Data

```python
from collections import defaultdict

# Group by single key
groups = defaultdict(list)
for row in data:
    groups[row['show_name']].append(row)

# Process each group
for show_name, episodes in groups.items():
    print(f"{show_name}: {len(episodes)} episodes")

# Group by multiple keys
groups = defaultdict(list)
for row in data:
    key = (row['show'], row['season'])
    groups[key].append(row)
```

### Important Notes

1. **Never use `sqlite3.connect()` directly** - Always use `get_db_manager()`
2. **Thread Safety** - Each thread gets its own connection automatically
3. **Auto-retry** - Database locks are handled with exponential backoff
4. **Transactions** - Use the `transaction()` context manager for atomic operations
5. **Resource Cleanup** - Connections are managed automatically per thread
6. **Dict Lists vs DataFrames** - For typical dataset sizes (< 10,000 rows), dict lists provide better memory efficiency and simpler code
7. **Type Inference** - `create_table_from_dicts()` infers column types from the first row (int, float, or text)

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

            # Load data as list of dictionaries
            data = self.db_manager.fetchall_as_dicts("SELECT * FROM shows")

            # Transform data
            for row in data:
                # Use show_name_mapper for name normalization
                row['normalized_name'] = show_name_mapper.map(row['show'], strategy='all')
                row['clean_name'] = show_name_mapper.clean(row['normalized_name'], mode='matching')

            # Filter data
            active_shows = [row for row in data if row.get('active', False)]

            # Save processed data
            self.db_manager.replace_table_data("processed_shows", active_shows)

            return len(active_shows)

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

## Network Switching (Developer Notes)

### Overview
The application supports dynamic network switching (e.g., “Toonami”, “Cartoon Network”). This affects UI labels and the selected SQLite database (`<network>.db`). To ensure consistency, UIs re‑exec the current process after updating `config.py`.

### Orchestrator API
`API/FrontEndLogic.py` exposes:

```python
validate_network(network_name: str) -> bool
apply_network(network_name: str) -> bool
reset_network() -> bool
```

Use `validate_network` before `apply_network` for UIs. `apply_network` writes the new `network` to `config.py` and broadcasts a status update. UIs are responsible for restarting the process.

### Validator Component
`API/utils/NetworkManager.py`

```python
validate_network_name(network_name) -> tuple[bool, str]
update_config_network(config_path, new_network) -> None
```

- Uses urllib HEAD (fallback GET) with a custom User-Agent to probe Wikipedia pages:
  - `List_of_programs_broadcast_by_<Network>` and `..._on_<Network>`
- Accepts multi‑word names (spaces become underscores for probing only).
- Returns guidance messages for UIs on failure.

### UI Implementation Guidance
- TOM (`GUI/TOM.py`): present Advanced dialog on Page 1; on success call `os.execv(sys.executable, [sys.executable] + sys.argv)`.
- Absolution (`GUI/Absolution.py`): bottom‑right Advanced overlay; restart in a background thread after setting a status message.
- Clydes (`CLI/clydes.py`): optional pre‑flight advanced prompt; instruct user to re‑run after persisting.

### Testing Tips
- Use the TV fixtures with non‑Toonami networks (“Cartoon Network”, “Disney Channel”) to verify end‑to‑end operation.
- Mock `_url_exists` or the validator when running in offline CI.
- Ensure no long‑lived modules cache `config.network` at import time across a restart boundary; rely on the re‑exec to reload imports cleanly.
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

### Chain Continuity Validator

S.A.R.A. includes an optional chain continuity validator that asserts the lineup follows the TV guide announced by multibumps (NS2/NS3). It lives in `tests/validators/ChainValidator.py` and performs:

- Bump-to-bump chaining: After an NS3 (Now S1, Next S2, Later S3), the next bump must anchor on S3 (Now S3 or From S3). After an NS2 (S1 Next From S2), the next bump must anchor on S1.
- Bump-to-episode “Now”: The first episode after a bump must be the announced Now show (S1).
- Episode-to-episode “Next”: At show-change boundaries, the new show must match the bump’s Next mapping (S1→S2, S2→S3).
- NS2 “From” context: Immediately before an NS2, the active show must be S2.

By default, the validator runs in non-strict mode and logs potential violations. To enforce strictly and fail the test on violations:

```bash
STRICT_CHAIN_VALIDATION=1 pytest -q -k test_sara_automatic.py -s
```

You can also run it ad-hoc in Python (honors `DB_PATH`):

```bash
python - <<'PY'
from tests.validators.ChainValidator import ChainValidator
import os
os.environ['DB_PATH'] = 'absolute/path/to/your.db'
cv = ChainValidator()
viol = cv.validate_table_with_episodes('lineup_v8')
print(len(viol), viol[:3])
PY
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

### Show Name Normalization

Across tools, use the same normalization pipeline when comparing or joining show names:

- Map using all configured dictionaries: `show_name_mapper.map(name, strategy='all')`
- Then clean for matching: `show_name_mapper.clean(mapped, mode='matching')`

This produces a canonical, lowercase, punctuation-free key (e.g., “Law & Order” -> “law and order”) that aligns bumps, Toonami_Shows, and episode-derived names.

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
