# Architecture Overview

This document provides a technical overview of the CommercialBreaker & Toonami Tools system architecture, component relationships, and data flow.

## System Overview

CommercialBreaker & Toonami Tools is a modular Python application designed to automate the creation of Toonami-style anime marathon channels. The system processes anime episodes, detects commercial break points, and integrates authentic Toonami bumps to create seamless viewing experiences.

### Core Philosophy

- **Modular Design**: Each tool handles a specific aspect of the pipeline
- **Database-Driven**: SQLite manages metadata and processing state
- **Interface Flexibility**: Multiple UIs for different use cases
- **Platform Agnostic**: Works with various media servers and channel platforms

---

## Application Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Entry Point (main.py)                   │
├─────────────────────────────────────────────────────────────┤
│Interface Selection: --tom | --webui | --clydes | --combreak │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────┬─────────────────┬─────────────────┐
│   GUI Layer     │   Web Layer     │   CLI Layer     │
│                 │                 │                 │
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────┐ │
│ │ TOM.py      │ │ │Absolution.py│ │ │ clydes.py   │ │
│ │ (Tkinter)   │ │ │ (REMI/Web)  │ │ │ (Console)   │ │
│ └─────────────┘ │ └─────────────┘ │ └─────────────┘ │
└─────────┬───────┴─────────┬───────┴─────────┬───────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼ 
┌─────────────────────────────────────────────────────────────┐          
│               FrontEndLogic.py (Orchestrator API)           │
├─────────────────────────────────────────────────────────────┤
│ • LogicController class - Central API for all UIs           │           
│ • State management via SQLite database via DataManager      │
│ • Threading for background operations                       │
└─────────────────────────────────────────────────────────────┘           
        │    │  ▲          │    ▲
        │    │  │          │    │
        │    │  │          ▼    │  
        │    │  │   ┌───────────────────────────────────────────────────────────┐
        │    │  │   │                  Supporting API Modules                   │
        │    │  │   ├──────────────────────────┬────────────────────────────────┤
        │    │  │   │  FlagManager.py          │  MessageBroker.py              │
        │    │  │   │ • Platform compatibility │ • Real-time communication      │
        │    │  │   │ • Global Flags           │ • In-memory pub/sub            │
        │    │  │   ├──────────────────────────┼────────────────────────────────┤
        │    │  │   │  NetworkManager.py       │  ErrorManager.py               │
        │    │  │   │ • Network validation     │ • Centralized error handling   │
        │    │  │   │ • Config persistence     │ • Error history tracking       │
        │    │  │   │   (update config.py)     │ • UI error broadcasting        │
        │    │  │   ├──────────────────────────┼────────────────────────────────┤
        │    │  │   │  DatabaseValidator       │  FilenameParser                │
        │    │  │   │ • S.A.R.A. orchestration │ • Centralized parsing logic    │
        │    │  │   │ • 20 step validators     │ • Episode name extraction      │
        │    │  │   │ • Integrity validation   │ • Year handling (2002)         │
        │    │  │   │ • Phase-aware tracking   │ • Consistent across tools      │
        │    │  │   ├──────────────────────────┴────────────────────────────────┤
        │    │  │   │  NetworkUtils.py                                          │
        │    │  │   │ • Curl-based HTTP client  • Wikipedia table parser        │
        │    │  │   │ • Response interface      • Request exceptions            │
        │    │  │   └───────────────────────────────────────────────────────────┘
        │    │  │                                               ▲ 
        │    ▼  │                                               │
        │  ┌────────────────────────────────────────────────┐   │
        │  │                    Database                    │   │ 
        │  ├────────────────────────────────────────────────┤   │
        │  │ DatabaseManager.py                             │   │
        │  ├────────────────────────────────────────────────┤   │
        │  │ • Thread-safe connections • Transaction support│   │
        │  │ • Automatic retry logic   • Simplified API     │   │
        │  └────────────────────────────────────────────────┘   │
        │     ▲  │                                              │
        │     │  │                ┌─────────────────────────────┘
        ▼     │  ▼                │
   ┌─────────────────────────────────────────────────────────────┐
   │                   Core Processing Layer                     │
   ├─────────────────┬─────────────────┬─────────────────────────┤
   │   ComBreak/     │ ToonamiTools/   │     ExtraTools/         │
   │                 │                 │                         │
   │ • Commercial    │ • Show Detection│ • Manual Tools          │
   │   Detection     │ • Lineup        │ • Utilities             │
   │ • File Cutting  │   Generation    │ • Debugging             │
   │ • Cutless Mode  │ • Bump Encoding │                         │
   └─────────────────┴─────────────────┴─────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│              Platform Integration Layer                       │
