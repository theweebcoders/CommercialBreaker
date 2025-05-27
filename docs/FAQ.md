# Frequently Asked Questions (FAQ)

Common questions and answers about CommercialBreaker & Toonami Tools.

## General Questions

### Q: What exactly does this software do?

**A**: CommercialBreaker & Toonami Tools recreate the authentic Toonami experience by:
- Automatically detecting commercial break points in anime episodes
- Cutting episodes at these points (or creating virtual cuts)
- Organizing Toonami bumps and transitions
- Creating continuous Toonami-style channels with proper commercial breaks
- Integrating with Plex, DizqueTV, and Tunarr for seamless playback

### Q: Do I need to have original commercials?

**A**: No! The software creates the commercial break *points* where ads would go. You can:
- Find vintage commercials online to insert
- Use modern commercials
- Create custom content like trailers or fanmade bumps
- Leave the breaks empty for authentic "intermission" feeling

### Q: Does this damage my original anime files?

**A**: No. CommercialBreaker never modifies your original files unless you specifically enable "Destructive Mode." By default:
- **Traditional Mode**: Creates new cut files, preserves originals
- **Cutless Mode**: No physical cutting at all, just metadata

---

## Performance and Processing

### Q: How long does this take to run?

**A**: Processing time varies dramatically based on your setup:

- **With Chapter Markers + ToonamiTools filtering**: 30 minutes - 1 hour
- **With Plex Timestamps + filtering**: 2-20 hours  
- **Black frame detection on full library**: Days to weeks
- **Low Power Mode**: 1-3 hours

**Speed Tips**:
1. Use sources with chapter markers (80,000x faster!)
2. Filter shows with ToonamiTools first
3. Enable Fast Mode or Low Power Mode
4. Process in smaller batches

### Q: Why is chapter marker detection so much faster?

**A**: Chapter markers are pre-calculated metadata in the video file. Black frame detection requires:
- Reading every frame of video
- Analyzing audio levels
- Processing millions of data points
- Encoding temporary files

Chapter markers skip all this computational work.

### Q: My computer isn't very powerful. Can I still use this?

**A**: Yes! Use these strategies:
- **Low Power Mode**: Chapter markers and Plex timestamps only
- **Small Batches**: Process 5-10 episodes at a time
- **Cutless Mode**: Reduces processing and storage requirements
- **Filtered Selection**: Only process shows you'll actually use

---

## Mode Differences

### Q: What's the difference between Traditional cutting and Cutless Mode?

**A**: 

**Traditional Cutting**:
- ✅ Works with any platform (DizqueTV, Tunarr, etc.)
- ✅ Creates actual separate video files
- ❌ Uses 2-3x more disk space
- ❌ Longer processing time

**Cutless Mode**:
- ✅ Preserves original files completely
- ✅ Faster processing after detection
- ✅ Saves massive amounts of disk space
- ❌ Only works with our DizqueTV fork
- ❌ Limited platform compatibility

### Q: When should I use Destructive Mode?

**A**: Only if you're confident and need to save space:
- You've tested cutting on a few episodes first
- You have backups of important files
- Disk space is critically limited
- You don't plan to use files elsewhere

**Never use Destructive Mode on your only copy of rare content!**

---

## Platform Integration

### Q: Can I use this with Jellyfin or Emby?

**A**: Not directly. The software currently supports:
- **Plex** (for content management and timestamp extraction)
- **DizqueTV** (for channel creation and playback)
- **Tunarr** (for channel creation, traditional cutting only)

Community contributions for other platforms are welcome!

### Q: What's this about a "DizqueTV fork"?

**A**: For Cutless Mode, you need our modified version of DizqueTV that understands start/end timestamps. You can:
- Use our fork: [theweebcoders/dizquetv](https://github.com/theweebcoders/dizquetv)
- Use the official dev branch (may have issues)
- Use traditional cutting with any DizqueTV version

### Q: Why doesn't Cutless Mode work with Tunarr?

**A**: Tunarr doesn't currently support the timestamp parameters needed for virtual cutting. This feature would need to be added to Tunarr itself.

---

## File Organization

### Q: How strict are the naming requirements?

**A**: Very strict. The software uses regex patterns to identify content:

**Episodes MUST be**: `Show Name - S##E## - Title.ext`
**Bumps MUST follow**: [Specific bump naming convention](File-Naming-Conventions)

Even small deviations (like missing spaces around hyphens) will cause files to be ignored.

### Q: Can I add shows that weren't actually on Toonami?

**A**: Yes! Use the Manual Show Adder tool:
- Add your custom show to the database
- Create appropriate bumps ("to ads", "back", "generic")
- The show will be integrated into lineup generation
- Make sure the show is cut first

### Q: How do I fix naming issues in my existing library?

**A**: Several approaches:
1. **Bulk rename tools**: Use software like Bulk Rename Utility
2. **Plex naming**: Let Plex identify shows, then use our Plex tools
3. **Manual fixing**: Rename files to match the required pattern
4. **Scripted solutions**: Write scripts to automate renaming

---

## Technical Issues

### Q: I get "WinError 2: The system cannot find the file specified"

**A**: This usually means FFmpeg isn't installed or found:
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org)
2. Place executables in `Tools/` folder
3. Or install via package manager (Chocolatey, Homebrew, etc.)
4. Update `config.py` with correct paths if needed

