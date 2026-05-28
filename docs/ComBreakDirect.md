# ComBreakDirect

## What is ComBreakDirect?

ComBreakDirect is a self-contained streaming server that creates live TV channels directly from your Toonami cutless database. It eliminates the dependency on third-party platforms by providing its own streaming engine, M3U playlist generation, and XMLTV guide generation.

Think of it as your own personal TV station that broadcasts your Toonami channel 24/7, complete with commercial breaks, all served directly from CommercialBreaker.

## Why ComBreakDirect?

### Key Benefits

1. **Self-Contained**: No dependency on external platforms
2. **Plex Integration**: HDHomeRun-style discovery for seamless Plex integration
3. **Direct Streaming**: Stream cutless content without intermediate platform
4. **Simplified Setup**: One server handles everything - streaming, playlists, and guides
5. **Automatic Commercial Injection**: Server-side commercial break rendering
6. **Fast Startup**: Pre-rendered commercial breaks prevent delays
7. **Infinite by Design**: A built-in `LineupExtender` arms a `threading.Timer` per channel that fires ahead of the last program's stop time and runs ShowScheduler+CutlessFinalizer to append a fresh chunk — wall-clock based, so the channel keeps marching forward whether anyone is streaming or not. Page 7's manual continuation flow is superseded for ComBreakDirect channels.

### How It Compares

| Feature | External Platforms | ComBreakDirect |
|---------|-----------------|----------------|
| External Dependency | Required | None |
| Cutless Support | DizqueTV 1.7+ | Native |
| Commercial Breaks | Client-side | Server-side |
| Setup Complexity | Multiple steps | Single server |
| Plex Discovery | Manual | Automatic (HDHomeRun) |
| Startup Time | Instant | ~30s (pre-rendering) |
| Channel Lifespan | Manual continuation each ~40h | Auto-extending forever |

## Architecture Overview

ComBreakDirect uses a clean "dock" architecture with three specialized processing areas, organized into modular subdirectories. The streaming architecture uses a **Studio → FIFO → Broadcast FFmpeg → BroadcastTower** pattern for continuous MPEG-TS streaming with multi-client support.

```
┌───────────────────────────────────────────────────────────────────────┐
│                  ComBreakDirect Server (Flask)                        │
│                         Port 8083 (default)                           │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────┐         │
│  │                   WebUI (UI/ subfolder)                 │         │
│  │  • Landing page with setup info                         │         │
│  └─────────────────────────────────────────────────────────┘         │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  ▼                 ▼                 ▼
        ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
        │  Loading Dock    │ │Factory Floor │ │ Unloading Dock   │
        │   (INPUT)        │ │ (WORK AREA)  │ │    (OUTPUT)      │
        │  (docks/)        │ │  (docks/)    │ │   (docks/)       │
        │                  │ │              │ │                  │
        │ • Ingests lineup │ │ • Stores     │ │ • Broadcast      │
        │ • Injects ads    │ │   channels   │ │   streaming      │
        │ • Pre-renders    │ │ • Generates  │ │ • Multi-client   │
        │   breaks         │ │   M3U8/XMLTV │ │ • Thin wrapper   │
        │                  │ │ • lineup.json│ │                  │
        └──────────────────┘ └──────────────┘ └──────────────────┘
                 │                   │                   ▲
                 └───────────────────┴───────────────────┘
                         Factory Pattern:
                Client → Loading (in) → Factory (work) → Unloading (out) → Client

  ┌─────────────────────────────────────────────────────────────────────┐
  │              Broadcasting Architecture (Unloading Dock)             │
  │                                                                     │
  │  ┌──────────┐    FIFO    ┌──────────────┐    ┌──────────────────┐ │
  │  │  Studio  │───Pipe────▶│  Broadcast   │───▶│ BroadcastTower   │ │
  │  │  Thread  │            │   FFmpeg     │    │  (Multi-client)  │ │
  │  └──────────┘            └──────────────┘    └──────────────────┘ │
  │      │                          │                      │           │
  │  Normalizes              Creates continuous      Distributes to    │
  │  & merges               stream with +genpts      multiple clients  │
  │  programs                                                          │
  │                                                                     │
  │  Studio → Spawns FFmpeg per program, writes to FIFO                │
  │  Broadcast FFmpeg → Reads FIFO, flattens transitions, rate limits  │
  │  BroadcastTower → Broadcasts to Antenna objects (one per client)   │
  │  Antenna → Client-specific buffer (132 chunks, ~2 sec)             │
  │                                                                     │
  │  Key Features:                                                      │
  │  • Multi-client support (multiple Antennas)                        │
  │  • Auto stop/start when clients connect/disconnect                 │
  │  • Continuous stream (no gaps at transitions)                      │
  │  • Rate limited broadcasting (~5.4 Mbps)                           │
  └─────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────┐
  │         Supporting Utilities (utilities/)              │
  │  • BroadcastTower - Multi-client streaming engine     │
  │  • AudioTrackSelector - Intelligent audio selection   │
  │  • CommercialBreakRenderer - Pre-rendering system     │
  │  • CleanupManager - Automatic file maintenance        │
  │  • configuration - Path resolution                    │
  └────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────┐
  │      Infinite Channel Extension (docks/ + ToonamiTools)│
  │  • LineupExtender (docks/) - Per-channel watchdog,    │
  │    one threading.Timer per channel, fires ahead of    │
  │    channel-end                                         │
  │  • InfiniteChannelExtender (ToonamiTools/) - One-shot │
  │    orchestrator: ShowScheduler + CutlessFinalizer     │
  │    against per-extension SQLite tables                │
  │  Spawned by FactoryFloor at store_channel time and    │
  │  on _load_channels restart. Wall-clock based — fires  │
  │  whether anyone is streaming or not.                  │
  └────────────────────────────────────────────────────────┘
```

### The Three Docks

#### 1. Loading Dock (`LoadingDock.py`)
**Purpose**: Processes incoming cutless lineup data and sends to Factory Floor

**Responsibilities**:
- Receives lineup data from `ComBreakToComBreakDirect`
- Injects commercial breaks between consecutive bumps
- Pre-renders commercial breaks for seamless playback
- Assigns BLOCK_IDs to all content
- Converts to streaming-ready format with timestamps
- **Automatically sends processed data to Factory Floor for storage**

**Key Methods**:
- `process_lineup(payload)` - Main pipeline orchestrator that processes AND stores
- `_inject_commercials(lineup_data, network_name, flex_duration)` - Finds consecutive bumps and inserts ads
- `_format_for_streaming(lineup_data, channel_number, network_name)` - Converts to channel format with timing
- `_format_programs(lineup_data, anchor_time)` - Inner program-builder extracted from `_format_for_streaming`; reused by `format_extension` to anchor extensions to an arbitrary moment instead of "now"
- `format_extension(lineup_data, existing_channel_data)` - Builds program dicts whose `start`/`stop` ISO timestamps pick up immediately after the existing channel's tail. Used by `LineupExtender` to splice new chunks into a running channel without breaking timeline continuity
- `_prime_initial_breaks()` - Warm-starts the pre-render cache for the first hour of breaks
- `update_commercial_folder(folder)` - Swaps the commercial library on-the-fly when a payload overrides it