├─────────────────┬─────────────────────┬───────────────────────┤
│   Plex API      │   Platform APIs     │  ComBreakDirect       │
│                 │                     │                       │
│ • OAuth Auth    │ • External REST     │ • Self-contained      │
│ • Library Scan  │ • Channel Creation  │ • Direct streaming    │
│ • Timestamps    │                     │ • M3U/XMLTV gen       │
│ • Smart Retry   │                     │ • Plex discovery      │
└─────────────────┴─────────────────────┴───────────────────────┘
```

### Plex Integration

CommercialBreaker includes a Plex client implementation located in `API/utils/`:

```
Plex Client Architecture

┌─────────────────────────────────────────────────────────┐
│                 PlexConnectionHelper.py                 │
│  • Smart connection retry (local → direct → relay)     │
│  • Server discovery and connection management          │
│  • Automatic failover between connection URLs          │
└────────────────┬────────────────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
      ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ PlexClient.py    │  │ PlexServer.py    │
│                  │  │                  │
│ • PlexAuthClient │  │ • SimplePlexServ.│
│ • OAuth PIN flow │  │ • Library access │
│ • Account client │  │ • Section queries│
│ • Resource list  │  │ • Episode data   │
└──────────────────┘  └──────────────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌────────────────────────┐
         │   CurlHttpClient       │
         │   (ToonamiTools/)      │
         │  • HTTP operations     │
         │  • Stdlib based        │
         └────────────────────────┘
