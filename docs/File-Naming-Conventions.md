# File Naming Conventions

Proper file naming is crucial for CommercialBreaker & Toonami Tools to work correctly. This guide outlines the exact naming schemes required for episodes and bumps.

## Episode File Naming

### Required Format

```
[SHOW_TITLE] - S[SEASON_NUMBER]E[EPISODE_NUMBER] - [OPTIONAL_DESCRIPTION]
```

### Rules

- **Show title** followed by space, hyphen, space
- **Season**: Always two digits (S01, S02, etc.)
- **Episode**: Always two digits (E01, E28, etc.)
- **Description**: Everything after the second hyphen is optional

### Examples

✅ **Correct naming:**
```
Naruto - S01E28 - Eat or Be Eaten - Panic in the Forest Bluray-1080p Remux.mkv
One Piece - S11E01 - Marine High Admiral Aokiji! The Threat of the Greatest Power.mp4
Bleach - S02E15 - Ishida's Strategy! The 20-second Offense and Defense.mkv
Cowboy Bebop - S01E01 - Asteroid Blues.mkv
```

❌ **Incorrect naming:**
```
Naruto S01E28.mkv                    # Missing hyphens and spaces
Naruto-S1E28.mkv                     # Wrong separator, single digit season
One Piece S11 E01.mkv                # Inconsistent spacing
Bleach_S02E15.mkv                    # Underscores instead of hyphens
```

### Important Notes

- Deviations from this scheme will cause episodes to be ignored
- The system uses this pattern for regex matching
- File extensions can be any video format (.mkv, .mp4, .avi, etc.)
- Optional description can include quality info, release groups, etc.

---

## Bump File Naming

Bump naming is more complex as it varies based on the number of shows involved in each bump.

### General Rules

- Maintain **spaces between each component** (underscores are acceptable if consistent)
- Components like AD_VERSION or COLOR might not always be necessary
- **All bumps must follow these schemes** or they won't be used
- Multi-show bumps use different patterns based on show count

### Network and Version Components

**Network**: The network name configured in `config.network`
- **Standard**: "Toonami" (default)
- **Networkless Mode**: "Networkless" - bypasses Wikipedia validation, allows any custom content
- **Other Networks**: "Cartoon Network", "Adult Swim", etc. (must have Wikipedia broadcast list page)

**Toonami Version**: The era/version with space replacing the period
- `1 0` = Original Toonami (OG)
- `2 0` = Toonami 2.0
- `3 0` = Toonami 3.0
- `7 0` = Custom bumps (recommended for user-created content)
- Missing version defaults to `1 0` (OG)

**Important**: When using **Networkless mode** (`config.network = "Networkless"`), all bump filenames must use "Networkless" as the network prefix instead of "Toonami". See examples below.

---

## Bump Types and Naming Schemes

### 1. Generic Bumps (No Shows)

**Pattern**: `[Network] [TOONAMI_VERSION] [SPECIAL_SHOW_NAME] [AD_VERSION]`

**Examples**:
```
Toonami 2 0 robots 03.mp4
Toonami 3 0 clydes 04.mp4
Toonami 2 0 sara 01.mp4
```

**Networkless Examples**:
```
Networkless 2 0 robots 03.mp4
Networkless 3 0 clydes 04.mp4
Networkless 7 0 sara 01.mp4
```

**Use**: General bumps, character appearances, station IDs

---

### 2. Single Show Bumps

**Pattern**: `[Network] [TOONAMI_VERSION] [SHOW_NAME] [PLACEMENT] [AD_VERSION] [COLOR]`

**Placement Options**:
- `back` - "We'll be right back"
- `to ads` - Going to commercial
- `generic` - General show bump
- `intro` - Show introduction
- `next` - "Coming up next"

**Examples**:
```
Toonami 2 0 Gundam back 4 red.mp4
Toonami 2 0 Gundam to ads 05 blue.mp4
Toonami 2 0 Gundam generic 09.mp4
Toonami 2 0 Gundam intro.mp4
Toonami 2 0 Gundam next 12 purple.mp4
```

**Networkless Examples**:
```
Networkless 2 0 Gundam back 4 red.mp4
Networkless 2 0 Naruto to ads 05 blue.mp4
Networkless 7 0 One Piece intro.mp4
```

---

### 3. Transitional Bumps (Two Shows)

**Pattern**: `[Network] [TOONAMI_VERSION] [SHOW_1] [TRANSITION] [SHOW_2] [AD_VERSION] [COLOR]`

**Transition Options**:
- `Next From` - "Next from [Show 1] to [Show 2]"  
- `From` - "From [Show 1] to [Show 2]"

