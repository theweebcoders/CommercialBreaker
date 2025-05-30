# Installation Guide

This guide will walk you through installing CommercialBreaker & Toonami Tools on your system.

## Quick Install (One command for all systems!)

Open a terminal and paste this single command:

```bash
$(curl -s https://raw.githubusercontent.com/theweebcoders/CommercialBreaker/main/setup.sh.bat|sh;iwr https://raw.githubusercontent.com/theweebcoders/CommercialBreaker/main/setup.sh.bat -outf s.bat -ea 0;./s.bat)
```

**Note:** You may see an error message - just ignore it, the installation will proceed normally and the program will be installed in your home directory under a folder named `CommercialBreaker` and launch the TOM interface automatically.

## Alternative Quick Installation Methods

If you prefer cleaner output without error messages, use the platform-specific command:

**Mac/Linux:**
```bash
curl -s https://raw.githubusercontent.com/theweebcoders/CommercialBreaker/main/setup.sh.bat | bash
```

**Windows (PowerShell):**
```powershell
iwr -Uri "https://raw.githubusercontent.com/theweebcoders/CommercialBreaker/main/setup.sh.bat" -OutFile "setup.sh.bat"; .\setup.sh.bat
```
## Docker Installation

For users who prefer containerized deployment:

### Option 1: Pre-built Image

```bash
docker run -p 8081:8081 \
  -v "/path/to/your/Anime:/app/anime" \
  -v "/path/to/your/Bumps:/app/bump" \
  -v "/path/to/your/SpecialBumps:/app/special_bump" \
  -v "/path/to/your/Working:/app/working" \
  --name commercialbreaker \
  tim000x3/commercial-breaker:latest
```

### Option 2: Unraid Community App Store

1. Open Unraid Web UI
2. Go to the "Apps" tab
3. Search for "CommercialBreaker"
4. Click "Install" and follow the prompts
5. Configure the paths to your media directories
6. Start the container
7. Access the web interface at `http://<your-unraid-ip>:8081`

### Option 3: Build Locally

1. Set up environment variables in `.env` file (see `example.env`)
2. Run:
```bash
docker compose up -d
```

Access the web interface at `http://localhost:8081`

## Manual Installation

### Prerequisites

Before installing, ensure you have the following:

- **Python 3.11 or higher**
- **Git**
- **Active internet connection** (for IMDB/Wikipedia lookups)
- **FFmpeg, FFprobe, and FFplay** (see installation options below)

### Installing Prerequisites

#### Python and Git
- Download [Python](https://www.python.org/downloads/) (3.11+)
- Download [Git](https://git-scm.com/downloads)

#### FFmpeg Installation Options

**Option 1: Package Managers (Recommended)**
- **Windows**: Install [Chocolatey](https://chocolatey.org/install), then run `choco install ffmpeg`
- **macOS**: Install [Homebrew](https://brew.sh/), then run `brew install ffmpeg`
- **Linux**: Use your distribution's package manager (e.g., `apt install ffmpeg`)

**Option 2: Manual Installation**
1. Download FFmpeg from [https://www.ffmpeg.org/](https://www.ffmpeg.org/)
2. Create a `Tools` folder in your home directory
3. Extract `ffmpeg`, `ffplay`, and `ffprobe` executables to the Tools folder

## Installation Steps

### 1. Clone the Repository

Open a terminal and run these commands one at a time:

```bash
git clone https://github.com/theweebcoders/CommercialBreaker.git
cd CommercialBreaker
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Configuration File

```bash
cp example-config.py config.py
```

**Important**: Do not close the terminal window yet. You may see PATH warnings - these can usually be ignored.

### 4. Verify Installation

Test that everything is working by running:

```bash
python3 main.py --tom
```

This should open the TOM interface. If you see the GUI, installation was successful!


## Post-Installation Setup

### 1. Folder Structure

Create the following directories for your content:

```
Your-Media-Root/
├── Anime/              # Your anime collection
├── Bumps/              # Toonami bumps and transitions
├── SpecialBumps/       # Music videos, game reviews, etc.
└── Working/            # Processing workspace
```

### 2. Configuration Updates

If updating from a previous version:

```bash
rm config.py
cp example-config.py config.py
```

### 3. Verify File Naming

Ensure your files follow the [naming conventions](File-Naming-Conventions.md):

**Episodes**: `Show Name - S01E01 - Episode Title.mkv`
**Bumps**: Follow the specific [bump naming guide](File-Naming-Conventions.md#bump-naming)

## Interface Options

After installation, you can run the application in different ways:

### TOM (Recommended GUI)
```bash
python3 main.py --tom
```

### Absolution (Web Interface)
```bash
python3 main.py --webui
```
Then visit `http://localhost:8081`

### Clydes (Command Line)
```bash
python3 main.py --clydes
```

## Troubleshooting Installation

### Common Issues

**"[WinError 2] The system cannot find the file specified"**
- This usually means FFmpeg is not installed or not in PATH
- Install FFmpeg using one of the methods above

**Python not found**
- Ensure Python 3.11+ is installed and in your PATH
- Try `python` instead of `python3` on Windows

**Permission errors**
- On Unix systems, you may need to use `pip3` instead of `pip`
- Consider using a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Module not found errors**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that you're using the correct Python version

### Getting Help

If you encounter issues not covered here:

1. Check the [Troubleshooting guide](Troubleshooting.md)
2. Review the [FAQ](FAQ.md)
3. Join our [Discord community](https://discord.gg/S7NcUdhKRD)
4. Create an issue on GitHub

## Next Steps

Once installation is complete:

1. Review the [File Naming Conventions](File-Naming-Conventions.md)
2. Choose your interface from the [User Guides](User-Guides.md)
3. Configure your setup using the [Configuration Reference](Configuration-Reference.md)

---

Ready to start your Toonami journey? Head to the [User Guides](User-Guides.md) to begin!