```

**Key Benefits**:
- **Minimal Dependencies**: Uses Python stdlib `urllib` and `CurlHttpClient`
- **Connection Reliability**: Automatically tries all available server URLs
- **Lightweight**: Only implements features actually used by CommercialBreaker
- **Stability**: Direct control over Plex API interactions

**Integration Points**:
- `LoginToPlex.py` - OAuth authentication and server selection
- `GetTimestampPlex.py` - Fetch "Skip Intro" timestamps
- `PlexAutoSplitter.py` - Split merged episodes
- `RenameSplitPlex.py` - Rename split episodes to match file names

---

## In-Memory Message Broker

A unified in-memory message broker is responsible for all real-time communication between the LogicController and the various user interfaces (GUI, Web, CLI).

- **Channel-Based Communication**: All UIs subscribe to relevant channels for updates and publish user actions/events.
- **Decoupled Integration**: Interfaces interact with the LogicController exclusively through the message broker, ensuring modularity and testability.

## Database Management

The CommercialBreaker uses a centralized DatabaseManager for all database operations, providing:

- **Thread-safe connections**: Each thread gets its own database connection
- **Automatic retry logic**: Handles database locks with exponential backoff
- **Transaction support**: Atomic operations with automatic commit/rollback
- **Simplified API**: Common operations wrapped in convenient methods
- **Dictionary-based operations**: Queries return lists of dictionaries (`fetchall_as_dicts()`, `bulk_insert_dicts()`, etc.)

All modules access the database through `get_db_manager()` from `API.utils.DatabaseManager`, ensuring consistent error handling and preventing database lock issues in multi-threaded scenarios.

## Centralized Error Handling

The system employs a centralized error handling mechanism via `ErrorManager.py`, which provides:
- **Global Error Tracking**: All errors are logged and can be retrieved by any interface
- **UI Broadcasting**: Errors can be sent to all interfaces for real-time user feedback
- **Error History**: Maintains a history of errors for debugging and user support
- **Modular Error Handling**: Each module can raise errors that are caught and processed by the ErrorManager
- **Custom Error Types**: Allows for specific error handling based on module needs

---

## S.A.R.A. Validation System

The **S.A.R.A. (System Analysis and Reporting Assistant)** validation system provides comprehensive database validation and diagnostics. It follows the philosophy: **"Validate everything, trust nothing."**

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DatabaseValidator                        │
│               (Main Orchestration Layer)                    │
├─────────────────────────────────────────────────────────────┤
│ • Coordinates 20 validators (18 step + 2 integrity)         │
│ • Consolidates issues intelligently                         │
│ • Reports to ErrorManager → broadcasts to all UIs           │
│ • Phase-aware progress tracking                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    BaseValidator                            │
│            (Abstract Base for All Validators)               │
├─────────────────────────────────────────────────────────────┤
│ • Database access utilities (via DatabaseManager)           │
│ • Bump vs anime detection (consistent with main tools)      │
│ • Mode detection (cutless vs traditional)                   │
│ • Platform detection (DizqueTV, Tunarr, ComBreakDirect)     │
│ • Issue creation and management                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
        ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Step Validator│ │  Integrity   │ │PhaseTracker  │ │ValidationRes.│
│  (18 total)  │ │ Validators   │ │              │ │              │
│              │ │  (2 total)   │ │• Maps steps  │ │• Result      │
│• Platform    │ │              │ │  to phases   │ │• Issue       │
│• ToonamiCheck│ │• Lineup      │ │• Progress    │ │• Level       │
│• LineupPrep  │ │  Integrity   │ │  tracking    │ │• Status      │
│• CommercialBr│ │• Referential │ │• Conditional │ │              │
│• (15 more)   │ │  Integrity   │ │  step logic  │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### Key Features

**Step Validation:**
- Each pipeline step has a dedicated validator
- Validates table existence, structure, and data quality
- Checks cross-table relationships and referential integrity
- Detects platform compatibility issues

**Integrity Validation:**
- **LineupIntegrityValidator**: Validates bump placement rules (multibumps → anime, intro → matching BLOCK_ID, etc.)
- **ReferentialIntegrityValidator**: Validates cross-table consistency (BLOCK_IDs exist, file paths valid, etc.)

**Phase-Aware Tracking:**
- Maps individual steps to logical workflow phases (0-6)
- Tracks which phase is complete vs in-progress
- Accounts for conditional steps (PlexAuth, BumpCalculator, etc.)

**Issue Consolidation:**
- Groups related issues to prevent overwhelming users
- Three consolidation strategies:
  1. Version-based (e.g., "Version 2: missing data, Version 3: invalid timestamps")
  2. List-items (e.g., "3 folder issues: • ANIME_FOLDER missing • BUMPS_FOLDER missing • ...")
  3. Generic numbered list for other multi-issue scenarios

**Mode Detection:**
- Automatically detects cutless vs traditional mode
- Identifies platform (DizqueTV, Tunarr, ComBreakDirect)
- Warns about incompatibilities (e.g., cutless mode with Tunarr)

### UI Integration: Page8 Diagnostics

S.A.R.A. is accessible through **Page8** in the GUI interfaces (TOM and Absolution):

**Access Method:**
- **Hidden Panic Button**: Click any page title 5 times in 2 seconds

**Features:**
- Pipeline status with completion checklist (✓/✗ for each step)
- Run full validation button
- Refresh status button
- Copy results to clipboard (for bug reports)
- Real-time status updates during validation
- Grouped issues by severity (CRITICAL, ERROR, WARNING, INFO)

### Hidden Panic Button

**Implementation**: Track clicks on page title labels. 5 clicks within 2 seconds → navigate to Page8.

**Purpose**: Provides quick access to diagnostics without memorizing menu structure, especially useful during critical errors.

**Location**: Implemented on all pages except Page5 in TOM (complex layout).

### Validation Output

Each validation issue includes:
- **Where**: Which step, table, and row (if applicable)
- **What**: User-friendly message describing the problem
- **Why**: Technical details for developers
- **How to Fix**: Actionable suggestion
- **When**: Timestamp

**Example Issue:**
```
[ERROR] CommercialBreaker → cuts
Message: 3 episodes missing commercial break timestamps
Details: Files: Naruto S01E05.mkv, Naruto S01E06.mkv, Bleach S02E03.mkv
Suggestion: Re-run CommercialBreaker in normal mode (not low power) to detect breaks
```

### Integration with FrontEndLogic

**Methods Added to LogicController:**
```python
def run_full_validation(self):
    """Run comprehensive database validation (background thread)"""