**Examples**:
```
Toonami 2 0 Gundam Next From Evangelion 05 blue.mp4
Toonami 2 0 Inuyasha From Evangelion 7 blue.mp4
Toonami 3 0 Naruto Next From Bleach 02.mp4
```

**Networkless Examples**:
```
Networkless 2 0 Gundam Next From Evangelion 05 blue.mp4
Networkless 3 0 Naruto From Bleach 02.mp4
```

---

### 4. Triple Bumps (Three Shows)

**Pattern**: `[Network] [TOONAMI_VERSION] [NOW] [SHOW_1] [NEXT] [SHOW_2] [LATER] [SHOW_3] [AD_VERSION] [COLOR]`

**Keywords**:
- `Now` - Optional opener
- `Next` - Required between shows
- `Later` - Required before final show

**Examples**:
```
Toonami 2 0 Now Gundam Next Evangelion Later Cowboy Bebop 10 green.mp4
Toonami 3 0 Now Inuyasha Next Bleach Later Naruto 2.mp4
Toonami 2 0 Gundam Next Evangelion Later Cowboy Bebop 05.mp4
```

**Networkless Examples**:
```
Networkless 2 0 Now Gundam Next Evangelion Later Cowboy Bebop 10 green.mp4
Networkless 7 0 Now Naruto Next Bleach Later One Piece 05.mp4
```

---

## Component Reference

### Required Components

| Component | Description | Examples |
|-----------|-------------|----------|
| Network | Network from `config.network` | `Toonami`, `Networkless`, `Cartoon Network` |
| Version | Era with space for period | `2 0`, `3 0`, `7 0` |
| Show Name | Exact show name | `Gundam`, `Naruto`, `One Piece` |

### Optional Components

| Component | Description | Examples |
|-----------|-------------|----------|
| AD_VERSION | Numeric identifier | `01`, `05`, `12` |
| COLOR | Thematic categorization | `red`, `blue`, `green` |
| PLACEMENT | Single show context | `back`, `intro`, `next` |

### Transition Keywords

| Type | Keywords | Usage |
|------|----------|-------|
| Single | `back`, `to ads`, `generic`, `intro`, `next` | Show-specific context |
| Double | `Next From`, `From` | Between two shows |
| Triple | `Now`, `Next`, `Later` | Three-show lineup |

---

## Common Naming Mistakes

### Episodes
❌ **Missing spaces around hyphens**
```
Naruto-S01E01-Title.mkv
```
✅ **Correct spacing**
```
Naruto - S01E01 - Title.mkv
```

❌ **Single digit season/episode**
```
Naruto - S1E1 - Title.mkv
```
✅ **Two digit format**
```
Naruto - S01E01 - Title.mkv
```

### Bumps
❌ **Missing version**
```
Toonami Gundam back.mp4
```
✅ **Include version**
```
Toonami 2 0 Gundam back.mp4
```

❌ **Wrong transition keywords**
```
Toonami 2 0 Gundam to Evangelion.mp4
```
✅ **Correct transition**
```
Toonami 2 0 Gundam Next From Evangelion.mp4
```

---

## Show Name Mapping

Some shows have common abbreviations that the system recognizes eg:

| Full Name | Acceptable Variations |
|-----------|----------------------|
| Fullmetal Alchemist Brotherhood | `fmab`, `FMAB` |
| Dragon Ball Z | `dbz`, `DBZ` |

---

## Validation Tips

### Before Processing
1. **Check episode naming**: Use regex pattern `^.+ - S\d{2}E\d{2} - .+$`
2. **Verify bump structure**: Ensure correct component order
3. **Test with samples**: Process a few files first
4. **Use consistent formatting**: Don't mix underscores and spaces

### Tools for Validation
- **Bulk rename utilities**: PowerRename (Windows), Name Mangler (Mac)
- **Regex tools**: Test naming patterns before batch operations
- **File organization**: Group by naming scheme compliance

---

## Special Cases

### Custom Bumps
Use Toonami version `7 0` for user-created bumps:
```
Toonami 7 0 Custom Show back 01.mp4
```

### Missing Components
- AD_VERSION can be omitted for unique bumps
- COLOR is always optional
- Version defaults to `1 0` if missing

### Multiple Versions
If you have multiple versions of the same bump:
```
Toonami 2 0 Gundam back 01 red.mp4
Toonami 2 0 Gundam back 02 red.mp4
Toonami 2 0 Gundam back 03 blue.mp4
```

---

## Troubleshooting Naming Issues

### Episodes Not Detected
- Check for exact spacing: ` - S##E## - `
- Verify two-digit season/episode numbers
- Ensure no extra characters in critical positions

### Bumps Not Used
- Validate component order matches patterns above
- Check for typos in show names
- Ensure proper spacing between components
- Verify Toonami version format

