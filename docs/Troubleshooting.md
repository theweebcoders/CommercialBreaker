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

---

## Configuration Issues

### Plex Authentication Failed
**Problem**: Can't connect to Plex server

**Solutions**:
1. **Check Plex credentials**: Verify server URL and token
2. **Network connectivity**: Ensure Plex server is accessible
3. **Manual token entry**: Use Plex token directly if OAuth fails
4. **Firewall/VPN**: Check if network restrictions block access

### Library Not Found
**Problem**: Selected library doesn't appear or is empty

**Solutions**:
1. **Refresh Plex libraries**: Scan for new content
2. **Check file naming**: Ensure files follow [naming conventions](File-Naming-Conventions)
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
- Use [Manual Timestamp Editor](Component-Documentation#manual-timestamp-editor)
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

## File Naming Issues

### Shows Not Recognized
**Problem**: Anime not detected by ToonamiChecker

**Solutions**:
1. **Check Naming Format**: Must be `Show Name - S##E## - Title`
2. **Show Name Matching**: Verify show names match expected format
3. **Manual Addition**: Use [Manual Show Adder](Component-Documentation#manual-show-adder)
4. **Database Update**: Show may not be in Toonami database

### Bumps Not Found
**Problem**: Bump files not recognized during lineup creation

**Solutions**:
1. **Follow Naming Convention**: Use exact [bump naming format](File-Naming-Conventions#bump-naming)
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

1. **Check FAQ**: Review [FAQ](FAQ) for additional solutions
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
