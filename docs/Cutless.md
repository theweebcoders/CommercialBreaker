# Cutless Mode Guide

## What is Cutless Mode?

Cutless Mode is a revolutionary feature in CommercialBreaker that identifies commercial break points without physically cutting your video files. Instead of creating multiple file segments, it generates metadata that tells your playback system exactly where commercial breaks should occur, preserving space while delivering the authentic Toonami experience.

## Why Cutless Mode is the Future

### Key Benefits

1. **Space Efficiency**: Zero additional disk space required
2. **Speed**: Much faster processing after initial detection phase
3. **Flexibility**: Easy to adjust break points without re-processing files
4. **Simplicity**: No file management headaches with multiple parts
5. **Preserves Metadata**: Since files remain intact, Plex retains all metadata
   - Beautiful episode thumbnails display correctly
   - Full episode descriptions remain available
   - Series information stays complete
   - No more generic "Part 1", "Part 2" entries losing context

### How It Works

Instead of cutting `Naruto - S01E01.mkv` into:
- `Naruto - S01E01 - Part 1.mkv`
- `Naruto - S01E01 - Part 2.mkv`
- `Naruto - S01E01 - Part 3.mkv`

Cutless Mode creates metadata like:
```
Naruto - S01E01.mkv
  Break 1: Start at 0:00, End at 7:23
  Break 2: Start at 7:53, End at 15:47
  Break 3: Start at 16:17, End at 22:30
```

## Important Caveats

### 1. DizqueTV Fork Requirement