### Q: Why do you include FFmpeg paths in config instead of using system PATH?

**A**: Originally needed because Windows PATH broke with apostrophes in usernames. Now supports both methods, but we kept the option for:
- Users with path issues
- Containerized deployments
- Multiple FFmpeg versions
- Portable installations

### Q: The cutting stopped partway through. What now?

**A**: Use the Part Renamer tool in Extra Tools:
1. Update the cut folder path in the script
2. Run it to standardize part numbering
3. Delete .txt files for successfully cut shows
4. Re-run cutting - it will only process shows with .txt files remaining

---

## Content and Usage

### Q: Where do I get Toonami bumps?

**A**: Several sources:
- **Archive.org**: Historical Toonami content
- **YouTube**: Fan uploads and collections
- **Fan Communities**: Discord servers and forums
- **Personal Recording**: If you recorded Toonami broadcasts
- **Create Your Own**: Using video editing software

### Q: Can I adjust commercial break timing?

**A**: Yes! Two methods:
1. **Manual editing**: Edit the .txt timestamp files directly
2. **Timestamp Editor**: Use the GUI tool in ExtraTools for easier editing

### Q: What if my episodes already have commercials in them?

**A**: The software detects potential break points but doesn't remove existing commercials. You could:
- Manually edit timestamps to remove commercial segments
- Use video editing software to clean episodes first
- Accept that some "breaks" might be within existing commercial blocks

---

## Advanced Usage

### Q: Can I create multiple channels?

**A**: Absolutely! The software supports:
- Different Toonami versions (Original, 2.0, 3.0, Mixed)
- Cut vs Uncut versions
- Continuing where previous channels left off
- Custom channel numbering
- Different show selections per channel

### Q: How does the "continue from last episode" feature work?

**A**: When enabled:
1. The system tracks which episodes were used in previous channels
2. New channels start from the next available episode
3. If Naruto ended at episode 26, the next channel starts at episode 27
4. Helps create ongoing, continuous Toonami marathons

### Q: What are "Special Bumps"?

**A**: Content that made Toonami unique beyond just anime:
- Music videos
- Game reviews
- Tech segments
- Anime industry coverage
- Original Toonami productions
- You can add any content here for variety

---

## Development and Customization

### Q: Can I modify the software for my needs?

**A**: Yes! The project is free and open source:
- Fork the repository
- Modify components as needed
- Submit pull requests for improvements
- Check the [Developer Guide](Developer-Guide) for technical details

### Q: Why is the naming scheme inconsistent in the code?

**A**: The project evolved over time and multiple contributors added features. Some inconsistencies remain for backward compatibility. It's a known issue we're gradually addressing.

### Q: What are Toonami versions 7, 8, and 9 in the code?

**A**: Internal placeholders:
- **Version 7**: Custom bumps and future features
- **Version 8**: Mixed version lineups
- **Version 9**: Original Toonami (renamed from "1" due to database issues)

### Q: Are you real programmers?

**A**: As the README honestly states: "We have no idea what we are doing; we're not ever real programmers; we're just nerds who like anime and Toonami." This is a passion project by anime fans who learned programming to solve a problem nobody else would tackle.

---

## Philosophical Questions

### Q: Why add commercials back to ad-free content?

**A**: Nostalgia and authenticity. Many people have fond memories of Toonami marathons where commercials were part of the experience - providing anticipation, bathroom breaks, snack runs, and that specific rhythm of late-night anime viewing.

### Q: Isn't this a waste of time/effort?

**A**: Yes!

### Q: How much time did you spend on this?

**A**: "More than 2 years and six months of my own time on a project that will only be used by a handful of people and cannot be monetized in any way." But we regret nothing.

---

## Getting Help

### Q: Where can I get support?

**A**: Multiple channels:
1. **Discord**: [Join our community](https://discord.gg/S7NcUdhKRD)
2. **GitHub Issues**: Report bugs and request features
3. **Documentation**: Check [Troubleshooting](Troubleshooting) guide
4. **FAQ**: You're reading it!
5. **ChatGPT**: Give them all these documents and a link to the repo for assistance

### Q: How can I contribute?

**A**: Several ways:
- **Bug Reports**: Help identify and fix issues
- **Feature Requests**: Suggest improvements
- **Code Contributions**: Submit pull requests
- **Documentation**: Improve guides and explanations
- **Testing**: Try new features and report results
- **Community Support**: Help other users in Discord
- **Buy Us a Coffee**: Support development with a small donation

### Q: Will you add [specific feature]?

**A**: Maybe! We're open to suggestions, especially:
- Features that improve the core Toonami experience
- Platform integrations (if we can test them)
- Quality of life improvements
- Bug fixes and optimizations

File an issue on GitHub to discuss your idea!

---

*Remember: "Until next time, stay gold, Space Cowboy!"*