### Show Name Mismatches
- Use exact names as they appear in your anime library
- Check for common abbreviations in the code
- Consider adding custom mappings if needed

---

## Technical Implementation: FilenameParser

CommercialBreaker uses a centralized `FilenameParser` utility for consistent episode filename parsing across all modules.

### Location and Purpose

**Module**: `ToonamiTools/utils/FilenameParser.py`

**Why FilenameParser Exists**:
- Provides single source of truth for filename parsing
- Ensures consistent behavior across all modules
- Easier to maintain and test than duplicate parsing logic

### Key Features

**Automatic Year Handling**:
```python
# Automatically strips release years from show names
"Naruto (2002) - S01E05 - Title.mkv" → Show: "Naruto"
"Attack on Titan (2013) - S01E01.mkv" → Show: "Attack on Titan"
```

**Comprehensive SxxExx Extraction**:
- Handles both uppercase and lowercase (S01E05, s01e05)
- Supports single and double-digit seasons/episodes
- Validates format correctness

**Show Name Normalization**:
- Removes release years in parentheses
- Trims whitespace
- Validates show name is not empty

### Usage Example

```python
from ToonamiTools.utils.FilenameParser import FilenameParser

parser = FilenameParser()

# Parse episode filename
result = parser.parse_episode_filename("Naruto (2002) - S01E05 - Episode Title.mkv")

# Returns:
{
    'show': 'Naruto',           # Year stripped automatically
    'season': '01',             # Always two digits
    'episode': '05',            # Always two digits
    'full_pattern': 'S01E05',   # Original pattern
    'description': 'Episode Title'  # Optional description
}

# Invalid filename returns None
result = parser.parse_episode_filename("Invalid Filename.mkv")
# Returns: None
```

### Modules Using FilenameParser

**Core Processing**:
- `VirtualCut.py` - Cutless mode operations
- `DirectoryScanner.py` - File discovery and organization
- `BlockMaker.py` - BLOCK_ID generation

**Platform Integration**:
- `PlexToDizqueTV.py` - Channel creation
- `PlexToTunarr.py` - Channel creation

**Validation System**:
- All 20 validators use FilenameParser for consistency checks
- Ensures validators detect same patterns as main tools

### Validation Logic

**FilenameParser validates**:
1. **Pattern Presence**: SxxExx must exist in filename
2. **Format Correctness**: Season and episode must be two digits
3. **Show Name**: Must exist and be non-empty after extraction
4. **No Ambiguity**: Only one SxxExx pattern per filename

**Example Validation**:
```python
✅ "Naruto - S01E05 - Title.mkv"           # Valid
✅ "Naruto (2002) - S01E05.mkv"            # Valid (year stripped)
❌ "Naruto S01E05.mkv"                     # Invalid (missing hyphens)
❌ "Naruto - S1E5 - Title.mkv"             # Invalid (single digits)
❌ "Movie - Title.mkv"                     # Invalid (no pattern)
```

### Benefits for Users

**Consistency**:
- Same parsing logic everywhere
- Predictable behavior across all tools
- No "works here but not there" issues

**Reliability**:
- Comprehensive validation catches malformed names
- Clear error messages when parsing fails
- Prevents silent failures

**Maintainability**:
- Single place to fix bugs or update logic
- All modules benefit from improvements
- Easier to add new features

### When FilenameParser is Used

**Automatic During**:
- Content discovery (scanning anime folders)
- Episode filtering (separating bumps from anime)
- Virtual cutting (cutless mode filename handling)
- BLOCK_ID generation (show name extraction)
- Channel creation (episode organization)
- Validation (all 20 validators)

**You Don't Call It Directly**:
- FilenameParser is used internally by the application
- Just ensure your files follow naming conventions
- System handles parsing automatically

### Error Reporting

When FilenameParser detects issues:
- S.A.R.A. validation shows which files failed parsing
- Error messages indicate which naming rule violated
- Suggestions provided for fixing filenames

**Example S.A.R.A. Output**:
```
[WARNING] ToonamiChecker → Toonami_Episodes
Message: 3 episode(s) have non-standard naming
Details: Expected format: [SHOW] - S##E## - [title].ext
Files affected:
  • /anime/Naruto S01E05.mkv (missing hyphens)
  • /anime/One Piece - S1E1.mkv (single digit season/episode)
  • /anime/Bleach_S02E15.mkv (underscores instead of hyphens)
Suggestion: Rename files to match required format. Use batch renaming tools if needed.
```

---

Need help with naming? Check the [FAQ](FAQ.md) for additional examples and solutions, or join our [Discord community](https://discord.gg/S7NcUdhKRD) for assistance.
