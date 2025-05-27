# User Guides

Choose your preferred interface to get started with CommercialBreaker & Toonami Tools.

## Interface Overview

### TOM (Toonami Operations Module) - Recommended
The primary GUI interface that provides the most complete and user-friendly experience. Perfect for first-time users and regular operation.

### Absolution (Web Interface)
A web-based interface designed for Docker deployments and remote access. Ideal for server installations.

### Clydes (Command Line Interface)
A question-based CLI for users who prefer terminal interactions or need scriptable automation.

---

## TOM User Guide

**Command**: `python3 main.py --tom`

TOM is your mission control for creating Toonami channels. It guides you through the entire process with a intuitive GUI.

### Getting Started with TOM

#### Phase 1: Plex Setup

**Step 1: Login to Plex**
- Click "Login with Plex"
- A browser window opens - log into your Plex account
- Click "Allow" when prompted
- Close the success window

**Step 2: Select Plex Server**
- Use the dropdown to select your Plex server
- Even with one server, you may need to click the dropdown

**Step 3: Choose Libraries**
- **Anime Library**: Your existing anime collection (for intro timestamps)
- **Toonami Library**: Create a new library for cut content and bumps

**Step 4: Select Platform**
- Choose between **DizqueTV** or **Tunarr**
- Enter your platform's URL (e.g., `http://192.168.1.100:3000`)

**Pro Tip**: Toggle dark mode with the button in the bottom-left corner.

#### Phase 2: Folder Configuration

**Step 1: Anime Folder**
- Click "Browse Anime Folder"
- Select your main anime collection directory

**Step 2: Bumps Folder**
- Click "Browse Bumps Folder"  
- Select directory containing Toonami bumps and transitions

**Step 3: Special Bumps Folder**
- Click "Browse Special Bumps Folder"
- Select directory with music videos, game reviews, etc.

**Step 4: Working Folder**
- Click "Browse Working Folder"
- Choose processing workspace (where cut files or metadata will be stored)

#### Phase 3: Content Preparation

**Step 1: Prepare Content**
- Click "Prepare Content"
- A popup shows available Toonami shows from your library
- Uncheck shows you don't want in your channel
- Choose processing mode:
  - **Move Files (Legacy)**: Traditional file moving
  - **Prepopulate Selection**: Prepare for selective processing

**Step 2: Get Plex Timestamps (Optional but Recommended)**
- Click "Get Plex Timestamps"
- Extracts intro markers from Plex (requires Plex Pass)
- Provides backup when automatic detection fails

#### Phase 4: Commercial Processing