def get_pipeline_status(self) -> PipelineStatus:
    """Get quick pipeline status without full validation"""
```

**For complete S.A.R.A. documentation**, see [S.A.R.A. Validation System](S.A.R.A-Validation-System.md).

---

## Filename Parsing

The `FilenameParser` utility provides centralized, consistent episode filename parsing across all modules.

**Location**: `/ToonamiTools/utils/FilenameParser.py`

**Features:**
- Automatic year stripping from show names (e.g., "Naruto (2002)" → "Naruto")
- Comprehensive SxxExx pattern extraction
- Season and episode number parsing (handles single and double digits)
- Validation and error reporting

**Used By:**
- VirtualCut (cutless mode operations)
- DirectoryScanner (file discovery)
- BlockMaker (BLOCK_ID generation)
- PlexToDizqueTV (channel creation)
- All validators (consistency check)

**Benefits**:
- Single source of truth for filename parsing
- Consistent behavior across entire codebase
- Automatic year handling from show names
- Easier to maintain and test

---

## Plex Connection Reliability

Enhanced Plex connection reliability with retry logic and progressive timeouts.

**Improvements:**
- **Retry Logic**: Up to 3 attempts with configurable delay
- **Progressive Timeout**: Increases with each retry (base + 20s per attempt)
- **Status Broadcasting**: Real-time updates to user during retries
- **Configuration-Driven**: `config.PLEX_RETRY_ATTEMPTS`, `config.PLEX_RETRY_DELAY`, timeouts

**Modified Files:**
- `LoginToPlex.py` - PlexLibraryManager and PlexLibraryFetcher
- `PlexServer.py` - SimplePlexServer with configurable timeout

**Why**: Intermittent failures on slower networks or when servers are starting up. Retry logic makes connection more reliable without user intervention.

---

## Data Flow

### 1. Initialization Phase

```
User Input → Interface Selection → Configuration Loading → Platform Selection → Plex Authentication (conditional)
```

**Note**: Platform selection (DizqueTV, Tunarr, or ComBreakDirect) determines whether Plex authentication is required. ComBreakDirect users skip Plex authentication entirely.

### 2. Content Discovery Phase

```
Plex Library Scan → Show Detection (IMDB/Wikipedia) → Bump Analysis → Database Population
```

### 3. Processing Phase

```
Episode Selection → Commercial Detection → File Processing → Metadata Generation
```

### 4. Integration Phase

```
Lineup Generation → Platform Channel Creation → Playback Optimization
```

**Platform Options**:
- **External Platforms**: Traditional platform integration via REST APIs
- **ComBreakDirect**: Self-contained streaming server (new)

### 5. ComBreakDirect Streaming Phase (Optional)

```
ComBreakToComBreakDirect → ComBreakDirect Server → Live MPEG-TS Stream → Plex/Clients
                                  │
                                  └─▶ LineupExtender (per channel)
                                         │  threading.Timer
                                         │  fires INFINITE_EXTEND_LEAD_MS
                                         │  before channel end
                                         ▼
                                  InfiniteChannelExtender
                                  (ShowScheduler + CutlessFinalizer)
                                         │
                                         ▼
                                  FactoryFloor.extend_channel
                                  (append-only, persists channels.json)