**Infinite-channel handoff**: when the incoming payload includes `infinite: true`, LoadingDock stashes the metadata block as `channel_data['_infinite_meta']` with `enabled=True` before handing to FactoryFloor. FactoryFloor's `_maybe_spawn_extender` then arms a `LineupExtender` for the channel.

**Commercial Break Handling**:
- Break requests are queued during `_inject_commercials` and passed to `CommercialBreakRenderer`
- `plan_break` reserves output files in `_pre_rendered_breaks/`, while `pre_render_window` performs eager rendering
- Each break is stored as a `.ts` asset with cached metadata (`id`, `path`, `duration_ms`, and component commercials)

**Factory Flow**:
- LoadingDock creates FactoryFloor during initialization
- After processing, calls `factory_floor.store_channel()`
- Returns channel_number to server
- LoadingDock handles all coordination with FactoryFloor

#### 2. Factory Floor (`FactoryFloor.py`)
**Purpose**: Does ALL the work - generation, processing, storage, and maintenance

**Responsibilities**:
- **Channel Storage**: Persists channel data to `channels.json`
- **Playlist Generation**: Creates M3U8 master playlists
- **XMLTV Generation**: Builds EPG guides with show metadata
- **Lineup Generation**: Produces HDHomeRun channel lineup
- **Metadata Extraction**: Parses show info from file paths
- **BLOCK_ID Consolidation**: Groups program segments by show
- **Quality Term Cleaning**: Removes encoding info from episode titles
- **Factory Maintenance**: Runs CleanupManager for automatic file cleanup

**Key Methods**:

