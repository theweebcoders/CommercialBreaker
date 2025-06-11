"""
macOS build script for CommercialBreaker
Creates a proper .app bundle with icon
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import time

def main():
    print("CommercialBreaker macOS App Builder")
    print("=" * 50)
    
    # Create a build folder
    build_folder = Path("CommercialBreaker-Build")
    
    if build_folder.exists():
        print(f"\nFolder '{build_folder}' already exists.")
        response = input("Delete it and start fresh? (y/n): ")
        if response.lower() == 'y':
            print("Removing old build folder...")
            shutil.rmtree(build_folder)
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
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "Pillow"], check=True)
        
        # Convert the PNG icon to ICNS format for macOS
        print("\n3. Converting icon to macOS ICNS format...")
        icon_conversion_script = '''
from PIL import Image
import os
import subprocess
import tempfile

# Read the PNG disguised as ICO
with open("icon.ico", "rb") as f:
    png_data = f.read()

# Create temp directory for icon conversion
with tempfile.TemporaryDirectory() as tmpdir:
    # Write as actual PNG
    png_path = os.path.join(tmpdir, "icon.png")
    with open(png_path, "wb") as f:
        f.write(png_data)
    
    # Open and convert to RGBA
    img = Image.open(png_path)
    print(f"  Original size: {img.size}")
    
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Create iconset directory
    iconset_path = os.path.join(tmpdir, "icon.iconset")
    os.makedirs(iconset_path)
    
    # macOS icon sizes (need @2x versions for Retina)
    sizes = [
        (16, "16x16"),
        (32, "16x16@2x"),
        (32, "32x32"),
        (64, "32x32@2x"),
        (128, "128x128"),
        (256, "128x128@2x"),
        (256, "256x256"),
        (512, "256x256@2x"),
        (512, "512x512"),
        (1024, "512x512@2x")
    ]
    
    for size, name in sizes:
        icon_size = (size, size)
        resized = img.resize(icon_size, Image.Resampling.LANCZOS)
        icon_file = os.path.join(iconset_path, f"icon_{name}.png")
        resized.save(icon_file, "PNG")
        print(f"  Created {name} icon")
    
    # Use iconutil to create ICNS
    print("  Converting to ICNS format...")
    subprocess.run(["iconutil", "-c", "icns", iconset_path, "-o", "icon.icns"], check=True)
    
    print("  [OK] Created icon.icns")
'''
        
        with open("convert_icon.py", "w", encoding="utf-8") as f:
            f.write(icon_conversion_script)
        
        subprocess.run([sys.executable, "convert_icon.py"], check=True)
        os.remove("convert_icon.py")
        
        # Copy example-config.py to config.py
        print("\n4. Setting up configuration...")
        shutil.copy("example-config.py", "config.py")
        
        # Fix config.py for bundled app
        print("   Patching config.py for app bundle...")
        
        with open("config.py", "r", encoding="utf-8") as f:
            config_content = f.read()
        
        # Add resource path handling
        icon_patch = '''# Resource path handling for PyInstaller
import sys
import os

if getattr(sys, 'frozen', False):
    # Running as compiled app
    application_path = sys._MEIPASS
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))

'''
        
        # Update icon path
        import re
        if "icon_path" in config_content:
            config_content = re.sub(
                r'(icon_path\s*=\s*["\'].*?["\'])',
                'icon_path = os.path.join(application_path, "icon.icns")',
                config_content
            )
            config_content = icon_patch + "\n" + config_content
        else:
            config_content = icon_patch + 'icon_path = os.path.join(application_path, "icon.icns")\n\n' + config_content
        
        with open("config.py", "w", encoding="utf-8") as f:
            f.write(config_content)
        
        # Install remaining dependencies
        print("\n5. Installing remaining dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "setuptools<81", "wheel", "build"], check=True)
        
        if Path("requirements/pre_deps.txt").exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements/pre_deps.txt"], check=True)
        
        subprocess.run([sys.executable, "-m", "pip", "install", "m3u8"], check=True)
        
        # Create minimal setup.py
        with open("setup.py", "w") as f:
            f.write("from setuptools import setup, find_packages\nsetup(name='commercialbreaker', version='0.1.0', packages=find_packages())")
        
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-build-isolation", "."], check=True)
        
        for req in ["runtime.txt", "graphics.txt"]:
            if Path(f"requirements/{req}").exists():
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", f"requirements/{req}"], check=True)
        
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        
        # Build with PyInstaller
        print("\n6. Building macOS app bundle...")
        
        # Create spec file for better control
        spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.icns', '.'),
        ('config.py', '.'),
        ('CLI', 'CLI'),
        ('requirements', 'requirements'),
    ],
    hiddenimports=['tkinter', 'cv2', 'numpy', 'scipy', 'skimage', 'pytesseract', 
                   'ffmpeg', 'm3u8', 'PIL', '_tkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CommercialBreaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns',
)

app = BUNDLE(
    exe,
    name='CommercialBreaker.app',
    icon='icon.icns',
    bundle_identifier='com.theweebcoders.commercialbreaker',
    info_plist={
        'CFBundleName': 'CommercialBreaker',
        'CFBundleDisplayName': 'CommercialBreaker',
        'CFBundleGetInfoString': "CommercialBreaker",
        'CFBundleIdentifier': 'com.theweebcoders.commercialbreaker',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
    },
)
'''
        
        with open("CommercialBreaker.spec", "w") as f:
            f.write(spec_content)
        
        # Build using the spec file
        subprocess.run([sys.executable, "-m", "PyInstaller", "CommercialBreaker.spec", "--clean", "--noconfirm"], check=True)
        
        # The app will be in dist/CommercialBreaker.app
        app_path = Path("dist/CommercialBreaker.app")
        if app_path.exists():
            output_path = original_dir / "CommercialBreaker.app"
            if output_path.exists():
                shutil.rmtree(output_path)
            shutil.copytree(app_path, output_path)
            
            print("\n" + "=" * 50)
            print("[SUCCESS!]")
            print(f"\nYour app is ready: {output_path}")
            
            # Get app size
            total_size = sum(f.stat().st_size for f in output_path.rglob('*') if f.is_file())
            print(f"Size: {total_size / 1024 / 1024:.1f} MB")
            
            print("\n[OK] Native macOS app bundle")
            print("[OK] Proper macOS icon at all sizes")
            print("[OK] No console window")
            print("\nTo run: Double-click CommercialBreaker.app")
            print("\nNote: First run may require:")
            print("  - Right-click → Open (to bypass Gatekeeper)")
            print("  - System Preferences → Security & Privacy → Allow")
        else:
            print("\n[FAILED] App bundle not found!")
            
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        import traceback
        traceback.print_exc()
            
    finally:
        os.chdir(original_dir)
        
    print(f"\nBuild folder left at: {build_folder}")

if __name__ == "__main__":
    main()