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

#### Phase 1: Platform and Plex Setup

**Page 1: Choose Your Platform**

1. **Select your platform**
   - Choose between **DizqueTV**, **Tunarr**, or **ComBreakDirect**
   - **DizqueTV/Tunarr**: External channel platforms requiring a URL
   - **ComBreakDirect**: Self-hosted streaming server (no URL needed, auto-configured)

2. **Enter Platform URL** (unless using ComBreakDirect)
   - Enter your platform's URL (e.g., `http://192.168.1.100:3000` for DizqueTV or `http://192.168.1.100:8000` for Tunarr)
   - ComBreakDirect users skip this - it's auto-configured

3. **Navigation**
   - Click "Skip" (ComBreakDirect) or "Continue" (DizqueTV/Tunarr) at bottom right

**Page 2: Login to Plex** (Optional - Not shown for ComBreakDirect)

**Note**: ComBreakDirect users won't see this page - the UI navigates directly to folder selection.

1. **Login with Plex**
   - Click "Login with Plex" button
   - Browser window opens - log into your Plex account
   - Click "Allow" when prompted
   - Close the success window

2. **Select Plex Server**
   - Use the dropdown to select your Plex server
   - Even with one server, you may need to click the dropdown

3. **Select Anime Library**
   - Choose your existing anime collection (used for intro timestamps)

4. **Select Toonami Library**
   - Choose or create a new library for cut content and bumps

5. **Continue**
   - After selecting libraries, "Skip" button changes to "Continue"
   - Click "Continue" to proceed to folder selection

**Page 2 Alternate: Manual Entry**

**Note**: DizqueTV/Tunarr users can access this page by clicking "Skip" at the bottom right of the Plex login page.

- Enter Plex URL and Token manually
- Enter platform URL
- Type library names instead of selecting from dropdowns

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

**Note**: If you selected ComBreakDirect in Page 1, these processing mode options won't appear - the system automatically uses "Prepopulate Selection" mode.

**Step 2: Get Plex Timestamps (Optional but Recommended)**

**Note**: If you selected ComBreakDirect in Page 1, this option won't appear since ComBreakDirect doesn't use Plex timestamps.

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

#### Advanced Settings (Change Network)
- On Page 1, click “Advanced.”
- Enter a network name (e.g., “Toonami”, “Cartoon Network”, “Disney Channel”).
- Click “Validate” to check the network’s Wikipedia list page exists.
- Click “Apply & Restart” to save and automatically restart TOM.

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

#### Advanced Settings (Change Network)
- On Page 1, click the “Advanced” button at the bottom‑right.
- Enter a network and “Validate.”
- Click “Apply & Restart” to save and automatically restart the server.

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

#### Advanced Option (Change Network)
- On launch, Clydes offers an advanced prompt to change the active network.
- Enter a network (e.g., "Cartoon Network") and confirm. Clydes will persist the setting and ask you to re‑run.

#### Using Networkless Mode

**Networkless mode** bypasses Wikipedia validation entirely, allowing you to create custom channels with any content collection—perfect for fansubs, non-broadcast anime, or custom compilations.

**Setup Steps**:

1. **Set network to "Networkless"**:
   - Via Clydes advanced prompt: Enter `Networkless` when asked for network name
   - Via config.py: Set `network = "Networkless"`
   - Via TOM/Absolution: Use Advanced Settings to change network to `Networkless`

2. **Rename your bumps**:
   - All bump files must use the "Networkless" prefix
   - Example: `Networkless 2 0 ShowName back 4 red.mp4`
   - See [File Naming Conventions](File-Naming-Conventions.md) for complete naming patterns

3. **Process content normally**:
   - Run ToonamiChecker - it will skip Wikipedia and use ALL shows in your library
   - Continue with the normal workflow
   - All shows in your anime folder will be included without filtering

**Requirements**:
- Bump files MUST be named with "Networkless" prefix
- Bumps should be in folders containing "bump" or "special" in the path for proper filtering

**When to use Networkless mode**:
- Custom content that didn't air on broadcast networks
- Fansubs or unofficial releases
- Creating themed channels without network restrictions
- Testing with limited content collections

### When to Use Clydes

- **Terminal preference**: You prefer command-line interfaces
- **Automation**: Scripting repeated channel creation
- **Remote access**: SSH sessions without GUI forwarding
- **Low resource**: Minimal system overhead

**Note**: While functional, TOM and Absolution provide more comprehensive experiences with better error handling and visual feedback.

---

## S.A.R.A. Diagnostics (Page8)

**S.A.R.A. (System Analysis and Reporting Assistant)** provides comprehensive database validation and diagnostics inside the GUI experiences. Page8 is the diagnostics interface accessible from TOM and Absolution.

### Accessing S.A.R.A. Diagnostics

**Access Method:**

**Hidden Panic Button**: Click any page title **5 times in 2 seconds** → automatically navigates to diagnostics

**Why the Panic Button?**
- Quick access without memorizing menu structure
- Especially useful during critical errors that break normal navigation

### Page8 Features

#### Pipeline Status Display
Shows which pipeline steps have been completed:
- ✓ (Checkmark) - Step completed successfully
- ✗ (X) - Step failed or incomplete
- ○ (Circle) - Step not yet run

**Information Shown:**
- Current processing phase (0-6)
- Overall completion percentage
- Processing mode (Cutless vs Traditional)
- Platform selection (DizqueTV, Tunarr, or ComBreakDirect)
- Available Toonami versions

#### Validation Controls

**Run Full Validation**
- Executes comprehensive database validation
- Checks all 20 pipeline steps
- Validates data integrity and cross-table consistency
- Takes 5-30 seconds depending on database size
- Results appear in real-time as validation progresses

