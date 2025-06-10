"""
Windows build script for CommercialBreaker
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import time

def main():
    print("CommercialBreaker Windows EXE Builder")
    print("=" * 50)
    
    # Create a build folder
    build_folder = Path("CommercialBreaker-Build")
    
    if build_folder.exists():
        print(f"\nFolder '{build_folder}' already exists.")
        response = input("Delete it and start fresh? (y/n): ")
        if response.lower() == 'y':
            print("Removing old build folder...")
            os.system(f'rmdir /s /q "{build_folder}"')
            time.sleep(1)
        else:
            print("Please remove or rename the existing folder first.")
            return
    
    print("\n1. Cloning CommercialBreaker...")
    subprocess.run([
        "git", "clone", 
        "https://github.com/theweebcoders/CommercialBreaker.git", 
        str(build_folder)
    ], check=True)
    
    original_dir = Path.cwd()
    os.chdir(build_folder)
    
    try:
        print("\n2. Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "windows-curses", "Pillow"], check=True)
        
        # Convert the PNG icon to proper ICO format
        print("\n3. Converting icon to proper Windows ICO format...")
        icon_conversion_script = '''
from PIL import Image
import os
import shutil

# Read the PNG disguised as ICO
with open("icon.ico", "rb") as f:
    png_data = f.read()

# Write it as actual PNG temporarily
with open("temp_icon.png", "wb") as f:
    f.write(png_data)

# Open the PNG
img = Image.open("temp_icon.png")
print(f"  Original size: {img.size}")

# Convert to RGBA if needed
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# Create multiple sizes for Windows
# Windows wants these specific sizes for best display
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icons = []

for size in sizes:
    if size[0] <= img.size[0]:
        # Use high quality resampling
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icons.append(resized)
        print(f"  Created {size[0]}x{size[1]} icon")

# Save as a proper ICO file with all sizes
if icons:
    icons[0].save("icon_proper.ico", format='ICO', sizes=sizes, append_images=icons[1:])
    print("  [OK] Created proper multi-resolution ICO file")
    
    # Close the image to release file handles
    img.close()
    
    # Replace the original
    if os.path.exists("icon.ico"):
        os.remove("icon.ico")
    shutil.move("icon_proper.ico", "icon.ico")
    
    # Clean up temp file
    try:
        if os.path.exists("temp_icon.png"):
            os.remove("temp_icon.png")
    except:
        pass  # If we can't delete it, just continue
        
    print("  [OK] Replaced icon.ico with proper ICO file")
'''
        
        with open("convert_icon.py", "w", encoding="utf-8") as f:
            f.write(icon_conversion_script)
        
        subprocess.run([sys.executable, "convert_icon.py"], check=True)
        os.remove("convert_icon.py")
        
        # Copy example-config.py to config.py first
        print("\n4. Setting up configuration...")
        shutil.copy("example-config.py", "config.py")
        
        # Fix config.py to handle icon path properly
        print("   Patching config.py for icon handling...")
        
        # Read existing config.py
        with open("config.py", "r", encoding="utf-8") as f:
            config_content = f.read()
        
        # Add icon path handling at the top of the file
        icon_patch = '''# Icon path handling for PyInstaller
import sys
import os

if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = sys._MEIPASS
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Update icon path
'''
        
        # Check if icon_path is defined and update it
        if "icon_path" in config_content:
            import re
            # Find where icon_path is defined and update it
            config_content = re.sub(
                r'(icon_path\s*=\s*["\'].*?["\'])',
                'icon_path = os.path.join(application_path, "icon.ico")',
                config_content
            )
            # Add the patch at the beginning
            config_content = icon_patch + "\n" + config_content
        else:
            # Add both the patch and icon_path definition
            config_content = icon_patch + 'icon_path = os.path.join(application_path, "icon.ico")\n\n' + config_content
        
        # Write patched config
        with open("config.py", "w", encoding="utf-8") as f:
            f.write(config_content)
        
        # Continue with dependencies
        print("\n5. Installing remaining dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "setuptools<81", "wheel", "build"], check=True)
        
        if Path("requirements/pre_deps.txt").exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements/pre_deps.txt"], check=True)
        
        subprocess.run([sys.executable, "-m", "pip", "install", "m3u8"], check=True)
        
        with open("setup.py", "w") as f:
            f.write("from setuptools import setup, find_packages\nsetup(name='commercialbreaker', version='0.1.0', packages=find_packages())")
        
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-build-isolation", "."], check=True)
        
        for req in ["runtime.txt", "graphics.txt"]:
            if Path(f"requirements/{req}").exists():
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", f"requirements/{req}"], check=True)
        
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "windows-curses"], check=True)
        
        # Build with PyInstaller
        print("\n6. Building EXE with proper icon...")
        
        # Get absolute path to icon
        icon_path = Path("icon.ico").absolute()
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",  # No console
            "--name", "CommercialBreaker",
            "--icon", str(icon_path),
            # Include the icon file in the bundle
            "--add-data", f"{icon_path};.",
            "--add-data", "config.py;.",
            "--add-data", "CLI;CLI",
            "--add-data", "requirements;requirements",
        ]
        
        # Add imports
        for imp in ["tkinter", "cv2", "numpy", "scipy", "skimage", "pytesseract", 
                    "ffmpeg", "m3u8", "PIL", "curses", "_curses", "windows_curses", "_curses_panel"]:
            cmd.extend(["--hidden-import", imp])
        
        cmd.extend([
            "--exclude-module", "matplotlib",
            "--clean",
            "--noconfirm",
            "main.py"
        ])
        
        subprocess.run(cmd, check=True)
        
        # Copy to Downloads
        exe_path = Path("dist/CommercialBreaker.exe")
        if exe_path.exists():
            output_path = original_dir / "CommercialBreaker.exe"
            shutil.copy2(exe_path, output_path)
            print("\n" + "=" * 50)
            print("[SUCCESS!]")
            print(f"\nYour EXE is ready: {output_path}")
            print(f"Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
            print("\n[OK] No console window")
            print("[OK] Proper Windows icon (16x16 to 256x256)")
            print("[OK] Icon will show in EXE, taskbar, and window")
        else:
            print("\n[FAILED] EXE not found!")
            
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        import traceback
        traceback.print_exc()
            
    finally:
        os.chdir(original_dir)
        
    print("\nBuild folder left at: CommercialBreaker-Build")

if __name__ == "__main__":
    main()