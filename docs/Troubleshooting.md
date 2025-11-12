# Troubleshooting Guide

This guide helps you resolve common issues with CommercialBreaker & Toonami Tools.

## Installation Issues

### FFmpeg Not Found
**Error**: `[WinError 2] The system cannot find the file specified`

**Solution**:
1. **Install FFmpeg**: Download from [https://www.ffmpeg.org/](https://www.ffmpeg.org/)
2. **Place in Tools folder**: Copy `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe` to `Tools/` directory
3. **Or install via package manager**:
   - **Windows**: `choco install ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`

### Python Version Issues
**Error**: Various import or syntax errors

**Solution**:
- Ensure Python 3.11+ is installed
- Check version: `python3 --version`
- Use correct Python command for your system

### Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'xyz'`

**Solution**:
```bash
pip install -r requirements.txt
```

### DizqueTV Package Installation Failure
**Error**: `ModuleNotFoundError: No module named 'm3u8'` or `error: subprocess-exited-with-error` during `pip install`

**Problem**: The dizquetv package (required for Cutless Mode) has a build-time import issue. Its `setup.py` imports code from the package itself (`from dizqueTV._info import __version__`), which triggers imports of the entire dizqueTV module. This module imports dependencies like `m3u8`, `PlexAPI`, and `objectrest` at the top level - but these dependencies aren't installed yet because pip is still trying to build the dizquetv package!

**Solution**: Install dependencies in the correct order:

```bash
# Step 1: Install build tools
pip install --no-cache-dir wheel setuptools

# Step 2: Install pre-dependencies (m3u8, PlexAPI, numpy, objectrest)
pip install -r requirements/pre_deps.txt

# Step 3: Install dizquetv without build isolation
pip install --no-build-isolation git+https://github.com/theweebcoders/dizquetv-python.git

# Step 4: Install remaining requirements
pip install -r requirements.txt
```

**Why `--no-build-isolation` works**: This flag allows the dizquetv setup.py to access already-installed packages (like m3u8) during the build process instead of creating an isolated environment.

**Note**:
- This issue only affects **manual desktop installations**
- The automated setup script (`setup.sh.bat`) handles this automatically
- Docker installations use a corrected installation order in the Dockerfile
- Most users won't encounter this since they use Docker or the setup script

**Alternative**: If the above doesn't work, try installing dizquetv separately first:
```bash
pip install -r requirements/pre_deps.txt
pip install --no-build-isolation git+https://github.com/theweebcoders/dizquetv-python.git
pip install -r requirements.txt
```

---

## Using S.A.R.A. Diagnostics

**S.A.R.A. (System Analysis and Reporting Assistant)** is your first stop for troubleshooting. Before diving into specific issues, use S.A.R.A. to get a comprehensive analysis of your pipeline state.

### When to Use S.A.R.A.

**Use S.A.R.A. diagnostics when:**
- Something isn't working and you don't know why
- A step seems to have failed
- Channel creation produces unexpected results
- Processing appears stuck or incomplete
- You need to understand what went wrong

### Accessing S.A.R.A.

**Panic Button**: Click any page title **5 times in 2 seconds**

### Quick Diagnostic Workflow

**Step 1: Open S.A.R.A. Diagnostics** (Page8)

**Step 2: Check Pipeline Status**
- Look at the completion checklist
- Find the last successful step (✓)
- Find the failing step (✗)
- Note which step hasn't run yet (○)

**Step 3: Run Full Validation**
- Click "Run Full Validation" button
- Wait for results (5-30 seconds)
- Read through issues from top to bottom

**Step 4: Follow Suggestions**
- Start with CRITICAL issues (⊗)
- Then address ERRORs (✗)
- Review WARNINGs (⚠) as needed
- Each issue includes specific fix suggestions

**Step 5: Copy Results for Help**
- Click "Copy All Results" button
- Include in bug reports or support requests

### Interpreting Validation Results

#### CRITICAL Issues (⊗)

**"Table 'xyz' does not exist"**
- **Meaning**: Step hasn't been run yet
- **Fix**: Run the step from the interface

**"Platform type not set in app_data"**
- **Meaning**: Platform selection incomplete
- **Fix**: Select platform on Page1 (DizqueTV, Tunarr, or ComBreakDirect)

#### ERROR Issues (✗)

**"X episodes missing commercial break timestamps"**
- **Meaning**: Commercial detection didn't find break points
- **Fix**: Re-run CommercialBreaker in normal mode (not low power)
- **Note**: Some episodes may not have detectable breaks

**"Table 'xyz' has insufficient data"**
- **Meaning**: Step ran but didn't process any content
- **Fix**: Check input folders have files, verify file naming

**"Missing required columns"**
- **Meaning**: Database schema is outdated or corrupt
- **Fix**: Re-run the step to rebuild table

**"BLOCK_ID not found in lineup_prep_out"**
- **Meaning**: Lineup references a bump that doesn't exist
- **Fix**: Re-run "Prepare Toonami Channel" to rebuild lineup

#### WARNING Issues (⚠)

**"Episode repeated in lineup"**
- **Meaning**: Same episode appears multiple times
- **Usually OK**: Marathon format often repeats episodes
- **Fix**: Only address if unintentional

**"Cutless mode active but platform is Tunarr"**
- **Meaning**: Platform incompatibility
- **Fix**: Change to DizqueTV or disable cutless mode

**"Multibump not followed by anime"**
- **Meaning**: Lineup placement rule violation
- **Fix**: Re-run Merger to rebuild lineup

#### INFO Messages (ℹ)

These are informational only - no action required:
- "3 versions detected" - Normal if using multiple Toonami versions
- "Cutless mode active" - Confirmation of your mode selection
- Platform and configuration confirmations

### Common Validation Scenarios

#### Scenario: "Everything shows as incomplete"

**Symptoms:**
```
○ PlatformSelection - Not run yet
○ PlexAuth - Not run yet
○ FolderMaker - Not run yet
...
```

**Diagnosis**: Pipeline hasn't been started yet

**Fix**:
1. Go to Page1
2. Select your platform
3. Authenticate with Plex (if required)
4. Set up folder paths
5. Run "Prepare Toonami Channel"

#### Scenario: "Stopped at CommercialBreaker"

**Symptoms:**
```
✓ ToonamiChecker - Completed successfully
✓ LineupPrep - Completed successfully
...
✗ CommercialBreaker - Failed: 15 episodes missing timestamps
○ CommercialInjector - Not run yet
```

**Diagnosis**: Commercial detection didn't find breaks in some episodes

**Fix**:
1. Check which episodes are missing timestamps (listed in details)
2. Verify episodes are actual anime (not bumps)
3. Try different detection modes:
   - **Normal mode**: Most thorough
   - **Fast mode**: Skips silent black frame detection
   - **Low power mode**: Only checks chapters/Plex
4. For episodes without detectable breaks:
   - May have different commercial break patterns
   - May need manual timestamp entry
   - Can skip these episodes if necessary

#### Scenario: "Platform compatibility warning"

**Symptoms:**
```
⚠ WARNING: Cutless mode active but platform is Tunarr (unsupported)
```

**Diagnosis**: Tunarr doesn't support cutless mode

**Fix**:
- **Option 1**: Change platform to DizqueTV (requires custom fork) or ComBreakDirect
- **Option 2**: Disable cutless mode and use traditional cutting
- **Note**: Can't use cutless with Tunarr

#### Scenario: "Stale data warning"

**Symptoms:**
```
⚠ WARNING: Stale cutless tables detected: lineup_v2_cutless, lineup_v3_cutless
```

**Diagnosis**: Database contains tables from previous run with different mode

**Fix**:
- These old tables can be safely ignored
- Or delete them if you want to clean up:
  ```sql
  DROP TABLE IF EXISTS lineup_v2_cutless;
  DROP TABLE IF EXISTS lineup_v3_cutless;
  ```

### Using S.A.R.A. with Other Troubleshooting

After running S.A.R.A. diagnostics:
1. **If S.A.R.A. identifies the problem**: Follow its suggestions
2. **If issues persist**: Refer to specific sections below
3. **If S.A.R.A. shows no issues**: Problem may be outside database (files, network, etc.)

S.A.R.A. validates the database state - it doesn't check:
- Physical file existence (though some validators do sample checks)
- Network connectivity
- FFmpeg installation
- Disk space
- File permissions

For these issues, see specific troubleshooting sections below.

### S.A.R.A. Performance Tips

**For large databases (many shows/episodes):**
- Use "Refresh Status" for quick checks during processing
- Run "Full Validation" only when needed (after major steps)
- Full validation may take 15-30 seconds with large databases

**During active processing:**
- S.A.R.A. runs in background thread
- Won't interfere with other operations
- Results appear in real-time as validation progresses

---

## Configuration Issues

### Plex Authentication Failed
**Problem**: Can't connect to Plex server

**Solutions**:
1. **Check Plex credentials**: Verify server URL and token
2. **Network connectivity**: Ensure Plex server is accessible
3. **Manual token entry**: Use Plex token directly if OAuth fails
4. **Firewall/VPN**: Check if network restrictions block access

**Smart Connection Retry**: CommercialBreaker automatically tries all available connection URLs for your Plex server:
- Local network URLs (fastest)
- Direct connections
- Relay URLs (fallback)

If connection fails after trying all URLs, check the application logs to see which URLs were attempted.

### Plex Connection Timeouts
**Problem**: Connection to Plex server times out or is unreliable

**Automatic Handling**:
CommercialBreaker includes smart connection retry logic that handles most timeout issues automatically:
- Tries local network URLs first (192.168.x.x, 10.x.x.x)
- Falls back to direct public IPs
- Uses Plex relay URLs as last resort
- Logs all connection attempts for debugging

**Manual Solutions** (if automatic retry doesn't resolve):
1. **Check network stability**: Ensure consistent connection to your network
2. **Plex server status**: Verify Plex server is running and responsive
3. **Router/firewall**: Ensure ports are properly forwarded for direct connections
4. **Relay URL issues**: If only relay works, consider port forwarding for better performance
5. **Review logs**: Check console output to see which connection URLs were tried

**Understanding Connection Priority**:
- **Local URLs** (best): Direct connection on same network, fastest response
- **Direct URLs** (good): Public IP with port forwarding, reliable
- **Relay URLs** (fallback): Routed through Plex servers, can timeout under load

### Library Not Found
**Problem**: Selected library doesn't appear or is empty

**Solutions**:
1. **Refresh Plex libraries**: Scan for new content
2. **Check file naming**: Ensure files follow [naming conventions](File-Naming-Conventions.md)
3. **Verify permissions**: Ensure Plex can access file locations
4. **Library type**: Confirm you're selecting the correct library type (TV Shows)

---

## File Processing Issues

### No Commercial Breaks Detected
**Problem**: Detection phase finds no timestamps

**Causes & Solutions**:

**No Chapter Markers**:
- Use sources with embedded chapter markers for best results
- Consider "Low Power Mode" if no chapters available

**Silent/Black Frame Detection Fails**:
- Check audio levels aren't too low/high
- Adjust detection thresholds in config:
  ```python
  SILENCE_THRESHOLD = -50.0  # Try -40.0 or -60.0
  BLACK_FRAME_THRESHOLD = 0.1  # Try 0.05 or 0.2
  ```

**No Plex Timestamps**:
- Ensure Plex Pass subscription active
- Enable "Skip Intro" feature in Plex
- Run "Get Plex Timestamps" step

### Processing Takes Too Long
**Problem**: Commercial detection runs for hours/days

**Solutions by Priority**:

1. **Use Chapter Markers**: 80,000x faster than frame analysis
2. **Filter Shows First**: Use ToonamiTools to process only needed shows
3. **Enable Fast Mode**: Reduces detection methods used
4. **Use Low Power Mode**: Chapter markers and Plex timestamps only
5. **Process in Batches**: Select specific shows/episodes instead of entire library

### Cutting Failures
**Problem**: Some episodes fail to cut properly

**Common Issues**:

**Corrupted Files**:
- Check source file integrity
- Re-download or re-encode problematic files

**Insufficient Disk Space**:
- Ensure adequate free space (2-3x source file size)
- Clean up temporary files in working directory

**Timestamp Accuracy**:
- Use [Manual Timestamp Editor](Component-Documentation.md#manual-timestamp-editor)
- Fine-tune break points manually

---

## Platform Integration Issues

### DizqueTV Connection Failed
**Problem**: Can't create channel in DizqueTV

**Solutions**:
1. **Verify URL**: Check DizqueTV server address and port
2. **API Access**: Ensure DizqueTV API is accessible
3. **Version Compatibility**: Use our [DizqueTV fork](https://github.com/theweebcoders/dizquetv) for Cutless Mode
4. **Network Issues**: Check firewall and network connectivity

### Tunarr Integration Problems
**Problem**: Channel creation fails with Tunarr

**Solutions**:
1. **Check Tunarr Status**: Ensure Tunarr server is running
2. **Web Interface Access**: Verify you can access Tunarr web UI
3. **Version Requirements**: Ensure compatible Tunarr version
4. **Cutless Mode**: Note that Cutless Mode requires DizqueTV

### Flex Injection Fails
**Problem**: Commercial breaks not properly added

**Solutions**:
1. **DizqueTV Only**: Flex injection only works with DizqueTV
2. **Post-Channel Creation**: Run flex injection after channel creation
3. **API Permissions**: Ensure DizqueTV API access is working
4. **Channel Exists**: Verify channel was created successfully first

---

## Network Switching Issues

### “Validation failed” when changing network
- Ensure you have an active internet connection (validator checks Wikipedia).
- Use the exact network name Wikipedia uses (e.g., “Cartoon Network”, “Disney Channel”).
- Multi‑word names are supported; you do not need underscores.
- Try again later — Wikipedia may rate‑limit requests in some environments.

### Changed network but UI didn’t update
- TOM/Absolution must restart to fully apply the change. “Apply & Restart” will re‑exec the app; if that fails (restricted environment), restart the process manually.

---

## File Naming Issues

### Shows Not Recognized
**Problem**: Anime not detected by ToonamiChecker

**Solutions**:
1. **Check Naming Format**: Must be `Show Name - S##E## - Title`
2. **Show Name Matching**: Verify show names match expected format
3. **Manual Addition**: Use [Manual Show Adder](Component-Documentation.md#manual-show-adder)
4. **Database Update**: Show may not be in Toonami database

### Bumps Not Found
**Problem**: Bump files not recognized during lineup creation

**Solutions**:
1. **Follow Naming Convention**: Use exact [bump naming format](File-Naming-Conventions.md#bump-naming)
2. **Show Name Consistency**: Ensure bump show names match episode show names
3. **Version Numbers**: Include Toonami version in bump names
4. **Placement Keywords**: Use correct transition keywords

---

## Performance Issues

### High Memory Usage
**Problem**: Application uses excessive RAM

**Solutions**:
1. **Process Smaller Batches**: Select fewer files at once
2. **Close Other Applications**: Free up system memory
3. **Increase Virtual Memory**: Adjust system swap/page file settings
4. **Use Cutless Mode**: Reduces memory requirements

### Slow Processing
**Problem**: Operations take much longer than expected

**Solutions**:
1. **SSD Storage**: Use solid-state drives for working directory
2. **Local Processing**: Avoid network drives for intensive operations
3. **Hardware Upgrade**: Consider faster CPU for encoding operations
4. **Background Tasks**: Minimize other system activities

---

## Database Issues

### Database Corruption
**Problem**: SQLite database errors or crashes

**Solutions**:
1. **Delete Database**: Remove `Toonami.db` and restart
2. **Backup Regularly**: Keep copies of working database
3. **Check Disk Space**: Ensure adequate storage available
4. **Rebuild Database**: Re-run content preparation steps

### Inconsistent State
**Problem**: Application behavior seems erratic

**Solutions**:
1. **Clear Cache**: Delete temporary files in working directory
2. **Reset Configuration**: Restart configuration process
3. **Fresh Start**: Clear database and reconfigure from scratch

---

## Docker Issues

### Container Won't Start
**Problem**: Docker container fails to launch

**Solutions**:
1. **Check Environment Variables**: Verify `.env` file configuration
2. **Volume Mounts**: Ensure paths exist and are accessible
3. **Port Conflicts**: Verify port 8081 is available
4. **Docker Resources**: Allocate sufficient memory/CPU to Docker

### Volume Mount Problems
**Problem**: Files not accessible inside container

**Solutions**:
1. **Path Format**: Use absolute paths in docker-compose.yml
2. **Permissions**: Ensure Docker has access to mounted directories
3. **Path Existence**: Verify all mounted paths exist on host
4. **SELinux/Security**: Check if security policies block access

---

## Common Error Messages

### "No shows found in library"
- **Check Library Type**: Must be TV Shows library
- **Verify Content**: Ensure anime files are present and named correctly
- **Plex Scan**: Force library refresh in Plex

### "Unable to find FFmpeg"
- **Install FFmpeg**: See [FFmpeg installation instructions](#ffmpeg-not-found)
- **Update Config**: Verify FFmpeg path in config.py
- **Environment PATH**: Ensure FFmpeg is in system PATH

### "Platform not supported"
- **Choose Platform**: Select either DizqueTV or Tunarr in interface
- **Version Check**: Ensure compatible platform version
- **Network Access**: Verify platform server is reachable

### "Cutless mode requires DizqueTV fork"
- **Use Our Fork**: Install [theweebcoders/dizquetv](https://github.com/theweebcoders/dizquetv)
- **Or Use Traditional**: Disable Cutless Mode for standard cutting

---

## Getting More Help

If issues persist:

1. **Check FAQ**: Review [FAQ.md](FAQ.md) for additional solutions
2. **Discord Community**: Join our [Discord](https://discord.gg/S7NcUdhKRD)
3. **GitHub Issues**: Create an issue with detailed error information
4. **Log Files**: Include relevant log files and error messages
5. **ChatGPT**: Give all these documents and a link to the repo to ChatGPT for assistance

### Useful Information to Include

When reporting issues, provide:
- Operating system and version
- Python version
- Error messages (full text)
- Steps to reproduce
- File naming examples
- Configuration settings (without sensitive data)

---

## Prevention Tips

### Best Practices
1. **Use Chapter Markers**: Source content with embedded chapters
2. **Consistent Naming**: Follow naming conventions exactly
3. **Regular Backups**: Save working database and configurations
4. **Test Small**: Start with a few episodes before processing large libraries
5. **Monitor Resources**: Ensure adequate disk space and memory
6. **Update Regularly**: Keep software and dependencies current

### Performance Optimization
1. **SSD Storage**: Use fast storage for working directories
2. **Local Processing**: Avoid network drives during processing
3. **Batch Intelligently**: Process similar content together
4. **Clean Regularly**: Remove temporary files and unused data