```

ComBreakDirect channels are never finite. The LineupExtender's per-channel timer fires on wall-clock time (independent of whether a client is streaming) and appends a fresh ~40 hour chunk before the existing one runs out. The channel survives indefinitely until the LineupExtender is explicitly disabled or `_infinite_meta.enabled` is set to false on the channel.

---

## ComBreakDirect Architecture

ComBreakDirect is an optional self-contained streaming server using Studio → FIFO → Broadcast FFmpeg → BroadcastTower architecture. It provides:

- **Continuous MPEG-TS Streaming**: True broadcast-style streaming with seamless program transitions
- **BroadcastTower Multi-Client**: Efficient distribution to multiple simultaneous viewers
- **WebUI**: Toonami-themed landing page with setup instructions
- **M3U8 Generation**: Dynamic playlist creation for Plex/Jellyfin
- **XMLTV Guides**: Full EPG data with show metadata
- **Plex/Jellyfin Discovery**: HDHomeRun-style auto-discovery
- **Commercial Injection**: Server-side ad break management with pre-rendering
- **Intelligent Audio Selection**: Configurable audio track selection (defaults to English for Toonami)
- **Auto Lifecycle**: Studio and broadcast FFmpeg start/stop based on client connections
- **Infinite Channel Extension**: Per-channel `threading.Timer` arms ahead of channel end, runs ShowScheduler+CutlessFinalizer to append the next chunk, then reschedules — wall-clock based

### ComBreakDirect Components

```
┌──────────────────────────────────────────────────────────────────┐
│   ComBreakDirect Server (Flask + Studio + BroadcastTower)       │
│                        Port 8083                                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    WebUI (UI/)                           │   │
│  │  • Landing page (setup instructions, copy-to-clipboard) │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
  ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
  │  Loading Dock    │ │Factory Floor │ │ Unloading Dock   │
  │   (docks/)       │ │  (docks/)    │ │   (docks/)       │
  │                  │ │              │ │                  │
  │ • Process lineup │ │ • Store data │ │ • Studio thread  │
  │ • Inject ads     │ │ • Generate   │ │ • Broadcast      │
  │ • Pre-render     │ │   M3U8/XMLTV │ │   FFmpeg         │
  │   breaks         │ │ • Persist    │ │ • BroadcastTower │
  │                  │ │   channels   │ │ • Multi-client   │
  └──────────────────┘ └──────────────┘ └──────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │          Supporting Utilities (utilities/)                  │
  │  • BroadcastTower - Multi-client streaming engine          │
  │  • AudioTrackSelector - Intelligent audio selection        │
  │  • CommercialBreakRenderer - Pre-rendering system          │
  │  • CleanupManager - Automatic file maintenance             │
  │  • configuration - Path resolution                         │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │   Infinite Channel Extension (docks/ + ToonamiTools/)       │
  │  • LineupExtender (docks/) - Per-channel threading.Timer   │
  │    watchdog, fires before channel end                       │
  │  • InfiniteChannelExtender (ToonamiTools/) - Builds one    │
  │    extension chunk via ShowScheduler + CutlessFinalizer    │
  └─────────────────────────────────────────────────────────────┘

  Broadcasting Architecture (Unloading Dock):

  Studio Thread → FIFO → Broadcast FFmpeg → BroadcastTower → Antennas
     (full tape,     (pipe)   (+genpts,        (distributes    (per-client
      normalizes              continuous)       to all)         buffers)
      programs)
