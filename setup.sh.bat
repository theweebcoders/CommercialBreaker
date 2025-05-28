:; # Check if CommercialBreaker is already installed
:; if [ -d "$HOME/.commercialbreaker/CommercialBreaker" ] && [ -f "$HOME/.commercialbreaker/bin/commercialbreaker" ]; then
:;     echo "🎬 CommercialBreaker is already installed!"
:;     echo "🚀 Launching CommercialBreaker..."
:;     exec "$HOME/.commercialbreaker/bin/commercialbreaker"
:; fi
:;
:; echo '🎬 CommercialBreaker Universal Installer'
:; echo '================================================'
:; echo 'Setting up self-contained environment...'
:; 
:; # Set up installation directory
:; CB_HOME="$HOME/.commercialbreaker"
:; mkdir -p "$CB_HOME"
:; cd "$CB_HOME"
:; 
:; # Check if we already have conda/mamba
:; if [ -d "$CB_HOME/conda" ]; then
:;     echo "✓ Conda environment found"
:;     CONDA="$CB_HOME/conda/bin/conda"
:;     MAMBA="$CB_HOME/conda/bin/mamba"
:; else
:;     echo "📦 Installing Miniforge (lightweight conda)..."
:;     
:;     # Detect system
:;     SYSTEM=$(uname -s)
:;     ARCH=$(uname -m)
:;     
:;     if [ "$SYSTEM" = "Darwin" ]; then
:;         if [ "$ARCH" = "arm64" ]; then
:;             MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh"
:;         else
:;             MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh"
:;         fi
:;     else
:;         MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
:;     fi
:;     
:;     # Download and install Miniforge
:;     curl -L -o miniforge.sh "$MINIFORGE_URL" || wget -O miniforge.sh "$MINIFORGE_URL" || exit 1
:;     bash miniforge.sh -b -p "$CB_HOME/conda" || exit 1
:;     rm miniforge.sh
:;     
:;     CONDA="$CB_HOME/conda/bin/conda"
:;     MAMBA="$CB_HOME/conda/bin/mamba"
:; fi
:; 
:; # Create/update environment
:; echo "🐍 Setting up Python environment..."
:; $MAMBA create -n commercialbreaker python=3.11 ffmpeg git -y || $CONDA create -n commercialbreaker python=3.11 ffmpeg git -y || exit 1
:; 
:; # Activate environment
:; eval "$($CONDA shell.bash hook)"
:; conda activate commercialbreaker
:; 
:; # Clone/update repository
:; if [ -d "CommercialBreaker" ]; then
:;     echo "📦 Updating CommercialBreaker..."
:;     cd CommercialBreaker && git pull
:; else
:;     echo "📦 Downloading CommercialBreaker..."
:;     git clone https://github.com/theweebcoders/CommercialBreaker.git || exit 1
:;     cd CommercialBreaker
:; fi
:; 
:; # Install dependencies
:; echo "📦 Installing dependencies..."
:; pip install -r requirements/pre_deps.txt || exit 1
:; pip install -r requirements.txt || exit 1
:; 
:; # Copy example-config.py to config.py if needed
:; if [ -f "example-config.py" ] && [ ! -f "config.py" ]; then
:;     echo "📋 Creating config.py from example..."
:;     cp example-config.py config.py
:; fi
:; 
:; # Create bin directory first!
:; mkdir -p "$CB_HOME/bin"
:; 
:; # Create launcher script using echo instead of heredoc
:; echo "🚀 Creating launcher..."
:; echo '#!/bin/bash' > "$CB_HOME/bin/commercialbreaker"
:; echo 'source "$HOME/.commercialbreaker/conda/etc/profile.d/conda.sh"' >> "$CB_HOME/bin/commercialbreaker"
:; echo 'conda activate commercialbreaker' >> "$CB_HOME/bin/commercialbreaker"
:; echo 'cd "$HOME/.commercialbreaker/CommercialBreaker"' >> "$CB_HOME/bin/commercialbreaker"
:; echo 'python main.py "$@"' >> "$CB_HOME/bin/commercialbreaker"
:; chmod +x "$CB_HOME/bin/commercialbreaker"
:; 
:; # Add to PATH for this session
:; export PATH="$CB_HOME/bin:$PATH"
:; 
:; echo "✅ Installation complete!"
:; echo "🚀 Launching CommercialBreaker..."
:; exec "$CB_HOME/bin/commercialbreaker"
:; exit 0

@echo off
:: Windows batch script starts here

:: Check if already installed
if exist "%USERPROFILE%\.commercialbreaker\bin\commercialbreaker.bat" (
    echo 🎬 CommercialBreaker is already installed!
    echo 🚀 Launching CommercialBreaker...
    call "%USERPROFILE%\.commercialbreaker\bin\commercialbreaker.bat"
    exit /b 0
)

echo 🎬 CommercialBreaker Universal Installer
echo ================================================
echo Setting up self-contained environment...

:: Set up installation directory
set "CB_HOME=%USERPROFILE%\.commercialbreaker"
if not exist "%CB_HOME%" mkdir "%CB_HOME%"
cd /d "%CB_HOME%"

:: Check for existing conda
if exist "%CB_HOME%\conda" (
    echo ✓ Conda environment found
    set "CONDA=%CB_HOME%\conda\Scripts\conda.exe"
    set "MAMBA=%CB_HOME%\conda\Scripts\mamba.exe"
) else (
    echo 📦 Installing Miniforge (lightweight conda^)...
    
    :: Download Miniforge
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe' -OutFile 'miniforge.exe'" || goto :error
    
    :: Install silently
    start /wait miniforge.exe /S /D=%CB_HOME%\conda || goto :error
    del miniforge.exe
    
    set "CONDA=%CB_HOME%\conda\Scripts\conda.exe"
    set "MAMBA=%CB_HOME%\conda\Scripts\mamba.exe"
)

:: Create/update environment
echo 🐍 Setting up Python environment...
call "%CONDA%" create -n commercialbreaker python=3.11 ffmpeg git -y || goto :error

:: Activate environment
call "%CB_HOME%\conda\Scripts\activate.bat" commercialbreaker

:: Clone/update repository
if exist "CommercialBreaker" (
    echo 📦 Updating CommercialBreaker...
    cd CommercialBreaker
    git pull
) else (
    echo 📦 Downloading CommercialBreaker...
    git clone https://github.com/theweebcoders/CommercialBreaker.git || goto :error
    cd CommercialBreaker
)

:: Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements\pre_deps.txt || goto :error
pip install -r requirements.txt || goto :error

:: Install Windows-specific dependencies
echo 📦 Installing Windows-specific dependencies...
pip install windows-curses || goto :error

:: Copy example-config.py to config.py if needed
if exist "example-config.py" if not exist "config.py" (
    echo 📋 Creating config.py from example...
    copy example-config.py config.py
)

:: Create launcher script
echo 🚀 Creating launcher...
if not exist "%CB_HOME%\bin" mkdir "%CB_HOME%\bin"

(
echo @echo off
echo call "%%USERPROFILE%%\.commercialbreaker\conda\Scripts\activate.bat" commercialbreaker
echo cd /d "%%USERPROFILE%%\.commercialbreaker\CommercialBreaker"
echo python main.py %%*
) > "%CB_HOME%\bin\commercialbreaker.bat"

echo ✅ Installation complete!
echo 🚀 Launching CommercialBreaker...
call "%CB_HOME%\bin\commercialbreaker.bat"
exit /b 0

:error
echo ❌ Installation failed!
pause
exit /b 1
