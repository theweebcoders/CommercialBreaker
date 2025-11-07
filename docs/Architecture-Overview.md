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
│ • Authentication│ • External REST     │ • Self-contained      │
│ • Library Scan  │ • Channel Creation  │ • Direct streaming    │
│ • Timestamps    │                     │ • M3U/XMLTV gen       │
│ • File Paths    │                     │ • Plex discovery      │
└─────────────────┴─────────────────────┴───────────────────────┘
```
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
```

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

  Broadcasting Architecture (Unloading Dock):

  Studio Thread → FIFO → Broadcast FFmpeg → BroadcastTower → Antennas
     (full tape,     (pipe)   (+genpts,        (distributes    (per-client
      normalizes              continuous)       to all)         buffers)
      programs)
```

**Key Features**:
- **Loading Dock** (`docks/LoadingDock.py`): Processes cutless lineup data, injects commercials between bumps, pre-renders breaks
- **Factory Floor** (`docks/FactoryFloor.py`): Generates M3U8 playlists and XMLTV guides, stores channel configurations
- **Unloading Dock** (`docks/UnloadingDock.py`): Manages studio threads, broadcast FFmpeg processes, and BroadcastTower distribution
- **BroadcastTower** (`utilities/BroadcastTower.py`): Multi-client streaming engine with Antenna pattern
- **WebUI** (`UI/WebUI.py`): Landing page with setup instructions and copy-to-clipboard buttons
- **Audio Selector** (`utilities/AudioTrackSelector.py`): Configurable audio track selection (defaults to English)
- **Commercial Renderer** (`utilities/CommercialBreakRenderer.py`): Pre-renders breaks to eliminate startup delays
- **Cleanup Manager** (`utilities/CleanupManager.py`): Automatically removes old pre-rendered breaks

**Technical Architecture**:
- **Studio Thread**: Calculates channel position, spawns FFmpeg per program with normalization, writes to FIFO
- **Broadcast FFmpeg**: Reads FIFO with `+genpts`, creates continuous stream, rate limits broadcasting
- **BroadcastTower**: Receives stream, distributes to all Antenna objects (one per client)
- **Antenna Buffer**: Per-client 132-chunk buffer (~2 seconds) with rate limiting
- **Auto Lifecycle**: Studio and broadcast FFmpeg only run when clients connected
- **Real-time Sync**: All clients synchronized to same channel position

**Integration Points**:
- `ComBreakToComBreakDirect` - Pushes cutless lineup to server via REST API
- `LogicController._ensure_combreakdirect_server()` - Auto-starts server
- Flask REST API for channel management and streaming
- HDHomeRun discovery for Plex DVR integration
- WebUI served at root path for easy access

For detailed ComBreakDirect documentation, see [ComBreakDirect.md](ComBreakDirect.md).

---

This architecture supports the system's goals of modularity, reliability, and extensibility while maintaining the performance necessary for processing large media libraries efficiently. The addition of ComBreakDirect provides an alternative deployment model that eliminates external platform dependencies.