*Storage:*
- `store_channel(channel_data)` - Persists processed channel from Loading Dock. Triggers `_maybe_spawn_extender` after persisting so infinite channels get their watchdog armed
- `extend_channel(channel_number, new_programs)` - Append-only growth path used by `LineupExtender`. Takes the factory lock, extends `channel_data['programs']` (never replaces — the Studio loop reads the same list reference live), bumps `_infinite_meta.extension_seq`, stamps `last_extension_at`, and persists. Returns the new total program count or `None` if the channel was deleted mid-extension
- `get_channel(channel_number)` - Retrieves channel data for streaming
- `_load_channels()` - Loads persisted channels on startup. Walks loaded channels and respawns `LineupExtender` watchdogs for any with `_infinite_meta.enabled=true`
- `_save_channels()` - Atomically saves channels to disk. Strips ephemeral `_runtime` keys (Studio's `current_index` is re-derived from UTC clock on next startup, so the on-disk snapshot would be misleading)
- `_maybe_spawn_extender(channel_data)` - Spawns a `LineupExtender` if the channel has `_infinite_meta.enabled` truthy and FactoryFloor has a LoadingDock back-reference. Idempotent — won't double-spawn for the same channel

*Generation (called by UnloadingDock):*
- `generate_playlist(external_url)` - Creates M3U8 master playlist
- `generate_xmltv()` - Builds complete XMLTV guide
- `generate_lineup_json(request_host)` - Produces HDHomeRun lineup
- `_consolidate_programs_by_block_id(programs)` - Groups segments by show
- `_extract_show_metadata_from_block_id(programs, block_id)` - Parses episode info
- `_clean_episode_title(title)` - Removes quality terms from titles

*Maintenance:*
- Starts `CleanupManager` background thread on initialization
- CleanupManager handles cleanup of old segments and commercial breaks
- Cleanup runs every 5 minutes, removing files older than configured thresholds

**Note**: Factory Floor does the work - UnloadingDock just hands it out.

#### 3. Unloading Dock (`docks/UnloadingDock.py`)
**Purpose**: Manages continuous MPEG-TS broadcasting to multiple clients

**Responsibilities**:
- **Broadcast Streaming**: Continuous MPEG-TS via Studio → FIFO → Broadcast FFmpeg → BroadcastTower pattern
- **Multi-Client Support**: Handles multiple simultaneous viewers per channel
- **Lifecycle Management**: Auto start/stop based on client connections
- **Output Wrapper**: Calls FactoryFloor and returns metadata to clients

**Broadcasting Architecture**:

*Studio Thread (`build_stream`):*
- Calculates current channel position based on startTime
- Spawns FFmpeg per program with normalized settings (H.264 1080p 30fps, AAC stereo 48kHz, CBR 5.4 Mbps)
- Writes MPEG-TS chunks directly to FIFO (`/tmp/studio_ch{N}.fifo`)
- Simple read-write loop: `read from FFmpeg → write to FIFO`
- Stops on BrokenPipeError when broadcast FFmpeg disconnects

*Broadcast FFmpeg Process (`start_broadcast_ffmpeg`):*
- Reads from studio FIFO using `-fflags +genpts+discardcorrupt`
- **Creates continuous stream** by regenerating PTS across program transitions
- Copies stream (`-c copy`) without re-encoding
- Rate limits broadcasting to ~5.4 Mbps (13ms per chunk)
- Feeds chunks to BroadcastTower for distribution
- Stops when no clients connected (`broadcast_tower.has_antennas()` returns False)

*BroadcastTower (`BroadcastTower.py`):*
- Receives continuous stream from broadcast FFmpeg
- Distributes to multiple Antenna objects (one per client)
- No buffering at tower level - immediate broadcast
- Tracks active connections

*Antenna (per client):*
- Minimal signal buffer (132 chunks, ~2 seconds) for network stability
- Rate-limited iteration (13ms per chunk) prevents client buffering ahead
- Auto-disconnect detection

**Key Methods**:

*Broadcasting:*
- `create_studio_fifo(channel_number)` - Creates named pipe between studio and broadcast FFmpeg
- `start_broadcast_ffmpeg(channel_number, fifo_path, broadcast_tower)` - Starts continuous stream creation
- `build_stream(channel_data, fifo_path)` - Studio thread that normalizes and writes to FIFO
- `ensure_channel_ready(channel_number, channel_data)` - Ensures FIFO, studio, broadcast FFmpeg, and tower are running
- `connect_client(channel_number, client_id)` - Connects client antenna to broadcast tower

*Output Wrapper (thin layer):*
- `get_master_playlist(external_url)` → calls `factory_floor.generate_playlist()`
- `get_xmltv_guide()` → calls `factory_floor.generate_xmltv()`
- `get_lineup_json(request_host)` → calls `factory_floor.generate_lineup_json()`

**Lifecycle**:
1. First client connects → Creates FIFO, starts studio thread, starts broadcast FFmpeg, connects antenna
2. Additional clients → Reuses existing infrastructure, just adds new antenna
3. Last client disconnects → Broadcast FFmpeg detects no antennas, stops
4. Studio thread gets BrokenPipeError, stops
5. Next client → Everything restarts automatically

**Key Advantages**:
- **Truly continuous stream**: Broadcast FFmpeg's `+genpts` eliminates transition glitches
- **Multi-client**: Multiple viewers without conflicts
- **Resource efficient**: Only runs when clients connected
- **Simple architecture**: Direct FIFO communication, no complex buffering

### Supporting Components

#### WebUI System (`UI/WebUI.py`)
**Purpose**: Provides a Toonami-themed landing page with setup information

- `/` serves landing page with copy buttons for tuner URL, M3U8 playlist, and XMLTV guide
- Includes setup instructions for Plex and Jellyfin
- Styling matches the Absolution theme
- Lightweight for quick reference inside Docker

#### Audio Track Selector (`utilities/AudioTrackSelector.py`)
**Purpose**: Intelligent audio track selection for multi-audio video files

**Problem Solved**:
Anime often contains multiple audio tracks (Japanese, English dubs, commentary). The selector automatically chooses the appropriate audio track based on user preferences during HLS segment generation.

**Configuration**:
- **DEFAULT_LANGUAGE**: Set in `config.py` (defaults to 'english' for Toonami's English dub focus)
- **LANGUAGE_VARIATIONS**: Dictionary defining language tag variations (e.g., 'eng', 'en', 'english' for English)
- Supports multiple languages: English, Japanese, Spanish, and more

**Selection Logic**:
1. **Configured Language**: Searches for tracks matching the configured DEFAULT_LANGUAGE
2. **First Audio Track**: Fallback if no matching language found
3. **Audio Index Tracking**: Maintains consistency across segments

**Key Methods**:
- `find_best_audio_track(file_path, preferred_language)` - Analyzes file and returns optimal audio track index
- `get_audio_tracks(file_path)` - Uses FFprobe to enumerate available audio tracks
- `get_ffmpeg_audio_mapping(file_path)` - Generates FFmpeg arguments for audio selection

**Usage in Pipeline**:
- Called by `UnloadingDock` during segment generation
- Respects user's language preference from config.py
- Ensures consistent audio across all segments of an episode
- Handles files with missing or malformed audio metadata gracefully

**Example Configuration**:
```python
# In config.py
DEFAULT_LANGUAGE = 'english'  # or 'japanese', 'spanish', etc.
LANGUAGE_VARIATIONS = {
    'english': ['eng', 'english', 'en', 'en-us', 'en-gb'],
    'japanese': ['jpn', 'japanese', 'jp', 'ja']
}
```

#### Commercial Break Renderer (`utilities/CommercialBreakRenderer.py`)
**Purpose**: Pre-renders commercial breaks to avoid startup delays

**The Problem**: Originally, CommercialBreaker would try to render commercial breaks on-demand during streaming, causing:
- 30+ second delays when starting the channel
- Timeout issues with Plex
- Poor user experience

**The Solution**: Pre-rendering system that:
- Renders breaks ahead of time (1 hour window)
- Stores rendered breaks in `_pre_rendered_breaks/` folder
- Background thread maintains the break library
- Instant playback when commercial slots are needed

**Key Methods**:
- `plan_break(break_id, duration_ms)` - Creates break plan without rendering
- `pre_render_window(breaks, window_ms)` - Renders breaks for upcoming window
- `pre_render_upcoming_breaks(channel_data, hours_ahead)` - Proactive rendering
- `start_background_renderer(channels_callback)` - Continuous background rendering for pre-rendering

#### Cleanup Manager (`utilities/CleanupManager.py`)
**Purpose**: Automatic maintenance for temporary files

**What it does**:
- Periodically removes old HLS segment files (`.ts` files older than 15 minutes)
- Periodically removes old pre-rendered commercial breaks (older than 4 hours)
- Runs every 5 minutes in background
- Started by FactoryFloor on initialization

**Key Methods**:
- `start_cleanup_thread(segment_max_age_minutes, break_max_age_hours, cleanup_interval_minutes)` - Starts background cleanup
- `_cleanup_old_segments(max_age_minutes)` - Removes old HLS segment files
- `_cleanup_old_breaks(max_age_hours)` - Removes old pre-rendered commercial breaks

**Architecture**:
- Runs as part of FactoryFloor (factory maintenance)
- Single cleanup thread handles both segments and breaks
- Configurable age thresholds and cleanup intervals

#### Configuration Module (`configuration.py`)
**Purpose**: Resolves runtime paths for Docker and native environments

**Functions**:
- `resolve_data_root()` - Base data directory for ComBreakDirect
- `resolve_commercial_folder()` - Location of commercial break files
- `resolve_storage_path()` - Path to `channels.json` persistence

## Infinite Channel Extension

ComBreakDirect channels never end. Every time you create one, two coordinating pieces of plumbing keep the lineup growing forever:

### LineupExtender (`docks/LineupExtender.py`)

**Purpose**: Per-channel watchdog that fires extensions ahead of the channel's natural end time

One `LineupExtender` is spawned by `FactoryFloor._maybe_spawn_extender` for each channel that arrived with `_infinite_meta.enabled=true` — both at `store_channel` time for fresh channels and on `_load_channels` restart for channels recovered from `channels.json`.

It wraps **one `threading.Timer`** scheduled to fire `INFINITE_EXTEND_LEAD_MS` (default 3 hours, configurable via `config.py` or env) before the last program's `stop` ISO timestamp. When the timer fires:

1. Read the channel back out of FactoryFloor (race-check that it still exists)
2. Disk-space gate: skip if `combreak_direct_data` partition has less than `DEFAULT_MIN_FREE_DISK_BYTES` free (default 2 GB)
3. Call `_build_extension`, which delegates to `ToonamiTools.InfiniteChannelExtender`
4. Hand the new programs to `FactoryFloor.extend_channel`
5. Recompute the new channel-end and arm a fresh timer

**Safety paths**:
- Channels shorter than the lead time fire immediately (`delay=0`)
- Channels whose last program is already in the past fire immediately
- Channel was deleted during the long-running build → discard the new programs, cancel the watchdog
- Build raises → bump `_infinite_meta.consecutive_failures`, retry in `RETRY_AFTER_FAILURE_MS` (5 min)
- `MAX_CONSECUTIVE_FAILURES` (3) consecutive failures → set `_infinite_meta.enabled=false`, cancel watchdog, surface to `ErrorManager`. Studio's modulo loop keeps playing existing programs while infinite mode sleeps.

**Wall-clock anchored, not playback-anchored.** The timer counts down in real time regardless of whether anyone is currently streaming. A viewer who returns next week still finds fresh content waiting because the channel kept growing in the interim. Studio's `current_index` (which only advances while a client is connected) is published to `channel_data['_runtime']` but the watchdog deliberately ignores it.

**Lazy LoadingDock lookup**: `LineupExtender` takes the `FactoryFloor` reference at construction (not LoadingDock) and reaches LoadingDock lazily via `factory_floor.loading_dock` only when its timer fires. This sidesteps the bootstrap chicken-and-egg where `FactoryFloor.__init__` spawns watchdogs while `LoadingDock.__init__` is still mid-assignment of `self.factory_floor = FactoryFloor(...)`.

### InfiniteChannelExtender (`ToonamiTools/InfiniteChannelExtender.py`)

**Purpose**: One-shot orchestrator that builds a single extension chunk

Called by `LineupExtender._build_extension`. Reads the channel's `_infinite_meta` for the `toonami_version` key, then:

1. Looks up `config.TOONAMI_CONFIG_CONT[version]` to get the encoder + bump-list table names
2. Constructs a per-extension output table name: `{merger_out}_inf_ch{channel}_ext{seq}` (e.g., `lineup_v9_cont_inf_ch61_ext3`). Each chunk lives in its own SQLite table so individual extensions stay debuggable in isolation
3. Runs `ShowScheduler(reuse_episode_blocks=True, continue_from_last_used_episode_block=True, uncut=...)` against the new output table — the per-show cursor in `last_used_episode_block` advances naturally
4. If cutless mode is enabled (always true for ComBreakDirect), runs `CutlessFinalizer.run_for_table(input_table, output_table)` to produce the `_cutless` companion
5. Loads the rows via the shared `load_lineup_rows(table)` helper (the same one `ComBreakToComBreakDirect` uses for the initial channel POST)
6. Returns `(rows, output_table)` for the caller to format and append

If ShowScheduler produces zero rows (cursor exhausted with `reuse_episode_blocks=True` shouldn't happen, but) the caller treats it as a hard failure and disables infinite mode for the channel.

### Episode-cursor seeding

For the *first* extension of a channel to actually continue the timeline (Bleach S01E01 in the original chunk → Bleach S01E02 in the extension, not S01E10 or S01E01 again), the `last_used_episode_block` cursor table needs to know where the original lineup ended.

`ComBreakToComBreakDirect._seed_episode_cursor` handles this. Before POSTing the lineup to ComBreakDirect, it:

1. Sweeps the loaded lineup rows and derives a show-key → BLOCK_ID map (max BLOCK_ID per show)
2. Derives each show key via `show_name_mapper.clean(show_name_mapper.map(name), mode='matching')` to match ShowScheduler's exact internal format — derive it any other way and the cursor lookup will silently miss
3. Merges with any existing `last_used_episode_block` entries, taking the larger BLOCK_ID per show (never rolls a cursor backwards just because a new channel was built from earlier content)

Without this seed step the first extension would treat every show as "no prior position" and pick whatever ShowScheduler's index has at position 0 — usually NOT the next episode the viewer expects.

### Per-channel state (`_infinite_meta`)

Stored on the channel dict, persisted in `channels.json`:

```json
{
  "_infinite_meta": {
    "enabled": true,
    "toonami_version": "OG",
    "cutless_enabled": true,
    "network": "Toonami",
    "flex_duration_ms": 260000,
    "commercial_folder": "/app/commercials",
    "extension_seq": 3,
    "last_extension_at": "2026-05-28T15:01:17Z",
    "consecutive_failures": 0
  }
}
```

`enabled` is the master kill switch — the `LineupExtender` self-disables here on hard failure. `extension_seq` increments on each successful extension and feeds the per-chunk SQLite table naming.

### Configuration knob

- `INFINITE_EXTEND_LEAD_MS` (default 10 800 000 ms = 3 hours, env-overridable) — how long before the last program's stop to fire the extension. Tuned so ShowScheduler + CutlessFinalizer + initial pre-rendering all finish well before a viewer would actually hit the seam, with margin for one retry on transient failure.

## API Endpoints

ComBreakDirect exposes a RESTful API for channel management, streaming, and web interface:

### WebUI Routes

#### `GET /`
Toonami-themed landing page with setup information.

**Features**:
- Copy buttons for tuner URL, M3U8 playlist, and XMLTV guide
- Setup instructions for Plex and Jellyfin
- Direct streaming URL examples
- Lightweight control panel for Docker deployments

### Channel Management

#### `POST /channels`
Create or update a channel with lineup data.

**Request Body**:
```json
{
  "channel_number": 1,
  "network": "Toonami",
  "lineup": [
    {
      "block_id": "NARUTO_S01E01",
      "file_path": "/path/to/Naruto - S01E01.mkv",
      "code": "V2-P1:BCK-S1:NAR",
      "start_time": 0,
      "end_time": 432000,
      "duration": 1440000
    }
  ],
  "flex_duration": 150000,
  "commercial_folder": "/path/to/commercials",
  "infinite": true,
  "infinite_meta": {
    "toonami_version": "OG",
    "cutless_enabled": true,
    "commercial_folder": "/path/to/commercials"
  }
}
```

The `infinite` flag tells `LoadingDock` to stash a populated `_infinite_meta` block on the channel, which `FactoryFloor._maybe_spawn_extender` reads to arm the per-channel `LineupExtender` watchdog. `toonami_version` is the key into `config.TOONAMI_CONFIG_CONT` so subsequent extensions know which encoder + bump-list tables to feed ShowScheduler.

`ComBreakToComBreakDirect` sets `infinite=True` automatically for all ComBreakDirect channels — clients don't need to opt in.

**Response**:
```json
{
  "success": true,
  "channel_number": 1,
  "playlist_url": "http://localhost:8083/playlist.m3u",
  "guide_url": "http://localhost:8083/api/xmltv.xml"
}
```

### Playlist Generation

#### `GET /playlist.m3u8`
Generate M3U8 playlist for all channels (HLS-compatible).

**Response**:
```
#EXTM3U url-tvg="http://localhost:8083/api/xmltv.xml"
#EXTINF:0 tvg-id="1" tvg-chno="1" tvg-name="Toonami" group-title="ComBreakDirect",Toonami
http://localhost:8083/video/channel/1
```

**Note**: `/playlist.m3u` is also supported for backward compatibility but returns the same M3U8 format.

#### `GET /api/xmltv.xml`
Generate XMLTV guide with show metadata.

**Response**:
```xml
<?xml version="1.0" ?>
<tv generator-info-name="ComBreakDirect">
  <channel id="1">
    <display-name lang="en">Toonami</display-name>
  </channel>
  <programme start="20250109120000 +0000" stop="20250109123000 +0000" channel="1">
    <title lang="en">Naruto</title>
    <sub-title lang="en">Eat or Be Eaten</sub-title>
    <desc lang="en">Naruto - Season 1, Episode 28: Eat or Be Eaten</desc>
    <episode-num system="onscreen">S01E28</episode-num>
    <episode-num system="xmltv_ns">0.27.0/1</episode-num>
    <category lang="en">Animation</category>
  </programme>
</tv>
```

### Continuous MPEG-TS Streaming

#### `GET /video/channel/{number}`
**Continuous MPEG-TS broadcast stream** using BroadcastTower architecture.

**Example**: `/video/channel/1`

**Response**: Continuous MPEG-TS stream

**Headers**:
- `Content-Type: video/mp2t`
- `Cache-Control: no-cache`
- `Access-Control-Allow-Origin: *`

**Architecture**:
Each client connection creates a dedicated Antenna that receives from the BroadcastTower:

1. **Studio Thread**: Normalizes programs to H.264 1080p 30fps, AAC stereo 48kHz, writes to FIFO
2. **Broadcast FFmpeg**: Reads FIFO with `+genpts`, creates truly continuous stream
3. **BroadcastTower**: Distributes stream to all connected Antennas
4. **Antenna**: Client-specific buffer (132 chunks, ~2 seconds) with rate limiting

**Features**:
- **Multi-client support**: Multiple viewers can watch simultaneously
- **Truly continuous**: Broadcast FFmpeg's `+genpts` eliminates transition glitches
- **Auto start/stop**: Studio and broadcast FFmpeg only run when clients connected
- **Live positioning**: All clients synchronized to same position in channel
- **Resource efficient**: Single studio feeds all clients via broadcast tower

**Stream Characteristics**:
- **Format**: MPEG-TS (Transport Stream)
- **Video**: H.264, 1080p, 30fps
- **Audio**: AAC stereo, 48kHz
- **Bitrate**: CBR ~5.4 Mbps
- **Chunk size**: 9400 bytes (188-byte packets × 50)
- **Rate limiting**: 13ms per chunk (~75 chunks/second)

**Use Case**: Plex/Jellyfin Live TV integration via HDHomeRun emulation

### Plex Discovery (HDHomeRun Emulation)

#### `GET /discover.json`
HDHomeRun-style device discovery for Plex.

**Response**:
```json
{
  "FriendlyName": "ComBreakDirect",
  "Manufacturer": "CommercialBreaker",
  "ModelNumber": "HDTC-2US",
  "FirmwareVersion": "1.0.0",
  "TunerCount": 1,
  "BaseURL": "http://localhost:8083",
  "LineupURL": "http://localhost:8083/lineup.json"
}
```

#### `GET /lineup.json`
Channel lineup for Plex.

**Response**:
```json
[
  {
    "GuideNumber": "1",
    "GuideName": "Toonami",
    "URL": "http://localhost:8083/video/channel/1"
  }
]
```

#### `GET /lineup_status.json`
Lineup status for Plex.

**Response**:
```json
{
  "ScanInProgress": 0,
  "ScanPossible": 1,
  "Source": "Cable",
  "SourceList": ["Cable"]
}
```

### Status

#### `GET /status`
Server status and channel information.

**Response**:
```json
{
  "status": "running",
  "version": "ComBreakDirect-Clean",
  "factory_floor": {
    "channels": 1,
    "storage_path": "/path/to/channels.json"
  }
}
```

## Installation & Setup

### Prerequisites

- Python 3.11+
- FFmpeg with MPEG-TS support
- Cutless mode database from CommercialBreaker

### Configuration

Add these settings to your `config.py`:

```python
# ComBreakDirect Configuration
CBDIRECT_HOST = os.environ.get("CBDIRECT_HOST", "0.0.0.0")
CBDIRECT_PORT = int(os.environ.get("CBDIRECT_PORT", "8083"))
CBDIRECT_BASE_URL = os.environ.get("CBDIRECT_BASE_URL", f"http://127.0.0.1:{CBDIRECT_PORT}")
CBDIRECT_DATA_ROOT = os.environ.get("CBDIRECT_DATA_ROOT") or os.path.join(os.path.dirname(__file__), "combreak_direct_data")
CBDIRECT_STORAGE_PATH = os.environ.get("CBDIRECT_STORAGE_PATH") or os.path.join(CBDIRECT_DATA_ROOT, "channels.json")
COMMERCIAL_FOLDER = os.environ.get("COMMERCIAL_FOLDER") or os.path.join(CBDIRECT_DATA_ROOT, "commercials")
```

### Running the Server

#### Standalone Mode

```bash
python3 -m ComBreakDirect.run_server
```

The server will start on `http://0.0.0.0:8083` by default.

#### Docker Mode

ComBreakDirect starts automatically with the Docker container:

```bash
docker run -p 8081:8081 -p 8083:8083 \
  -v "/path/to/anime:/app/anime" \
  -v "/path/to/bumps:/app/bump" \
  -v "/path/to/commercials:/app/commercials" \
  -v "/path/to/working:/app/working" \
  tim000x3/commercial-breaker:latest
```

The startup script launches ComBreakDirect in the background before starting the WebUI.

### Creating a Channel

#### Via TOM/Absolution GUI

1. Select "ComBreakDirect" as your platform type (Page 1)
2. Complete the normal workflow (prepare content, run commercial breaker, etc.)
3. On the "Create Channel" page:
   - ComBreakDirect will be auto-selected if it was chosen earlier
   - The server URL will be pre-filled
   - Enter channel number and flex duration
   - Click "Create Channel"

The GUI automatically:
- Starts the ComBreakDirect server if not running
- Waits for server readiness
- Pushes your lineup to the server
- Provides playlist and guide URLs

#### Via ComBreakToComBreakDirect API

```python
from ToonamiTools import ComBreakToComBreakDirect

# Create client
client = ComBreakToComBreakDirect(
    table="lineup_v8_cutless",
    channel_number=1,
    flex_duration=150000,  # milliseconds or "MM:SS"
    network="Toonami",
    base_url="http://localhost:8083",
    commercial_folder="/path/to/commercials"
)

# Push lineup
client.run()
```

## Usage with Plex

ComBreakDirect provides HDHomeRun-style discovery, making it easy to integrate with Plex:

### Adding to Plex

1. **Open Plex Settings** → **Live TV & DVR**
2. **Click "Set Up Plex DVR"**
3. Plex should automatically discover "ComBreakDirect"
4. **Select the device** and click "Continue"
5. **Select your country** and postal code
6. **Choose channels** - Your ComBreakDirect channels will appear
7. **Complete setup** - Plex will download the guide data

### Manual Setup (if auto-discovery fails)

1. Open Plex Settings → Live TV & DVR
2. Click "Set Up Plex DVR" → "Have an HDHomeRun?"
3. Enter the ComBreakDirect server URL: `http://YOUR_IP:8083`
4. Continue with setup as above

### Viewing Your Channel

- Go to **Live TV** in Plex
- Your Toonami channel will appear with full EPG data
- Click to watch - stream starts playing with commercial breaks
- Use the guide to see what's currently playing and what's coming up

## Technical Deep Dive

### Broadcasting Architecture

ComBreakDirect uses a **Studio → FIFO → Broadcast FFmpeg → BroadcastTower** pattern for continuous MPEG-TS streaming with multi-client support.

**Why This Architecture?**:
- **Truly Continuous**: Broadcast FFmpeg's `+genpts` regenerates PTS across program transitions
- **Multi-Client**: BroadcastTower distributes to multiple Antennas simultaneously
- **Resource Efficient**: Single studio feeds all clients, auto stops when idle
- **Simple Communication**: FIFO pipes for inter-process streaming
- **No Buffering**: Live broadcast only, clients join at current position

### Studio Thread (The Tape)

The studio thread has the "full tape" and continuously builds the channel stream:

**Responsibilities**:
1. Calculate current channel position based on `startTime` (UTC timestamp)
2. Find which program should be playing RIGHT NOW
3. Spawn FFmpeg to transcode from correct position
4. Normalize video/audio settings for consistency
5. Write MPEG-TS chunks to FIFO
6. Loop through programs, wrap around when channel ends

**Normalization Settings**:
```bash
ffmpeg -ss <seek_position> -i <file> -t <duration>
  # Video normalization
  -c:v libx264 -preset ultrafast
  -r 30  # 30 fps
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1,setsar=1,setdar=16/9"

  # Audio normalization
  -c:a aac -ar 48000 -ac 2  # AAC stereo 48kHz
  -map 0:v:0 -map 0:a:<selected>

  # MPEG-TS output
  -f mpegts -muxrate 5400k  # CBR 5.4 Mbps
  pipe:1
```

**FIFO Communication**:
- Simple read-write loop: `read from FFmpeg stdout → write to FIFO`
- Stops on `BrokenPipeError` when broadcast FFmpeg disconnects
- No buffering - direct streaming

### Broadcast FFmpeg Process

Broadcast FFmpeg sits between studio and BroadcastTower, creating the continuous stream:

**Purpose**:
- Reads from FIFO with `-fflags +genpts+discardcorrupt`
- Regenerates presentation timestamps across program transitions
- Eliminates glitches that freeze Jellyfin/Plex at transitions
- Rate limits broadcasting to ~5.4 Mbps

**Command**:
```bash
ffmpeg -fflags +genpts+discardcorrupt -i <fifo_path>
  -c copy  # No re-encoding
  -f mpegts -muxdelay 0 -muxpreload 0
  pipe:1
```

**Rate Limiting**:
- Reads 9400-byte chunks (188-byte packets × 50)
- Waits 13ms between chunks (~5.4 Mbps)
- Prevents antenna buffer overflow
- Only broadcasts when tower has antennas

**Lifecycle**:
- Starts when first client connects
- Stops when last client disconnects (detected via `broadcast_tower.has_antennas()`)
- Auto-restart on reconnection

### Channel Timing Algorithm

The timing algorithm ensures perfect synchronization across all clients:

**Key Concepts**:
- **Channel Start Time**: Absolute UTC timestamp when channel began (`startTime`)
- **Elapsed Time**: Milliseconds since channel start, modulo total channel duration
- **Current Position**: Determines which program should be playing RIGHT NOW
- **Program Lookup**: Finds program containing current timestamp

**Algorithm Flow**:
```python
# 1. Get current UTC time
now = datetime.now(timezone.utc).timestamp() * 1000

# 2. Calculate elapsed time since channel start
elapsed_ms = int((now - channel_start_ms) % total_duration_ms)

# 3. Find program containing this timestamp
for program in programs:
    if program['start_ms'] <= elapsed_ms < program['end_ms']:
        # This is the current program
        program_offset_ms = elapsed_ms - program['start_ms']
        seek_position = program.get('seek_ms', 0) + program_offset_ms
        break

# 4. Spawn FFmpeg starting from seek_position
# 5. Play program to completion, move to next
```

**Wrap-around Handling**:
- When `elapsed_ms` exceeds `total_duration_ms`, it wraps to 0
- Creates seamless 24/7 looping channel
- All clients synchronized regardless of connection time

### BroadcastTower Multi-Client Distribution

The BroadcastTower provides true multi-client streaming like a TV broadcast tower:

**Architecture**:
```
                    ┌─────────────────┐
                    │ Broadcast FFmpeg│
                    │   (continuous   │
                    │     stream)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ BroadcastTower  │
                    │   .broadcast()  │
                    └─┬──────┬──────┬─┘
                      │      │      │
              ┌───────▼─┐ ┌──▼──┐ ┌▼───────┐
              │Antenna 1│ │Ant 2│ │Antenna3│
              │(Client 1)│ │(Cl2)│ │(Client3)│
              └─────────┘ └─────┘ └────────┘
```

**BroadcastTower Responsibilities**:
- Receives continuous stream from broadcast FFmpeg
- Distributes chunks to ALL connected Antennas immediately
- NO BUFFERING - only transmits what's broadcasting NOW
- Tracks active connections
- Provides `has_antennas()` check for lifecycle management

**Antenna (Per-Client Buffer)**:
- Each client gets dedicated Antenna object
- Minimal buffer: 132 chunks (~2 seconds at 66 chunks/sec)
- Rate-limited iteration: 13ms per chunk prevents client buffering ahead
- Auto-disconnect detection via `active` flag
- Tracks "signal lost" when buffer overflows (client too slow)

**Key Implementation Details**:
```python
class BroadcastTower:
    def broadcast(self, chunk: bytes):
        """Send chunk to ALL antennas (no buffering)."""
        for antenna in self.antennas:
            antenna.receive(chunk)  # Add to antenna's buffer

class Antenna:
    def __iter__(self):
        """Yield chunks with rate limiting."""
        chunk_interval = 0.013  # 13ms per chunk
        while self.active:
            chunk = self.read_signal(timeout=30.0)
            if chunk:
                time.sleep(chunk_interval)  # Rate limit
                yield chunk
```

**Why This Works**:
- **No buffering at tower**: Prevents clients from buffering way ahead
- **Small antenna buffer**: Just enough for network stability (~2 seconds)
- **Rate limiting**: Forces real-time consumption
- **Live join**: New clients join at current broadcast position
- **Resource efficient**: Single studio + broadcast FFmpeg feed all clients

### Commercial Break System

#### Problem Statement
When creating authentic Toonami blocks, commercial breaks need to appear between consecutive bumps. However, rendering these on-demand causes unacceptable delays.

#### Solution Architecture

**Phase 1: Planning (Loading Dock)**
- Detects consecutive bumps in the lineup
- Generates unique break IDs: `break_{BLOCK_ID}_{network}_{end_marker}_{flex_duration}`
- Creates placeholder entries in the channel data

**Phase 2: Pre-rendering (Commercial Break Renderer)**
- Renders the first 1 hour of breaks immediately after channel creation
- Concatenates random commercials to match flex duration
- Stores in `_pre_rendered_breaks/` folder
- Each break is a single MP4 file ready to stream

**Phase 3: Background Maintenance**
- Background thread monitors all channels
- Pre-renders breaks 1 hour ahead of playback
- Maintains a library of ready-to-stream breaks
- Cleanup of old breaks that won't be needed

**Phase 4: Streaming (Studio Thread)**
- Studio thread encounters break in program list
- Spawns FFmpeg to stream the pre-rendered file
- No delay - file is already prepared
- Writes to FIFO like any other program

### XMLTV Metadata Extraction

ComBreakDirect extracts show metadata directly from file paths to populate the guide:

**Filename Pattern**: `Show Name - S01E01 - Episode Title.mkv`

**Extraction Process**:
1. Scan all programs in a BLOCK_ID group
2. Find anime files (those with start/end times, not bumps)
3. Parse filename with regex: `r'\s-\s[Ss](\d+)[Ee](\d+)\s-\s(.+?)\.'`
4. Extract season number, episode number, and episode title
5. Clean episode title by removing quality terms (Bluray, 1080p, etc.)
6. Consolidate all segments of the same show into one guide entry

**Result**: Plex displays "Naruto - Season 1, Episode 28: Eat or Be Eaten" instead of "Toonami - Part 5"

### Video Quality Term Cleaning

The `_clean_episode_title()` method removes common video quality terms that pollute episode titles:

```python
VIDEO_QUALITY_TERMS = [
    'Bluray', 'BluRay', 'BD', 'BDRip', 'BDMV',
    'WebDL', 'WEB-DL', 'WebRip', 'WEBRip', 'WEB',
    'HDTV', 'SDTV', 'DVDRip', 'DVD', 'DVDR',
    '2160p', '1080p', '720p', '480p',
    'x264', 'x265', 'h264', 'h265', 'HEVC',
    'DTS', 'DTS-HD', 'TrueHD', 'Atmos', 'AC3',
    'v2', 'v3', 'REPACK', 'PROPER'
]
```

Only terms at the very end of the title (after separators) are removed, preserving legitimate uses in episode titles.

## Troubleshooting

### Server Won't Start

**Symptoms**: `ComBreakDirect server failed to start` error

**Solutions**:
1. Check port 8083 is not in use: `lsof -i :8083` (macOS/Linux) or `netstat -ano | findstr :8083` (Windows)
2. Verify FFmpeg is in PATH: `ffmpeg -version`
3. Check permissions on data directories
4. Review logs for specific error messages

### Channel Shows "Unknown"

**Symptoms**: Channel appears but has no name or guide data

**Solutions**:
1. Verify `channels.json` was created: check `CBDIRECT_DATA_ROOT/channels.json`
2. Ensure lineup includes `network` field
3. Check XMLTV generation endpoint: `http://localhost:8083/api/xmltv.xml`
4. Verify file paths in lineup are accessible

### Buffering or Playback Issues

**Symptoms**: Stream buffers frequently, freezes at transitions, or stops

**Solutions**:
1. **Check studio thread**: Look for FFmpeg errors in server logs with `[STUDIO]` prefix
2. **Check broadcast FFmpeg**: Look for `[BROADCAST_FFMPEG]` messages, ensure it's running
3. **Verify FIFO exists**: Check `/tmp/studio_ch{N}.fifo` exists when streaming
4. **Check antenna buffer**: Look for "lost signal" messages indicating client can't keep up
5. **Test streaming endpoint**: `curl http://localhost:8083/video/channel/1 > test.ts` should create growing file
6. **Verify file paths**: Ensure all program file paths are absolute and accessible
7. **Check network bandwidth**: ~5.4 Mbps required per client
8. **Review BroadcastTower stats**: Look for `[BROADCAST_TOWER]` messages showing active antennas

**Transition Issues** (freezing between programs):
- Broadcast FFmpeg is CRITICAL - without it, transitions will freeze Jellyfin
- Check broadcast FFmpeg is using `+genpts` flag
- Verify rate limiting (13ms per chunk) is working
- Look for BrokenPipeError in studio logs (indicates disconnection)

### Commercial Breaks Not Appearing

**Symptoms**: Channel plays but no commercials between bumps

**Solutions**:
1. Verify `COMMERCIAL_FOLDER` contains commercial files
2. Check `flex_duration` was provided during channel creation
3. Look for pre-rendered breaks: `ls CBDIRECT_DATA_ROOT/_pre_rendered_breaks/`
4. Review `_inject_commercials()` logic - are bumps consecutive?
5. Check `CommercialBreakRenderer` logs

### Plex Discovery Not Working

**Symptoms**: Plex doesn't find ComBreakDirect automatically

**Solutions**:
1. Verify Plex and ComBreakDirect are on same network
2. Check firewall isn't blocking port 8083
3. Test discovery endpoint manually: `http://localhost:8083/discover.json`
4. Use manual setup with server URL
5. Ensure `CBDIRECT_BASE_URL` is accessible from Plex

### Guide Shows Wrong Information

**Symptoms**: Episode titles or show names incorrect in guide

**Solutions**:
1. Verify filename format matches pattern: `Show - S##E## - Title.ext`
2. Check `VIDEO_QUALITY_TERMS` list is complete
3. Review `_extract_show_metadata_from_block_id()` logic
4. Ensure BLOCK_IDs are assigned correctly in lineup
5. Test XMLTV generation and inspect output

## Performance Considerations

### Startup Time

**Cold Start**: ~30 seconds
- Commercial break pre-rendering: 25-28 seconds
- Channel data loading: 1-2 seconds
- Server initialization: <1 second

**Warm Start** (server already running): <1 second
- Channel creation is instant if server is running
- Only lineup processing and database update needed

**First Client Connection**: <3 seconds
- Studio FIFO creation: <100ms
- Studio thread startup and position calculation: 1-2 seconds
- Broadcast FFmpeg startup: <500ms
- BroadcastTower initialization: <100ms

### Memory Usage

**Baseline**: ~50-100 MB
- Flask server: 30-40 MB
- Channel data: 10-20 MB (per channel)
- Pre-rendered breaks cache: 20-40 MB

**Per Active Channel** (with clients connected):
- Studio thread: ~20-30 MB
- Broadcast FFmpeg: ~10-20 MB
- BroadcastTower: ~5 MB
- Each Antenna: ~1-2 MB (132 chunks × 9.4KB)

**Scaling**: Memory grows with active channels and client count
- Each idle channel: ~10-20 MB (data only, no streaming)
- Each active channel: ~40-60 MB (streaming infrastructure)
- Each additional client: ~1-2 MB (one Antenna)

### CPU Usage

**Per Active Channel**:
- Studio FFmpeg transcoding: 1-2 cores (H.264 encoding with ultrafast preset)
- Broadcast FFmpeg: <0.1 cores (copy mode, minimal overhead)
- BroadcastTower: <0.05 cores (chunk distribution)

**Multi-Client Efficiency**:
- Adding clients has MINIMAL CPU impact
- Studio transcodes once, BroadcastTower distributes to all
- No per-client transcoding

### Network Bandwidth

**Per Client**: ~5.4 Mbps (constant bitrate)
- MPEG-TS streaming with CBR muxrate
- H.264 1080p 30fps, AAC stereo 48kHz
- Rate-limited to prevent buffering ahead

**Per Channel** (regardless of client count):
- Studio → Broadcast FFmpeg: ~5.4 Mbps via FIFO (local, no network)
- Broadcast FFmpeg → Clients: ~5.4 Mbps × client_count (network)

### Disk I/O

**Read Operations**:
- Studio: Sequential reads for video streaming (one FFmpeg per program)
- Random reads for seek operations (finding current position)
- Pre-rendered breaks: Sequential reads

**Write Operations**:
- Commercial break rendering (periodic, background)
- Channel data persistence (infrequent)
- FIFO writes (in-memory pipes, not disk)
- Minimal disk writes during streaming

## Best Practices

### Commercial Break Library

1. **Organize by Duration**: Group commercials by length (15s, 30s, 60s)
2. **Maintain Variety**: Include diverse content to avoid repetition
3. **Check Formats**: Ensure all commercials are compatible formats (MP4, MKV)
4. **Test Rendering**: Run server once to pre-render all breaks
5. **Monitor Disk**: Pre-rendered breaks can accumulate (cleanup old channels)

### Channel Configuration

1. **Start Small**: Test with one channel before scaling
2. **Reasonable Flex**: 2-3 minutes (120000-180000ms) is typical
3. **Clean Filenames**: Follow naming conventions strictly
4. **Verify Paths**: Ensure all file paths are absolute and accessible
5. **Monitor Logs**: Check for errors during lineup processing

### Plex Integration

1. **Network Location**: Keep ComBreakDirect on same network as Plex
2. **Port Forwarding**: Not required for local network
3. **Guide Refresh**: Plex updates guide every ~30 minutes
4. **Recording**: Not supported (live stream only)
5. **Multiple Channels**: Plex handles multiple ComBreakDirect channels well

### Production Deployment

1. **Use Docker**: Simplifies deployment and dependencies
2. **Persistent Storage**: Mount volumes for `CBDIRECT_DATA_ROOT`
3. **Monitoring**: Set up logging and health checks
4. **Backup**: Regularly backup `channels.json`
5. **Firewall**: Only expose port 8083 if needed externally

## Limitations

### Current Limitations

1. **Single Server Instance**: No horizontal scaling support (one BroadcastTower per channel)
2. **No Recording**: Live streaming only, no DVR functionality
3. **Live Join Only**: Clients always join at current channel position, no seeking back
4. **Limited Codec Support**: Studio normalizes all content (transcoding overhead)
5. **FIFO Platform Dependency**: Requires Unix-like OS with named pipe support

### Platform Limitations

1. **Cutless Only**: Designed for virtual cuts, not physical file parts
2. **Plex DVR Limitations**: Some Plex DVR features unavailable (no recording)
3. **Network Dependency**: Requires network access to media files
4. **FFmpeg Dependency**: Requires system FFmpeg installation with H.264 and AAC support

### Known Issues

1. **Startup Delay**: ~30s startup time for commercial pre-rendering (first channel creation)
2. **First Connection Delay**: 1-3s delay while studio calculates position and starts streaming
3. **Studio Crash Recovery**: If studio thread crashes, requires manual channel restart
4. **Broadcast FFmpeg Critical**: Without broadcast FFmpeg, transitions freeze Jellyfin
5. **Audio Selection**: Manual configuration required for non-standard audio layouts
6. **Subprocess vs Thread bootstrap race**: In Docker mode `start.sh` launches `run_server.py` as a subprocess at boot; in desktop mode Absolution spawns CBD as a thread. If the canonical instance crashes mid-startup (e.g., the historical `_load_existing_breaks` listdir/stat race on stale `_seg_*.mkv` files — hardened in `CommercialBreakRenderer.py` to skip missing files), the fallback may take over with a different storage path. Cleanup any stale temp `_seg_*.mkv` files before a clean restart.

## Contributing

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/CommercialBreaker.git
cd CommercialBreaker

# Checkout ComBreakDirect branch
git checkout ComBreakDirect

# Install dependencies
pip install -r requirements.txt

# Run server in development mode
python3 -m ComBreakDirect.run_server
```

### Testing

```bash
# Run S.A.R.A. tests (includes duration manager mocking)
pytest tests/test_sara_automatic.py -v -s

# Test server endpoints
curl http://localhost:8083/status
curl http://localhost:8083/discover.json
curl http://localhost:8083/playlist.m3u
```

### Code Style

Follow the existing patterns:
- Use `print()` statements with `[DOCK_NAME]` prefixes for logging
- Keep dock responsibilities separate (Loading, Factory, Unloading)
- Document all major functions and classes

## Conclusion

ComBreakDirect represents a significant evolution in CommercialBreaker's architecture. By eliminating the dependency on third-party platforms and providing direct continuous MPEG-TS streaming, it offers:

- **Simpler deployment** (one self-contained server)
- **Better control** (own the entire streaming stack)
- **Faster iteration** (no external platform limitations)
- **Native Plex/Jellyfin integration** (HDHomeRun emulation)
- **Multi-client support** (BroadcastTower architecture)
- **Truly continuous streaming** (Broadcast FFmpeg flattens transitions)
- **Integrated landing page** (setup shortcuts with copy-to-clipboard links)
- **Modular architecture** (clean dock separation)

**Current Architecture (Studio → FIFO → Broadcast FFmpeg → BroadcastTower)**:
- **Continuous MPEG-TS Streaming**: True broadcast-style streaming with seamless transitions
- **BroadcastTower Pattern**: Efficient multi-client distribution (one transcode, multiple viewers)
- **Intelligent Audio Selection**: Configurable audio track selection (defaults to English for Toonami)
- **Resource Efficient**: Auto start/stop based on client connections
- **Rate Limited Broadcasting**: Prevents client buffering ahead (~5.4 Mbps CBR)
- **Commercial Pre-rendering**: Instant break playback with background maintenance
- **Infinite Channel Extension**: Per-channel `threading.Timer` arms ahead of channel-end, fires ShowScheduler+CutlessFinalizer to append a fresh chunk, and reschedules itself — wall-clock based, fires whether anyone is streaming or not. A single channel created once stays alive indefinitely.

**Key Technical Achievement**:
The addition of Broadcast FFmpeg with `+genpts` flag solved the critical transition glitch issue that froze Jellyfin/Plex between programs. This creates a truly continuous stream by regenerating presentation timestamps across program boundaries.

ComBreakDirect is production-ready and offers compelling advantages for users who want a self-contained, professional-grade streaming solution with authentic Toonami experience and multi-client support.

---

*For questions or issues, please visit the [GitHub Issues](https://github.com/yourusername/CommercialBreaker/issues) page.*