**Refresh Status**
- Quick status check without full validation
- Updates pipeline completion checklist
- Takes less than 1 second
- Use this for frequent progress checks

**Copy All Results**
- Copies validation results to clipboard
- Useful for bug reports and troubleshooting
- Includes all errors, warnings, and suggestions

#### Validation Results Display

Results are grouped by severity:

**CRITICAL (⊗):**
- Step cannot proceed
- Database table missing or corrupt
- Required configuration not set
- **Action Required**: Fix immediately before continuing

**ERROR (✗):**
- Significant data quality problems
- Missing timestamps or file paths
- Invalid BLOCK_ID formats
- **Action Required**: Address before channel creation

**WARNING (⚠):**
- Non-critical issues
- Duplicate episodes in lineup
- Unusual bump placement
- **Action Suggested**: Review but may be intentional

**INFO (ℹ):**
- Informational messages
- Platform and mode confirmations
- Version detection results
- **No Action Required**: Informational only

**Each Issue Includes:**
- **What**: User-friendly description of the problem
- **Where**: Which step and table has the issue
- **Why**: Technical details for understanding
- **How to Fix**: Actionable suggestion

### Using S.A.R.A. Diagnostics

#### When to Run Diagnostics

**After Initial Setup:**
- Verify platform configuration
- Check folder paths are correct
- Confirm Plex authentication (if required)

**After Content Preparation:**
- Validate bump preparation completed
- Check episode filtering worked correctly
- Verify lineup organization

**After Commercial Detection:**
- Ensure all episodes have timestamps
- Check for detection method used
- Validate break point quality

**Before Channel Creation:**
- Comprehensive validation of entire pipeline
- Catch issues before final export
- Verify cutless mode configuration (if applicable)

**When Troubleshooting:**
- Diagnose unexpected behavior
- Understand which step failed
- Get specific suggestions for fixes

#### Understanding Validation Results

**Example Validation Output:**

```
Pipeline Status: 85% complete (17/20 steps)
Current Phase: Phase 4 (Prepare Cut Anime)
Mode: Cutless | Platform: DizqueTV

✓ PlatformSelection - Completed successfully
✓ PlexAuth - Completed successfully
✓ FolderMaker - Completed successfully
✓ ToonamiChecker - Completed successfully
✓ LineupPrep - Completed successfully
...
✗ CommercialBreaker - Failed: 2 error(s)
○ CommercialInjector - Not run yet

[ERROR] CommercialBreaker → cuts
Message: 3 episodes missing commercial break timestamps
Details: Files: Naruto S01E05.mkv, Naruto S01E06.mkv, Bleach S02E03.mkv
Suggestion: Re-run CommercialBreaker in normal mode (not low power) to detect breaks
```

**Interpreting Results:**
- **85% complete** means most of pipeline has run successfully
- **✗ CommercialBreaker** indicates where the problem occurred
- **Specific file names** tell you exactly which episodes need attention
- **Suggestion** provides actionable next step

#### Common Validation Issues

**"Table does not exist" (CRITICAL)**
- **Meaning**: Pipeline step has not been run yet
- **Fix**: Run the step from the interface (e.g., "Prepare Toonami Channel")

**"Table has insufficient data" (ERROR)**
- **Meaning**: Step ran but didn't process any content
- **Fix**: Check input folders have files, verify file naming conventions

**"Episodes missing timestamps" (ERROR)**
- **Meaning**: Commercial detection didn't find break points
- **Fix**: Re-run CommercialBreaker in normal mode (not low power)

**"Cutless mode active but platform is Tunarr" (WARNING)**
- **Meaning**: Platform incompatibility detected
- **Fix**: Change platform to DizqueTV or disable cutless mode

**"Episode repeated in lineup" (INFO)**
- **Meaning**: Same episode appears multiple times
- **Usually Intentional**: Marathon format often repeats episodes

### Interface-Specific Details

#### TOM (Tkinter) Page8
- Native desktop interface
- Scrollable text widget for detailed results
- Buttons for validation controls
- Copy functionality uses system clipboard
- Panic button on all pages except Page5

#### Absolution (Web) Page8
- Web-based interface accessible via browser
- Collapsible sections for easier reading
- JavaScript-based clipboard copying
- Styled with Toonami theming
- Panic button on all page titles

> **Note:** The Clydes CLI does not expose a Page8-equivalent diagnostics view. Run validation from TOM or Absolution when you need the S.A.R.A. interface.

### Tips for Using S.A.R.A.

**Regular Checks:**
- Use "Refresh Status" frequently to monitor progress
- Run full validation after each major step
- Check diagnostics if any step seems stuck

**Before Asking for Help:**
- Run full validation and copy results
- Include validation output in bug reports
- Check suggestions before asking questions

**Understanding Your Pipeline:**
- Phase numbers help you understand "where am I?"
- Completion percentage shows overall progress
- Current step tells you what to do next

**Performance:**
- Full validation: 5-30 seconds depending on database size
- Quick status: <1 second, use for frequent checks
- No impact on other operations (runs in background)

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

1. **Install** following the [Installation Guide](Installation-Guide.md)
2. **Prepare files** using [naming conventions](File-Naming-Conventions.md)
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

- **[Configuration Reference](Configuration-Reference.md)**: Customize advanced settings
- **[File Naming Conventions](File-Naming-Conventions.md)**: Optimize your content organization  
- **[Troubleshooting](Troubleshooting.md)**: Solve common issues
- **[FAQ](FAQ.md)**: Find answers to frequently asked questions

Ready to dive deeper? Check out the [Architecture Overview](Architecture-Overview.md) to understand how everything works under the hood.