```

**Key Features**:
- **Loading Dock** (`docks/LoadingDock.py`): Processes cutless lineup data, injects commercials between bumps, pre-renders breaks. `format_extension` reuses the program-builder to splice extension chunks onto the existing channel timeline.
- **Factory Floor** (`docks/FactoryFloor.py`): Generates M3U8 playlists and XMLTV guides, stores channel configurations. `extend_channel` appends new programs under the factory lock; `_maybe_spawn_extender` arms a LineupExtender per infinite channel at `store_channel` and on `_load_channels` restart.
- **Unloading Dock** (`docks/UnloadingDock.py`): Manages studio threads, broadcast FFmpeg processes, and BroadcastTower distribution
- **BroadcastTower** (`utilities/BroadcastTower.py`): Multi-client streaming engine with Antenna pattern
- **WebUI** (`UI/WebUI.py`): Landing page with setup instructions and copy-to-clipboard buttons
- **Audio Selector** (`utilities/AudioTrackSelector.py`): Configurable audio track selection (defaults to English)
- **Commercial Renderer** (`utilities/CommercialBreakRenderer.py`): Pre-renders breaks to eliminate startup delays
- **Cleanup Manager** (`utilities/CleanupManager.py`): Automatically removes old pre-rendered breaks
- **Lineup Extender** (`docks/LineupExtender.py`): Per-channel `threading.Timer` scheduler, fires `INFINITE_EXTEND_LEAD_MS` (default 3h) before the last program ends, then reschedules after each extension
- **Infinite Channel Extender** (`ToonamiTools/InfiniteChannelExtender.py`): One-shot orchestrator the LineupExtender calls — runs ShowScheduler with `continue_from_last_used_episode_block=True` against a per-extension SQLite table, then CutlessFinalizer, then returns the rows for LoadingDock to format

**Technical Architecture**:
- **Studio Thread**: Calculates channel position, spawns FFmpeg per program with normalization, writes to FIFO
- **Broadcast FFmpeg**: Reads FIFO with `+genpts`, creates continuous stream, rate limits broadcasting
- **BroadcastTower**: Receives stream, distributes to all Antenna objects (one per client)
- **Antenna Buffer**: Per-client 132-chunk buffer (~2 seconds) with rate limiting
- **Auto Lifecycle**: Studio and broadcast FFmpeg only run when clients connected
- **Real-time Sync**: All clients synchronized to same channel position
- **Wall-Clock Extension**: LineupExtender's timer fires on real time, independent of playback — channels grow even when no client is streaming. The watchdog reads the last program's `stop` ISO timestamp, not Studio's `current_index`.
- **Cursor-Driven Continuation**: `ComBreakToComBreakDirect._seed_episode_cursor` populates `last_used_episode_block` from the initial lineup before the channel is POSTed, so the first extension picks up at E+1 of each show (not the same E0 again, not a random jump)
- **Append-Only Growth**: `FactoryFloor.extend_channel` only ever calls `programs.extend()` — never replaces or reorders — so the Studio's `programs[i % len(programs)]` reads stay coherent across the seam without read-side locking

**Integration Points**:
- `ComBreakToComBreakDirect` - Pushes cutless lineup to server via REST API; sets `infinite=True` + `infinite_meta` on the payload for ComBreakDirect channels
- `LogicController._ensure_combreakdirect_server()` - Auto-starts server
- Flask REST API for channel management and streaming
- HDHomeRun discovery for Plex DVR integration
- WebUI served at root path for easy access
- `config.INFINITE_EXTEND_LEAD_MS` - Tunable lead time (default 10 800 000 ms = 3h) for when the LineupExtender fires ahead of channel end

For detailed ComBreakDirect documentation, see [ComBreakDirect.md](ComBreakDirect.md).

---

This architecture supports the system's goals of modularity, reliability, and extensibility while maintaining the performance necessary for processing large media libraries efficiently. The addition of ComBreakDirect provides an alternative deployment model that eliminates external platform dependencies.