This is where the magic happens! See the [Commercial Breaking detailed guide](#commercial-breaking-process) below.

#### Phase 5: Channel Creation

**Step 1: Choose Lineup Version**
- Select Toonami version: Cut, Uncut, or Mixed
- Mixed blends different Toonami eras

**Step 2: Set Channel Number**
- Enter desired channel number (1-1000 recommended)
- Avoid duplicating existing channels

**Step 3: Commercial Break Length**
- Set flex duration (e.g., "2:30" for 2 minutes 30 seconds)

**Step 4: Final Preparation**
- "Prepare Cut Anime for Lineup": Processes metadata
- "Prepare Plex": Optimizes Plex library compatibility

**Step 5: Create Channel**
- **DizqueTV**: "Create Toonami Channel" 
- **Tunarr**: "Create Toonami Channel with Flex"

**Step 6: Add Flex (DizqueTV Only)**
- Adds commercial break spacing between segments

### Advanced TOM Features

#### Creating Additional Channels

**Continue from Last Episode**: 
- Checkbox option for sequential channels
- Starts new channel where previous one ended
- Requires running "Prepare Toonami Channel" twice on first use

#### Dark Mode
Toggle with the button in bottom-left corner for comfortable viewing.

---

## Absolution User Guide

**Command**: `python3 main.py --webui`
**Access**: `http://localhost:8081`

Absolution provides the same functionality as TOM but through a web interface, making it perfect for Docker deployments and remote access.

### Key Differences from TOM

#### Environment Variables Required
Instead of folder selection, Absolution uses environment variables set in `.env`:

```bash
ANIME_FOLDER=/path/to/your/anime
BUMPS_FOLDER=/path/to/your/bumps  
SPECIAL_BUMPS_FOLDER=/path/to/your/special_bumps
WORKING_FOLDER=/path/to/your/working
```

#### Docker-First Design
- Intended for containerized deployment
- Folders are mounted as Docker volumes
- Remote access capability for server installations

#### Web Interface Navigation
- Same workflow as TOM but web-based
- Mobile-friendly responsive design
- Supports multiple concurrent users

### Using Absolution

1. **Set up environment variables** in `.env` file
2. **Start the web server**: `python3 main.py --webui`
3. **Open browser** to `http://localhost:8081`
4. **Follow TOM workflow** - interface is nearly identical

For server deployments, replace `localhost` with your server's IP address.

---

## Clydes User Guide

**Command**: `python3 main.py --clydes`

Clydes provides a question-based command-line interface for users who prefer terminal interactions.

### Using Clydes

1. **Launch interface**: `python3 main.py --clydes`
2. **Answer prompts**: Clydes asks questions step-by-step
3. **Follow workflow**: Similar process to TOM but text-based
4. **Automation-friendly**: Can be scripted for repeated operations

### When to Use Clydes

- **Terminal preference**: You prefer command-line interfaces
- **Automation**: Scripting repeated channel creation
- **Remote access**: SSH sessions without GUI forwarding
- **Low resource**: Minimal system overhead

**Note**: While functional, TOM and Absolution provide more comprehensive experiences with better error handling and visual feedback.

---

## Commercial Breaking Process

Regardless of interface, the commercial breaking process follows these steps:

### Detection Phase

**1. Choose Input Method**:
- **Folder Mode**: Process entire directories
- **File Selection**: Choose specific episodes

**2. Detection Process**:
The system looks for commercial break points in this order:
- **Chapter markers** (fastest, most accurate)
- **Plex timestamps** (intro markers)  
- **Silence detection** (audio gaps)
- **Black frame detection** (visual transitions)

**3. Processing Modes**:

#### Traditional Mode
- **What it does**: Physically cuts video files at break points
- **Output**: Multiple files per episode (Part 1, Part 2, etc.)
- **Storage**: Requires additional disk space
- **Compatibility**: Works with all platforms

#### Cutless Mode ⭐ 
- **What it does**: Creates virtual break points without cutting files
- **Output**: Metadata describing break timestamps
- **Storage**: No additional space required
- **Compatibility**: Currently DizqueTV only
- **Benefits**: Preserves original files, faster processing

### Advanced Options

**Fast Mode**: Prioritizes chapter markers and Plex timestamps over detection

**Low Power Mode**: Uses only chapter markers and Plex timestamps

**Destructive Mode**: Deletes original files after cutting (use with caution)

**Cutless Mode**: Creates virtual cuts without modifying original files (DizqueTV only)

### Performance Tips

- **Use chapter markers**: 80,000x faster than detection
- **Filter shows first**: Only process what you'll use
- **Chapter source quality**: Some sources have better markers
- **Hardware matters**: Processing speed varies by system specs

---

## Quick Start Workflow

### For New Users (TOM Recommended)

1. **Install** following the [Installation Guide](Installation-Guide)
2. **Prepare files** using [naming conventions](File-Naming-Conventions)
3. **Launch TOM**: `python3 main.py --tom`
4. **Configure Plex** integration
5. **Select folders** for content
6. **Process content** and create channel
7. **Enjoy your Toonami marathon!**

### For Docker Users (Absolution)

1. **Set up `.env`** file with folder paths
2. **Run container** or `docker compose up -d`
3. **Access web interface** at `http://localhost:8081`
4. **Follow TOM workflow** in browser

### For Automation (Clydes)

1. **Launch CLI**: `python3 main.py --clydes`
2. **Answer prompts** for configuration
3. **Script responses** for repeated operations

---

## Next Steps

After completing your first channel:

- **[Configuration Reference](Configuration-Reference)**: Customize advanced settings
- **[File Naming Conventions](File-Naming-Conventions)**: Optimize your content organization  
- **[Troubleshooting](Troubleshooting)**: Solve common issues
- **[FAQ](FAQ)**: Find answers to frequently asked questions

Ready to dive deeper? Check out the [Architecture Overview](Architecture-Overview) to understand how everything works under the hood.
