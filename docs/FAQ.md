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
- ❌ Requires DizqueTV 1.7+
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

### Q: What DizqueTV version do I need for Cutless Mode?

**A**: Cutless Mode requires DizqueTV 1.7+ Traditional cutting works with any DizqueTV version.

### Q: Why doesn't Cutless Mode work with Tunarr?

**A**: Tunarr doesn't currently support the timestamp parameters needed for virtual cutting. This feature would need to be added to Tunarr itself.

---

## File Organization

### Q: How strict are the naming requirements?

**A**: Very strict. The software uses regex patterns to identify content:

**Episodes MUST be**: `Show Name - S##E## - Title.ext`
**Bumps MUST follow**: [Specific bump naming convention](File-Naming-Conventions.md)

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

## S.A.R.A. & Validation

### Q: What is S.A.R.A.?

**A**: **S.A.R.A. (System Analysis and Reporting Assistant)** is the comprehensive database validation and diagnostics system. It validates all 20 pipeline steps, checks data integrity, detects platform compatibility issues, and provides actionable suggestions for fixing problems.

S.A.R.A. follows the philosophy: **"Validate everything, trust nothing."**

### Q: How do I access S.A.R.A. diagnostics?

**A**: **Hidden Panic Button**: Click any page title 5 times in 2 seconds

The panic button is an easter egg feature for quick diagnostic access.

### Q: When should I run diagnostics?

**A**: Run S.A.R.A. diagnostics:
- **After initial setup** - Verify configuration is correct
- **After content preparation** - Ensure all content processed successfully
- **After commercial detection** - Check all episodes have timestamps
- **Before channel creation** - Catch issues before final export
- **When troubleshooting** - Diagnose problems and get specific fixes

Use "Refresh Status" for quick checks (< 1 second), "Run Full Validation" for comprehensive analysis (5-30 seconds).

### Q: What do validation errors mean?

**A**: S.A.R.A. uses four severity levels:

- **CRITICAL (⊗)**: Step cannot proceed. Database table missing or corrupt. Fix immediately.
- **ERROR (✗)**: Significant data quality problems. Address before channel creation.
- **WARNING (⚠)**: Non-critical issues. Review but may be intentional.
- **INFO (ℹ)**: Informational messages. No action required.

Each issue includes:
- **What**: User-friendly description
- **Where**: Which step and table
- **Why**: Technical details
- **How to Fix**: Actionable suggestion

### Q: Can S.A.R.A. fix issues automatically?

**A**: No, S.A.R.A. is **read-only** and diagnostic only. It identifies problems and suggests fixes, but you must take action:
- Re-run the failing step
- Check configuration settings
- Verify file naming conventions
- Review platform compatibility

This design prevents automatic "fixes" that might make problems worse.

### Q: Why is there a "panic button"?

**A**: The panic button (click title 5 times in 2 seconds) provides diagnostic access when:
- Critical error breaks normal navigation
- You need quick access without memorizing menus
- Pipeline seems stuck and you want to check status

It's implemented on all pages (except Page5 in TOM due to layout complexity).

### Q: What's the difference between "Refresh Status" and "Run Full Validation"?

**A**:

**Refresh Status** (quick check):
- Takes < 1 second
- Checks which steps have completed
- Updates progress indicators
- Use for frequent monitoring

**Run Full Validation** (comprehensive check):
- Takes 5-30 seconds depending on database size
- Validates all 20 pipeline steps
- Checks data quality and integrity
- Cross-table consistency validation
- Use after major steps or when troubleshooting

### Q: How does S.A.R.A. know if I'm in cutless mode?

**A**: S.A.R.A. automatically detects your processing mode by checking:
- Existence of `_cutless` suffixed tables
- Timing columns in `commercial_injector_prep`
- `cutless_mode_used` flag in `app_data`
- Platform selection (cutless only works with DizqueTV/ComBreakDirect)

It will warn you about platform incompatibilities (e.g., cutless mode with Tunarr).

### Q: What are "integrity validators"?

**A**: In addition to 18 step validators, S.A.R.A. includes 2 cross-cutting integrity validators:

**LineupIntegrityValidator:**
- Validates bump placement rules
- Ensures multibumps are followed by anime
- Checks intro bumps match BLOCK_IDs
- Verifies "back" and "to ads" placement

**ReferentialIntegrityValidator:**
- Validates cross-table consistency
- Ensures BLOCK_IDs exist in lineup_prep
- Checks file paths are consistent
- Verifies show names match across tables

These catch issues that span multiple pipeline steps.

### Q: Can I use S.A.R.A. from the command line?

**A**: The S.A.R.A. interface currently lives inside the GUI apps:
- **TOM** (Tkinter): Native desktop Page8
- **Absolution** (Web): Browser-based Page8

Use one of those interfaces when you need database diagnostics. The Clydes CLI does not expose a standalone validation screen yet.

### Q: How do I include validation results in bug reports?

**A**: On Page8:
1. Run "Full Validation"
2. Wait for results to appear
3. Click "Copy All Results" button
4. Paste into your bug report or support request

The copied text includes:
- Pipeline status and completion percentage
- All validation issues with severity levels
- Detailed error messages and suggestions
- Metadata about platform, mode, and versions

This helps developers diagnose your issue quickly.

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

**For ComBreakDirect users**: this happens automatically and continuously. Every ComBreakDirect channel runs a `LineupExtender` watchdog that, a few hours before the channel ends, generates a fresh chunk of content with the per-show cursor already advanced — same mechanism, just always on. You don't toggle anything. Page 7 ("Let's Make Another Channel") is hidden for ComBreakDirect channels because there's nothing to do manually.

### Q: Do my ComBreakDirect channels ever run out?

**A**: No. Every ComBreakDirect channel is born with a self-extending watchdog: roughly three hours before the channel's last program would end, the system runs ShowScheduler again (with each show's cursor advanced past whatever just aired) and stitches the new chunk onto the end of the existing lineup. It's wall-clock based — fires whether or not anyone is currently streaming the channel — so if you walk away for a week and come back, the channel kept growing while you were gone. You can override the lead time with `INFINITE_EXTEND_LEAD_MS` in `config.py` if you want a different runway buffer. Default is 3 hours.

### Q: Can I disable the auto-extension on a ComBreakDirect channel?

**A**: It's not a UI toggle — the design assumption is that ComBreakDirect channels are infinite. If you really need to stop extension on a specific channel, edit `channels.json` (in `combreak_direct_data/` for native installs or the working folder for Docker) and set the channel's `_infinite_meta.enabled` to `false`. The watchdog will see that on its next tick and stop scheduling. The Studio's modulo loop will keep the channel playing what's already there, looping the existing content until the channel is removed.

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
- Check the [Developer Guide](Developer-Guide.md) for technical details

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
3. **Documentation**: Check [Troubleshooting](Troubleshooting.md) guide
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