**You must use our fork of DizqueTV**: [https://github.com/theweebcoders/dizquetv](https://github.com/theweebcoders/dizquetv)

While the official DizqueTV dev branch theoretically supports the timestamp features, it hasn't accepted all our patches and may have compatibility issues. Our fork is:
- Constantly updated with the latest Cutless Mode improvements
- Thoroughly tested with CommercialBreaker
- Guaranteed to work with all Cutless features

### 2. Beta Status

Cutless Mode is currently in beta. What this means:
- Most functionality works great
- Occasional hiccups may occur
- We're actively improving based on user feedback
- Given that it doesn't use disk space, there's minimal risk in trying it

### 3. Platform Limitations

- **DizqueTV Only**: Currently only works with our DizqueTV fork
- **Not Compatible with Tunarr**: The required timestamp features aren't available
- **Future Platform Support**: We're exploring adding support for other platforms

## Installation & Setup

### Step 1: Install Our DizqueTV Fork

```bash
# Clone our fork
git clone https://github.com/theweebcoders/dizquetv.git
cd dizquetv
```
then either 
```bash
docker build -t dizquetv . 

docker run -d -p 8000:8000 --name dizquetv dizquetv
```
or if you prefer to run it directly:

```bash
# Install and run
npm install
npm start
```

### Step 2: Enable Cutless Mode

#### Understanding the Checkboxes

CommercialBreaker has several processing mode checkboxes that interact with each other:

- **Destructive Mode**: Deletes original files after processing (incompatible with Cutless)
- **Fast Mode**: Changes the processing priority see User Guides (incompatible with Low Power Mode)
- **Low Power Mode**: Does not use silent black frame detection (incompatible with Fast Mode)
- **Cutless Mode**: Creates virtual cuts instead of physical files (incompatible with Destructive Mode)

**Important Checkbox Rules:**
- When you check **Cutless Mode**, **Destructive Mode** automatically unchecks (and vice versa)
- The Cutless Mode checkbox only appears when using DizqueTV and the `--cutless` flag

#### For TOM (GUI)
1. Launch with cutless flag:
   ```bash
   python3 main.py --tom --cutless
   ```
2. The Cutless Mode checkbox will appear in the interface
3. Check the box before processing

#### For Absolution (Web)
1. Launch with cutless flag:
   ```bash
   python3 main.py --webui --cutless
   ```
2. The Cutless Mode option will be available in settings

#### For Clydes (CLI)
1. Launch with cutless flag:
   ```bash
   python3 main.py --clydes --cutless
   ```
2. You'll be prompted about using Cutless Mode during setup

#### For Docker

1. Ensure you have our DizqueTV fork running
2. Start CommercialBreaker normally as cutless is enabled by default

```bash
docker run -p 8081:8081 \
  -v "/path/to/your/Anime:/app/anime" \
  -v "/path/to/your/Bumps:/app/bump" \
  -v "/path/to/your/SpecialBumps:/app/special_bump" \
  -v "/path/to/your/Working:/app/working" \
  --name commercialbreaker \
  tim000x3/commercial-breaker:latest
```

#### Unraid Installation

Same as Docker, just ensure you have our DizqueTV fork running in Unraid. Use the Unraid Community App Store to install CommercialBreaker, and it will automatically enable Cutless Mode.

## Usage Workflow

### 1. Detection Phase (Same as Traditional)
- Commercial break points are detected using the same methods:
  - Chapter markers (fastest)
  - Plex timestamps
  - Silent/black frame detection
- This phase takes the same time regardless of mode

### 2. Processing Phase (Much Faster!)
- Instead of cutting files, metadata is generated instantly
- Database entries are created with:
  - Original file paths
  - Start/end timestamps for each segment
  - Show and episode information

### 3. Channel Creation
- When creating your DizqueTV channel, the system:
  - References original files in your Anime library
  - Adds timestamp metadata to each program entry
  - DizqueTV handles playback seamlessly

### 4. Playback Experience
- Videos start and stop at exact timestamps
- Commercial breaks occur naturally
- No visual difference from traditionally cut files
- Smoother transitions in many cases

## Bonus Tips

### DizqueTV EPG Configuration

When using our DizqueTV fork with Cutless Mode, we recommend optimizing your EPG (Electronic Program Guide) settings for the best experience:

1. **Navigate to Channel Settings → EPG Tab**

2. **Enable "Merge adjacent programs with same content"**
   - This crucial setting makes split shows appear as a single program in your guide
   - Even though a show might be split into 5 parts for commercial breaks, viewers will see it as one continuous program
   - Creates a cleaner, more professional-looking guide

3. **Set "Minimum program duration to appear in the TV guide" to 60 seconds**
   - Default is 300 seconds (5 minutes), which is too long for split content
   - Many segments (like show intros) are shorter than 5 minutes
   - Setting to 60 seconds ensures all parts appear and merge properly
   - Results in smoother guide navigation and better viewing experience

These settings work perfectly with Cutless Mode's virtual cuts, giving you the authentic Toonami experience with a clean, easy-to-navigate program guide.

## Technical Details

### Database Structure

Cutless Mode creates special tables suffixed with `_cutless`:
- `lineup_vX_cutless`

These tables include:
- `filename`: Original file path
- `startTime`: Where to begin playback (milliseconds)
- `endTime`: Where to stop for commercial break (milliseconds)

### File Organization

With Cutless Mode:
- **Anime Library**: Keep your original files here
- **Toonami Library**: Only needs bumps and special content
- **Working Folder**: Stores metadata, not video files

Traditional mode would require duplicating your entire anime collection in cut form. Cutless Mode eliminates this redundancy.

## Troubleshooting

### "Cutless Mode disabled: Platform not supported"
- Ensure you selected DizqueTV, not Tunarr
- Verify your DizqueTV URL is accessible
- Check you're using our fork, not standard DizqueTV
- **Automatic Detection**: If the Cutless option is missing on the CommercialBreaker page, you are using the wrong DizqueTV version. Switch to our fork to enable Cutless options.

### Channel shows full episodes instead of segments
- Confirm you're using our DizqueTV fork
- Check that Cutless Mode was enabled during processing
- Verify the `_cutless` tables exist in your database

### Processing seems to skip the cutting phase
- This is normal! Cutless Mode doesn't physically cut files
- Check your database for virtual cut entries
- Look for "Cutless Mode: Finalizing lineup tables" in the status

## Best Practices

1. **Start Small**: Test with a few episodes first
2. **Verify Fork**: Always use [our DizqueTV fork](https://github.com/theweebcoders/dizquetv)
3. **Check Status**: Look for "Cutless Mode enabled" in the logs
4. **Keep Originals**: Even though Cutless preserves files, maintain backups
5. **Report Issues**: Help us improve by reporting beta issues

## Future Development

We believe Cutless Mode represents the future of commercial injection because:

1. **Storage Efficiency**: As libraries grow, avoiding duplication becomes critical
2. **Speed**: Virtual cuts are instantaneous after detection
3. **Scalability**: Process thousands of episodes without storage concerns

We're actively working on:
- Tunarr compatibility
- Enhanced timestamp precision
- Additional platform support
- Performance optimizations

## Conclusion

While Cutless Mode is in beta, it's stable enough for daily use and offers compelling advantages over traditional cutting. The minimal risk (no disk space used, original files untouched) makes it worth trying, especially if you're:

- Limited on storage space
- Want faster processing
- Willing to use our DizqueTV fork

Give it a try - we think you'll agree it's the future of commercial injection!

---

*Note: Always use `--cutless` flag when launching CommercialBreaker to enable this feature.*