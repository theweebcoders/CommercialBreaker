# Component Documentation

This document provides detailed information about each tool and module in the CommercialBreaker & Toonami Tools ecosystem.

## Processing Order Overview

The tools work together in a specific sequence to create your Toonami channel:

```
1. LoginToPlex → 2. ToonamiChecker → 3. LineupPrep → 4. ToonamiEncoder → 
5. UncutEncoder → 6. ShowScheduler (Merger) → 7. FilterAndMove (EpisodeFilter) → 8. GetPlexTimestamps → 
9. CommercialBreaker → 10. AnimeFileOrganizer (CommercialInjectorPrep) → 11. LineupLogic (CommercialInjector) → 
12. ShowScheduler (again) → 13. CutlessFinalizer → 14. PlexAutoSplitter (PlexSplitter) → 
15. PlexLibraryUpdater (PlexSplitRenamer) → 16. PlexToDizqueTV/PlexToTunarr → 17. DizqueTVManager (FlexInjector)
```

---

## Authentication & Setup Components

### LoginToPlex
**File**: `ToonamiTools/LoginToPlex.py`
**Classes**: `PlexServerList`, `PlexLibraryManager`, `PlexLibraryFetcher`
**Purpose**: Authenticates with Plex, retrieves a list of available Plex servers, and fetches libraries from a selected server. This information is crucial for other tools that interact with the user's Plex media.

**Key Features & Process**:

**`PlexServerList` Class**:
-   **Purpose**: Handles the initial Plex authentication and retrieves a list of servers associated with the user's account.
-   **Authentication (`GetPlexToken` method)**:
    -   Uses the `plexauth` library to initiate an OAuth flow with Plex.tv.
    -   Constructs a payload with `X-Plex-*` headers identifying the application ("Commercial Breaker").
    -   Obtains an authentication URL (`auth_url`) which the user must open in a browser to grant access.
    -   Supports a callback mechanism (`auth_url_callback`) to pass the `auth_url` to the GUI or other handlers (e.g., for display or automatic opening). If no callback is provided, it defaults to opening the URL in a web browser and printing it to the console.
    -   Waits for the user to authenticate and then retrieves the Plex access token.
    -   Stores the token (`self.plex_token`) and the list of server names (`self.plex_servers`).
-   **Server Listing (`GetPlexServerList` method)**:
    -   Calls `GetPlexToken` to ensure authentication.
    -   Uses the obtained token to connect to `MyPlexAccount` (from `plexapi.myplex`).
    -   Fetches the user's resources (Plex servers) and populates `self.plex_servers` with their names.
-   **Inputs**: User interaction for browser-based authentication.
-   **Outputs**:
    -   Plex authentication token (stored and accessible via `self.plex_token`).
    -   List of Plex server names (stored and accessible via `self.plex_servers`).
    -   Authentication URL (passed to callback or opened in browser).

**`PlexLibraryManager` Class**:
-   **Purpose**: Given a selected Plex server name and a token, it connects to that server and retrieves its base URL.
-   **Details Fetching (`GetPlexDetails` method)**:
    -   Takes the selected server name and Plex token.
    -   Connects to `MyPlexAccount` using the token.
    -   Finds the specified server resource from the account's resources.
    -   Connects to the selected Plex server (`selected_resource.connect()`).
    -   Stores the server's base URL (`plex._baseurl`) in `self.plex_url`.
-   **Inputs**: Selected Plex server name, Plex authentication token.
-   **Outputs**: Plex server base URL (e.g., `http://localhost:32400`).

**`PlexLibraryFetcher` Class**:
-   **Purpose**: Fetches a list of library names from a specific Plex server, given its URL and token.
-   **Library Fetching (`GetPlexLibraries` method)**:
    -   Takes the Plex server URL and token.
    -   Connects to the `PlexServer` using the provided URL and token.
    -   Retrieves all library sections (`server.library.sections()`).
    -   Populates `self.libraries` with the titles (names) of these libraries.
-   **Inputs**: Plex server base URL, Plex authentication token.
-   **Outputs**: List of library names available on the server.

**Workflow Integration**:
1.  `PlexServerList` is used first to log in and get available servers.
2.  The user selects a server.
3.  `PlexLibraryManager` uses the selected server name and token to get the server's URL.
4.  `PlexLibraryFetcher` uses the server URL and token to get the list of libraries on that server.
5.  The selected libraries (e.g., for anime, Toonami content) and Plex credentials (URL, token) are then stored (typically in `config.py` or a local database by `FrontEndLogic.py`) for use by other tools.

### LoginToJellyfin
**File**: `ToonamiTools/LoginToJellyfin.py`
**Classes**: `JellyfinServerList`, `JellyfinLibraryManager`, `JellyfinLibraryFetcher`
**Purpose**: Authenticates with Jellyfin, retrieves a list of available Jellyfin servers, and fetches libraries from a selected server. This provides Jellyfin support equivalent to the Plex authentication system.

**Key Features & Process**:

**`JellyfinServerList` Class**:
-   **Purpose**: Handles the initial Jellyfin authentication and retrieves server information.
-   **Authentication (`GetJellyfinToken` method)**:
    -   Uses Jellyfin's Quick Connect system for seamless authentication (similar to Plex PIN flow).
    -   Prompts for or receives a Jellyfin server URL as input.
    -   Initiates Quick Connect with the server and obtains a 6-digit code.
    -   Displays an authentication URL or code for the user to approve in their Jellyfin dashboard.
    -   Polls the server until authentication is completed and retrieves the access token.
    -   Stores the token (`self.jellyfin_token`) and user ID (`self.jellyfin_user_id`).
-   **Server Listing (`GetJellyfinServerList` method)**:
    -   Calls `GetJellyfinToken` to ensure authentication.
    -   Retrieves server information from the authentication credentials.
    -   Populates `self.jellyfin_servers` with server names (typically one server per Jellyfin instance).
-   **Inputs**: User interaction for Quick Connect authentication, Jellyfin server URL.
-   **Outputs**: 
    -   `self.jellyfin_token`: Jellyfin access token.
    -   `self.jellyfin_servers`: List of available Jellyfin server names.
    -   `self.jellyfin_user_id`: Authenticated user's ID.

**`JellyfinLibraryManager` Class**:
-   **Purpose**: Manages connection details for a selected Jellyfin server.
-   **Server Connection (`GetJellyfinDetails` method)**:
    -   Takes the selected server name, token, and user ID.
    -   Retrieves the server URL from stored credentials.
    -   Validates the connection and stores the server URL for future use.
-   **Inputs**: Selected server name, Jellyfin token, user ID.
-   **Outputs**: Jellyfin server base URL (e.g., `http://localhost:8096`).

**`JellyfinLibraryFetcher` Class**:
-   **Purpose**: Fetches a list of library names from a specific Jellyfin server.
-   **Library Fetching (`GetJellyfinLibraries` method)**:
    -   Takes the Jellyfin server URL, token, and user ID.
    -   Uses Jellyfin's REST API to fetch user-accessible libraries (`/Users/{userId}/Views`).
    -   Filters for media libraries (TV shows, movies, mixed content) that might contain anime.
    -   Populates `self.libraries` with the library names.
-   **Inputs**: Jellyfin server base URL, Jellyfin authentication token, user ID.
-   **Outputs**: List of library names available on the server.

**Workflow Integration**:
1.  `JellyfinServerList` is used first to authenticate and get server information.
2.  The user selects a server (typically only one available).
3.  `JellyfinLibraryManager` uses the server selection and credentials to get the server's URL.
4.  `JellyfinLibraryFetcher` uses the server URL and credentials to get the list of libraries.
5.  The selected libraries and Jellyfin credentials are stored for use by other tools like `JellyfinToTunarr`.

**Important Notes**:
-   Jellyfin integration only works with Tunarr (not DizqueTV).
-   Uses Quick Connect for authentication, providing a user experience similar to Plex PIN authentication.
-   Requires a Jellyfin server URL as input (unlike Plex which can discover servers).

---

## Content Discovery Components

### ToonamiChecker
**File**: `ToonamiTools/toonamichecker.py`
**Classes**: `ToonamiShowsFetcher`, `ToonamiChecker`
**Purpose**: Identifies which shows in the user's local anime folder are known to have aired on the configured network (eg. Toonami) by cross-referencing with a list fetched from Wikipedia. It then saves this information, including file paths, to a database.

**Key Features & Process**:

**`ToonamiShowsFetcher` Class**:
-   **Purpose**: Fetches a list of programs broadcast by a specified network (e.g., "Toonami", configurable via `config.network`) from Wikipedia.
-   **Data Fetching (`get_toonami_shows` method)**:
    -   Uses the Wikipedia API (`action=parse`) to get the HTML content of the "List of programs broadcast by [network]" page.
    -   Parses the HTML using `BeautifulSoup` to find tables with class `wikitable`.
    -   Iterates through these tables, identifying relevant columns like 'title' (or 'program') and 'year(s) aired' (or 'airdate').
    -   Extracts show titles and their airing years, cleaning the data (removing footnotes, normalizing years).
    -   Returns a Pandas DataFrame with 'Title' and 'Year' columns, with duplicates dropped.
-   **Inputs**: `config.network` (e.g., "Toonami").
-   **Outputs**: Pandas DataFrame of Toonami shows and their airing years.

**`ToonamiChecker` Class**:
-   **Purpose**: Compares the fetched list of Toonami shows with video files in a user-specified anime folder, identifies matches, and saves the results to a SQLite database.
-   **Initialization**: Takes the path to the user's `anime_folder`.
-   **Video File Scanning (`get_video_files` method)**:
    -   Walks through the `anime_folder` (and subfolders) to find video files (e.g., .mkv, .mp4).
    -   Uses regex (`r'^(.*?)(?: - S\d{1,2}E\d{1,2})'`) to extract the show title from filenames.
    -   Returns a dictionary mapping show titles to a list of their corresponding episode file paths (relative to `anime_folder`).
-   **Show Name Normalization (`normalize_and_map` method)**:
    -   Converts show names to lowercase.
    -   Removes special characters and handles underscores using `unidecode` and regex.
    -   Applies custom name mappings defined in `config.show_name_mapping` to handle variations or alternative titles (e.g., "fmab" to "fullmetal alchemist brotherhood").
-   **Comparison (`compare_shows` method)**:
    -   Fetches Toonami shows using `ToonamiShowsFetcher`.
    -   Gets local video files using `get_video_files`.
    -   Normalizes both the Wikipedia show titles and the local file show titles using `normalize_and_map`.
    -   Compares the normalized lists to find matches.
    -   For matched shows, it creates a dictionary `toonami_episodes` mapping `(show_title, episode_filename)` to the full, normalized file path of the episode.
-   **Database Saving**:
    -   `save_episodes_to_spreadsheet` (method name is a misnomer, saves to DB): Saves the `toonami_episodes` (Title, Episode filename, Full_File_Path) to the `Toonami_Episodes` table in the SQLite database (`config.network.db`). Handles existing data by appending and removing duplicates.
    -   `save_show_names_to_spreadsheet` (method name is a misnomer, saves to DB): Saves unique matched show titles to the `Toonami_Shows` table. Handles existing data similarly.
-   **User Interaction Flow (`prepare_episode_data`, `process_selected_shows` methods)**:
    -   `prepare_episode_data`: Calls `compare_shows` and returns unique show names found locally that were on Toonami, along with the full `toonami_episodes` dictionary. This allows the GUI (`FrontEndLogic`) to present a list of shows for the user to select/deselect.
    -   `process_selected_shows`: Takes the user's selection of shows and the `toonami_episodes` data, filters the episodes to only include selected shows, and then saves this filtered data to the database tables.
-   **Inputs**:
    -   `anime_folder` (path to user's anime collection).
    -   `config.network`, `config.show_name_mapping`.
    -   User selection of shows (via `FrontEndLogic`).
-   **Outputs**:
    -   Populates/updates `Toonami_Episodes` and `Toonami_Shows` tables in the SQLite database (`[config.network].db`).

**Significance**: This tool is crucial for identifying relevant content for the Toonami channel, ensuring that only shows that actually aired on  the configured network (eg. Toonami) and are present in the user's library, are considered for the lineup. The database tables it creates are used by subsequent tools.

---

## Lineup Generation Components

### LineupPrep
**File**: `ToonamiTools/lineupprep.py`
**Class**: `MediaProcessor`
**Purpose**: Processes bump video files from a specified folder, extracts metadata (show names, placements, versions, colors) based on their filenames, and categorizes them into "nice" (matching known shows and patterns) and "naughty" (not matching) lists. This structured data is saved to a database for use in lineup creation.

**Key Features & Process**:
-   **Initialization**:
    -   Takes a `bump_folder` path.
    -   Loads keywords, show name mappings (`show_name_mapping`, `show_name_mapping_2`, `show_name_mapping_3`), and colors from `config.py`.
-   **Filename Parsing Logic**:
    -   **Keyword Counting (`count_keywords` method)**: Determines the type of bump (single, double, triple show involvement) based on keywords like "back", "to ads", "generic", "intro", "next", "from", "later" in the filename. Returns 1 for singles, 2 for "from" bumps, 3 for "later" bumps, 0 for generic/robot bumps.
    -   **Show Name Transformation (`_apply_show_name_mapping`, `_clean_show_name` methods)**:
        -   Applies multiple levels of show name mappings from `config` to the filename.
        -   Cleans show names by removing special characters and normalizing spaces.
    -   **Dynamic Regex Generation (`generate_dynamic_regex` method)**: Creates regex patterns based on the `count` from `count_keywords` and a list of known `shows` (retrieved from the `Toonami_Shows` database table).
        -   `count == 1` (Single show bumps): e.g., `Toonami [Version] [ShowName1] [PlacementKeyword] [AdVersion?] [Color?]`
        -   `count == 2` (Double show bumps, "from"): e.g., `Toonami [Version] [ShowName1] [PlacementKeyword] [ShowName2] [AdVersion?] [Color?]`
        -   `count >= 3` (Triple show bumps, "later"): e.g., `Toonami [Version] [Placement1?] [ShowName1] [Placement2] [ShowName2] [Placement3] [ShowName3] [AdVersion?] [Color?]`
        -   `count == 0` (Generic/Robot bumps): e.g., `Toonami [Version] [robot|clyde] [AdVersion?]`
    -   **Data Extraction (`_extract_data_from_pattern` method)**: Applies the generated regex to the (transformed) filename to extract named groups like `TOONAMI_VERSION`, `SHOW_NAME_1`, `PLACEMENT_2`, `SHOW_NAME_2`, `AD_VERSION`, `COLOR`, etc.
-   **File Processing (`_process_data_patterns` method)**:
    -   Retrieves all media files (mkv, mp4) from the `bump_folder`.
    -   For each file, cleans the filename (removes extension, replaces underscores with spaces).
    -   Calls `_extract_data_from_pattern` to get metadata.
    -   Normalizes extracted show names (e.g., `SHOW_NAME_1`) using the lowercase version of the combined mappings.
    -   **Status Setting (`_set_status` method)**:
        -   Sets status to 'nice' if extracted show names are found in the list of known `shows` (from `Toonami_Shows` table) or if the bump is a recognized generic bump (from `config.genric_bumps`).
        -   Otherwise, sets status to 'naughty'.
    -   Appends processed data to either a `new_df` (for matches) or `no_match_df`.
-   **Database Interaction (`run`, `_save_to_sql` methods)**:
    -   Connects to the SQLite database (`[config.network].db`).
    -   Reads the `Toonami_Shows` table to get the list of valid show titles (normalized).
    -   Saves the processed bump data into several tables:
        -   `nice_list`: Bumps with 'nice' status.
        -   `naughty_list`: Bumps with 'naughty' status.
        -   `no_match`: Files for which no pattern was matched.
        -   `lineup_prep_out`: A subset of `nice_list` (dropping `ORIGINAL_FILE_PATH` and `Status`), which serves as the primary input for `ToonamiEncoder`.
    -   Handles existing tables by appending new data and removing duplicates.
-   **Inputs**:
    -   `bump_folder` (path to bump files).
    -   `config.py` (keywords, show_name_mappings, colors, generic_bumps, network name).
    -   `Toonami_Shows` table from the database.
-   **Outputs**:
    -   Populates/updates `nice_list`, `naughty_list`, `no_match`, and `lineup_prep_out` tables in the SQLite database.

**Significance**: This tool is critical for structuring raw bump files into a usable format. It standardizes naming and categorizes bumps, making it possible for subsequent tools like `ToonamiEncoder` and `ShowScheduler` (Merger) to build coherent Toonami lineups. The `lineup_prep_out` table is the key handoff to the next stage of encoding.

### ToonamiEncoder
**File**: `ToonamiTools/ToonamiEncoder.py`
**Purpose**: Processes bump data from the `lineup_prep_out` database table to create standardized codes for each bump. These codes are used for efficient library management and bump selection during lineup generation by the `Merger (ShowScheduler)`.

**Key Features & Process**:
- **Input**: Reads data from the `lineup_prep_out` table (created by `LineupPrep`). This table is expected to have columns like `PLACEMENT_1`, `PLACEMENT_2`, `PLACEMENT_3`, `SHOW_NAME_1`, `SHOW_NAME_2`, `SHOW_NAME_3`, `TOONAMI_VERSION`, `AD_VERSION`, and `COLOR`.
- **Show Abbreviation (`get_abbr` method)**:
    - For each unique show name encountered (e.g., in `SHOW_NAME_1`), it generates a 3-letter uppercase abbreviation.
        - If the name has multiple words, it uses the first two letters of the first word and the first letter of the second word (e.g., "Dragon Ball Z" -> "DRB").
        - If one word, it uses the first three letters (e.g., "Naruto" -> "NAR").
    - If an abbreviation already exists, it appends a number to ensure uniqueness (e.g., "DRB1", "DRB2").
    - These abbreviations are stored in an internal dictionary (`self.codes`) mapping full names to abbreviations, and this dictionary is later saved to the `codes` table in the database.
    - The method returns a string like `S1:DRB` (for Show 1: Dragon Ball Z) or `P1:NXT` (for Placement 1: Next).
- **Code Creation (`create_code` method)**:
    - For each row (bump) in the input DataFrame:
        - It generates placement codes (e.g., `P1:BCK` for "Back") and show codes (e.g., `S1:GND` for "Gundam") using `get_abbr`.
        - It constructs a composite code string by concatenating:
            - Toonami Version (e.g., `V2.0` becomes `V2`)
            - Placement and Show codes in order (e.g., `P1:BCK-S1:GND`)
            - Ad Version (e.g., `-AV1` if present)
            - Color (e.g., `-B` if color is "Blue", taking the first letter)
            - Number of Shows (e.g., `-NS1` for a single show bump, `-NS2` for double, `-NS3` for triple).
    - **Example Code**: `V2-P1:BCK-S1:GND-P2:NXT-S2:BLE-AV1-R-NS2` (Toonami Version 2.0, Back Gundam, Next Bleach, Ad Version 1, Red, 2 Shows)
- **DataFrame Encoding (`encode_dataframe` method)**:
    - Applies `create_code` to each row to generate a `Code` column.
    - Extracts `sort_ver` (e.g., `2` from `V2`) and `sort_ns` (e.g., `1` from `NS1`) from the `Code` for sorting purposes.
    - Sorts the DataFrame by `sort_ver` then `sort_ns`.
- **Database Output**:
    - `codes` table: Stores the mapping of full show names (and placement names) to their generated abbreviations (e.g., "Dragon Ball Z" | "DRB").
    - `main_data` table: Contains the original bump data along with the new `Code` column (and `sort_ver`, `sort_ns` dropped).
    - `singles_data` table: A subset of `main_data` containing only single-show bumps (`Code` contains `-NS1`).
    - `multibumps_v8_data` table: A subset of `main_data` containing multi-show bumps (`Code` contains `-NS2` or `-NS3`). (Note: the 'v8' seems hardcoded here in the `save_encoded_dataframes` method, which might be an oversight if it's meant to be dynamic).
    - `multibumps_vX_data` tables: For each unique Toonami version (`sort_ver`) found in the multibumps, a separate table is created (e.g., `multibumps_v2_data`, `multibumps_v9_data`).
- **Overall Workflow (`encode_and_save` method)**:
    1. Reads `lineup_prep_out`.
    2. Encodes the DataFrame.
    3. Saves the various derived DataFrames (`main_data`, `singles_data`, `multibumps_vX_data`) to the database.
    4. Saves the `codes` mapping table to the database.

**Significance**:
- The `ToonamiEncoder` standardizes bump representation, making it easier for the `Merger (ShowScheduler)` to identify and sequence bumps based on the shows they feature and their type (single, double, triple, version, etc.).
- The `codes` table is crucial for the `Merger` to decode these abbreviations back to full show names when processing the lineup.


### UncutEncoder
**File**: `ToonamiTools/UncutEncoder.py`
**Class**: `UncutEncoder`
**Purpose**: Prepares data specifically for an "uncut" Toonami lineup. It identifies episode files from `toonami_episodes`, assigns them unique `BLOCK_ID`s, and strategically inserts corresponding intro/generic bumps (from `singles_data`) before each show block. This process creates the `uncut_encoded_data` table, which lists all files (episodes and their selected intro bumps) for a continuous uncut viewing experience. This table serves as a comprehensive list of content confirmed for this type of lineup.

**Key Features & Process**:
-   **Initialization**:
    -   Connects to the SQLite database (`[config.network].db`).
-   **Bump Data Loading (`load_bumps_data` method)**:
    -   Reads bump data from the `singles_data` table (created by `ToonamiEncoder`).
    -   Applies show name mappings (from `config.show_name_mapping`, `_2`, `_3`) to the `SHOW_NAME_1` column in the loaded bumps data.
    -   Creates a `default_bump_cycle` by selecting generic bumps (e.g., containing 'clydes' or 'robot' in `SHOW_NAME_1`) to be used as a fallback if specific intro bumps are not found.
-   **Episode File Discovery (`find_files` method)**:
    -   Queries the `toonami_episodes` table (created by `ToonamiChecker`) for `Full_File_Path` of episodes.
    -   Parses each file path to extract show name, season number, and episode number using regex (`r"/([^/]+)/Season (\d+)/[^/]+ - S(\d+)E(\d+)"`).
    -   Sorts these episodes by show name, season, and episode number to ensure chronological order.
    -   For each episode, creates a `BLOCK_ID` in the format `SHOW_NAME_SXXEYY` (e.g., `FULLMETAL_ALCHEMIST_S01E01`). Show names are uppercased, spaces replaced with underscores, and non-alphanumeric characters removed.
    -   Populates `self.file_paths` (list of full episode paths) and `self.block_ids` (list of corresponding block IDs).
-   **Intro Bump Insertion (`insert_intro_bumps` method)**:
    -   Iterates through the sorted `file_paths` and `block_ids` (in reverse to maintain correct insertion indices).
    -   For each episode (identified by its `block_id`):
        -   Extracts and normalizes the show name from the `block_id`.
        -   Applies show name mappings.
        -   Searches `self.bumps_df` (loaded `singles_data`) for:
            1.  Specific "Intro" bumps for that show (where `PLACEMENT_2` contains 'Intro').
            2.  If not found, specific "Generic" bumps for that show (where `PLACEMENT_2` contains 'Generic').
            3.  If neither is found, uses the next bump from `self.default_bump_cycle`.
        -   Uses `itertools.cycle` for each show's intro/generic bumps (`self.intro_bump_cycle`, `self.generic_bump_cycle`) to rotate through available bumps if multiple exist.
        -   Inserts the chosen intro bump's `FULL_FILE_PATH` and the episode's `BLOCK_ID` at the beginning of the `self.file_paths` and `self.block_ids` lists for that show block.
-   **Database Output (`create_table` method)**:
    -   Creates a Pandas DataFrame from the final `self.file_paths` and `self.block_ids`.
    -   Saves this DataFrame to the `uncut_encoded_data` table in the database, replacing it if it exists. This table contains `FULL_FILE_PATH` (for both bumps and episodes) and `BLOCK_ID` (repeated for all files within the same block).
-   **Overall Workflow (`run` method)**:
    1.  `load_bumps_data()`
    2.  `find_files()`
    3.  `insert_intro_bumps()`
    4.  `create_table()`
-   **Inputs**:
    -   `singles_data` table (for bump information).
    -   `toonami_episodes` table (for episode file paths).
    -   `config.py` (show name mappings, network name).
-   **Outputs**:
    -   `uncut_encoded_data` table in the SQLite database. This table represents a sequence of files (bumps and episodes) ready for an uncut Toonami lineup.

**Significance**: `UncutEncoder` is vital for users wanting a Toonami experience that preserves full episodes while including thematic Toonami intros. The `uncut_encoded_data` table it produces contains a complete list of *all files (episodes and their bumps)* that will form the uncut lineup. This table is then used by `EpisodeFilter` to specifically isolate the *episode files* from this lineup, ensuring that only these actual content episodes that have associated bumps (and not the bumps) are passed to `CommercialBreaker` for processing. The `BLOCK_ID` system ensures that shows are grouped correctly with their intros. This is important as shows that do not have bumps associated with them will not be included in the final lineup.

### Multilineup
**File**: `ToonamiTools/Multilineup.py`
**Class**: `Multilineup`
**Purpose**: Re-orders multi-show bump tables (e.g., `multibumps_vX_data` created by `ToonamiEncoder`) to create a more logical and flowing sequence of bumps. The goal is to ensure that the "Later" show of one bump becomes the "Now" or "Next" show of the subsequent bump, creating a continuous chain.

**Key Features & Process**:
-   **Initialization**:
    -   Connects to the SQLite database (`[config.network].db`).
    -   Initializes `used_rows` (a set to track already processed bumps) and `recent_shows` (a list to de-prioritize recently featured shows).
-   **Bump Selection Logic**:
    -   **Weighted Selection (`weighted_selection` method)**: Selects a bump from a given DataFrame, applying lower weights to bumps featuring shows that are in `self.recent_shows` to encourage variety.
    -   **Unused Bumps (`unused_bumps` method)**: Retrieves bumps from a specified table that haven't been used yet (i.e., their index is not in `self.used_rows`).
    -   **Optimal First Bump (`find_optimal_first_bump` method)**: Tries to select an ideal starting bump for a sequence. It prioritizes bumps where:
        1.  `SHOW_NAME_1` is not another bump's `SHOW_NAME_3`, AND `SHOW_NAME_3` *is* another bump's `SHOW_NAME_1` (good starting point).
        2.  Or, a variation involving counts of `SHOW_NAME_1` vs `SHOW_NAME_3` occurrences.
        3.  Or, `SHOW_NAME_1` is the `SHOW_NAME_3` of multiple other bumps.
        4.  If none of the above, it picks the first available bump.
    -   **Next Row Selection (`get_next_row` method)**: This is the core logic for chaining bumps.
        -   If `self.next_show_name` is set (from the previous bump's "Later" or "Next" show):
            -   It tries to find a bump where `PLACEMENT_2` is 'next' and `SHOW_NAME_1` matches `self.next_show_name`. Among these, it prioritizes bumps whose `SHOW_NAME_3` (the "Later" show) has fewer upcoming "Now" bumps available, aiming to use up rarer continuations first.
            -   If no such 'next' bump is found, it looks for 'next from' or 'from' bumps where `SHOW_NAME_2` matches `self.next_show_name`.
        -   If no specific `next_show_name` is set or no suitable continuation is found, it falls back to a weighted random selection from all unused bumps.
        -   Once a row is selected, its index is added to `self.used_rows`.
        -   `self.next_show_name` is updated based on the selected bump's `SHOW_NAME_3` (if `PLACEMENT_2` is 'next') or `SHOW_NAME_1`.
-   **Table Reordering (`reorder_table`, `reorder_all_tables` methods)**:
    -   `reorder_table`:
        -   Takes a `table_name` (e.g., `multibumps_v2_data`).
        -   Creates a new table with `_reordered` suffix (e.g., `multibumps_v2_data_reordered`).
        -   Selects an optimal first bump using `find_optimal_first_bump`.
        -   Writes this first bump to the new reordered table.
        -   Enters a loop:
            -   Gets the next bump using `get_next_row`.
            -   Writes it to the reordered table.
            -   Updates `self.recent_shows`.
        -   Continues until all bumps from the original table are used.
    -   `reorder_all_tables`: Iterates through potential table names (`multibumps_v0_data` to `multibumps_v9_data`) and calls `reorder_table` for each one that exists.
-   **Inputs**:
    -   Various `multibumps_vX_data` tables from the database (created by `ToonamiEncoder`).
    -   `config.network` (for database name).
-   **Outputs**:
    -   Creates new tables in the database with `_reordered` suffix (e.g., `multibumps_v2_data_reordered`), containing the bumps in a more logical sequence.

**Significance**: `Multilineup` is crucial for creating engaging Toonami blocks where the announcements flow logically from one multi-show bump to the next. The reordered tables it produces are used by the `ShowScheduler` (Merger) to construct the final channel lineup, ensuring that transitions between shows are smooth and make narrative sense based on the bump announcements.

### BlockIDCreator
**File**: `ToonamiTools/lineupencode.py` (Class: `BlockIDCreator`)
**Purpose**: Processes data from the `commercial_injector` table (which contains paths to cut episode parts and associated metadata), generates a standardized `BLOCK_ID` for each entry, and saves the result to the `commercial_injector_final` table. The `BLOCK_ID` groups all parts of the same original episode, which is crucial for subsequent lineup scheduling.

**Key Features & Process**:
-   **Initialization (`__init__` method)**:
    -   Connects to the SQLite database (`[config.network].db`).
-   **Data Loading (`load_data` method)**:
    -   Reads all data from the `commercial_injector` table into a Pandas DataFrame. This table is expected to contain `FULL_FILE_PATH` for cut episode parts.
-   **Block ID Generation (`create_block_id` static method)**:
    -   Takes a `FULL_FILE_PATH` as input.
    -   Normalizes the path and splits it into components.
    -   Extracts the series name (assumed to be the third-to-last component of the path, e.g., the show's folder name).
    -   Uses a regex (`r'S\d{2}E\d{2}'`) to find a season and episode pattern (e.g., "S01E01") in the filename (last path component).
    -   If the pattern is found, it constructs a `block_id` string: `SERIES_NAME-SXXEYY`.
    -   This `block_id` is then normalized by replacing non-alphanumeric characters with underscores and converting to uppercase (e.g., `FULLMETAL_ALCHEMIST_BROTHERHOOD-S01E01`).
    -   Returns `None` if the season/episode pattern is not found in the filename.
-   **Block ID Assignment (`assign_block_ids` method)**:
    -   Applies the `create_block_id` method to the `FULL_FILE_PATH` column of the DataFrame to create a new `BLOCK_ID` column.
    -   Iterates through the DataFrame to handle any rows where `BLOCK_ID` might be `None` (due to `create_block_id` not finding the pattern):
        -   If a `BLOCK_ID` is `None`, it attempts to fill it with the `BLOCK_ID` from the *next* row.
        -   If the next row is also `None` or doesn't exist, it uses the `self.last_block_id` (the last successfully generated/propagated `BLOCK_ID` from a previous row). This ensures that all parts related to an episode (even if some filenames are non-standard) get grouped under the same `BLOCK_ID` as long as at least one part's filename allows ID generation.
-   **Data Saving (`save_data` method)**:
    -   Drops the `SHOW_NAME_1` and `Season and Episode` columns from the DataFrame (as this information is now encapsulated or made redundant by the `BLOCK_ID` and the structured path).
    -   Saves the modified DataFrame (now including the `BLOCK_ID` column and with dropped columns) to a new table named `commercial_injector_final` in the database, replacing it if it already exists.
-   **Overall Workflow (`run` method)**:
    1.  `load_data()`
    2.  `assign_block_ids()`
    3.  `save_data()`

**Inputs**:
-   `commercial_injector` table from the SQLite database (`[config.network].db`). This table should contain `FULL_FILE_PATH` for cut episode segments.
-   File path structure that generally includes `ShowName/SeasonXX/ShowName - SXXEXX - PartX.ext`.

**Outputs**:
-   `commercial_injector_final` table in the SQLite database. This table includes the original data from `commercial_injector` plus a `BLOCK_ID` column, and excludes the `SHOW_NAME_1` and `Season and Episode` columns.

**Significance**: Consistent `BLOCK_ID`s are essential for the `ShowScheduler` (Merger) to correctly group all parts of a cut episode (e.g., intro, content part 1, content part 2, outro) and schedule them together as a single logical "episode block." This tool ensures that even if filenames are slightly inconsistent, related parts are correctly associated, which is crucial for building a coherent lineup from pre-cut content. It prepares the data specifically for the "cut content" path of the `ShowScheduler`.

### Merger (Show Scheduler)
**File**: `ToonamiTools/Merger.py`
**Purpose**: Creates cohesive lineups and manages show sequencing by merging bump lists with episode blocks.

**Key Functionality & Configuration**:
- **Dual Functionality**:
    1.  **Initial Run**: Creates a base lineup structure from a bump list (e.g., `multibumps_v9_data_reordered` from `config.TOONAMI_CONFIG[version]["merger_bump_list"]`) and an input episode data table (e.g., `commercial_injector_final` or `uncut_encoded_data` from `config.TOONAMI_CONFIG[version]["encoder_in"]`).
    2.  **Second Run**: Can be used to integrate commercial-cut content or refine lineups.
- **Input Tables**:
    - `encoder_table`: Contains bump data with encoded show information (e.g., `multibumps_v9_data_reordered`). This table has a `Code` column that indicates the shows involved in a bump (e.g., `-S1:DBZ-S2:GITS-NS3` for a triple bump).
    - `commercial_table`: Contains episode data, including `FULL_FILE_PATH` and `BLOCK_ID` (e.g., `commercial_injector_final` for cut content, `uncut_encoded_data` for uncut).
- **Output Table**: Saves the generated lineup to a specified table (e.g., `lineup_v9` from `config.TOONAMI_CONFIG[version]["merger_out"]`).
- **Show Name Normalization**: Uses `config.show_name_mapping` to standardize show names.
- **Episode Block Management**:
    - `reuse_episode_blocks` (boolean, constructor arg): If `True`, episode blocks for a show are reused from the beginning once exhausted. If `False`, the show is skipped once all its blocks are used.
    - `continue_from_last_used_episode_block` (boolean, constructor arg): If `True`, the scheduler attempts to continue from the last used episode block for each show (persisted in `last_used_episode_block` table). Otherwise, it resets tracking.
    - `shows_with_no_more_blocks` (internal set): Tracks shows that have run out of blocks when `reuse_episode_blocks` is `False`.
- **Uncut Mode**:
    - `uncut` (boolean, constructor arg, also in `config.TOONAMI_CONFIG[version]["uncut"]`): If `True`, schedules for uncut content. This also influences `apply_ns3_logic`.

**Core Scheduling Logic (`generate_schedule` method)**:
1.  Iterates through the `encoder_df` (bump list).
2.  For each bump (`row`), extracts the shows involved (`shows` list from `row["Code"]`) and the bump code itself (`code_value`).
3.  **NS2/NS3 Bump Handling** (`apply_ns3_logic` - enabled if NS2 bumps exist and not in `uncut` mode):
    -   **NS2 Bumps** (e.g., `Code` contains `-NS2`): These are typically "Next Show" transitions involving two shows (Show A, then Show B).
        -   The scheduler ensures continuity: if the `last_show_name` from the previous segment isn't Show B, it first inserts an episode block of Show B.
        -   Then, the NS2 bump file itself is added.
        -   Finally, an episode block of Show A is added (often with `delete_intro=True` for the first part of Show A).
    -   **NS3 Bumps** (e.g., `Code` contains `-NS3`): These are typically "Now Show A, Next Show B, Later Show C" transitions.
        -   `_detect_ns2_ns3_chain`: If an NS3 bump for Show A immediately follows an NS2 bump that also featured Show A, the first show (Show A) in the NS3 list is skipped to avoid repetition.
        -   The NS3 bump file is added.
        -   Episode blocks for the shows in the NS3 list (potentially adjusted by the chain detection or if the *next* bump is also an NS3 for the same tail show) are inserted sequentially.
    -   `_attempt_interweave`: Adds a blank row for spacing if the next bump starts with a different show and there's no direct NS2/NS3 handoff.
4.  **Episode Block Insertion (`_insert_episode_block`)**:
    -   `get_next_episode_block(show)`: Retrieves the next available `BLOCK_ID` for the given `show` from `commercial_injector_df`.
        -   Considers `last_used_episode_block` if `continue_from_last_used_episode_block` is true.
        -   Handles `reuse_episode_blocks` or adds to `shows_with_no_more_blocks`.
    -   The files corresponding to the selected `BLOCK_ID` are fetched from `commercial_injector_df` and appended to the `final_df`.
    -   `delete_intro`: If true (usually after a transition bump), the first file of the block (assumed to be an intro) is skipped.
5.  **NS3 Special Index Adjustment (`adjust_final_df_based_on_ns3_indices`)**:
    -   If `apply_ns3_logic` is true, `get_ns3_special_indices` finds NS3 bumps that immediately follow an NS2 bump for the *same show*.
    -   A simplistic reordering attempts to swap the NS3 bump with the content two rows above it, then removes the original NS3 bump row. This aims to fix specific transition flow issues.
6.  **Adding Unused Shows (`add_unused_shows_to_schedule`)**:
    -   If `continue_from_last_used_episode_block` is true, this logic attempts to insert blocks from shows not yet used in the current schedule.
    -   `locate_lines_of_fourth_unique_block_id`: Identifies "anchor points" in the schedule (just before the fourth unique block ID within an NS3 segment) to insert these unused shows, aiming for variety.

**Anti-Repetition & Continuity**:
- The core logic of processing bumps sequentially and using `last_show_name` helps maintain continuity.
- NS2/NS3 handling is specifically designed for complex multi-show transitions.
- `reuse_episode_blocks` and `continue_from_last_used_episode_block` manage how shows are revisited or continued across multiple schedule generations.

**Example Simplified Flow for a Triple Bump ("Now ShowA, Next ShowB, Later ShowC" - an NS3 type)**:
1.  NS3 Bump File (e.g., `NOW_A_NEXT_B_LATER_C.mp4`) is added to schedule.
2.  Episode Block for ShowA is added.
3.  Episode Block for ShowB is added.
4.  Episode Block for ShowC is added.
The next bump processed would ideally start with "Now ShowC...".

**Database Interaction**:
- Reads from: `encoder_table`, `commercial_table`, `codes`, `last_used_episode_block` (optional).
- Writes to: `save_table`, `last_used_episode_block` (optional).
All table names are typically sourced from `config.TOONAMI_CONFIG` based on the selected Toonami version.

### EpisodeFilter
**File**: `ToonamiTools/EpisodeFilter.py`
**Purpose**: Processes a lineup table (e.g., `uncut_encoded_data` from `UncutEncoder`, or a `lineup_vX` table from `ShowScheduler`) which contains a mix of episode file paths and bump file paths. Its primary function is to **isolate the actual episode files** by filtering out bump files. Bump files are identified by checking if their `FULL_FILE_PATH` contains the `config.network` name (e.g., "Toonami"), as bump filenames conventionally include the network name. The resulting list of episode files is then used for further processing, typically by `CommercialBreaker` or for file relocation.

**Operating Modes** (controlled by the `prepopulate` flag in the `run` method):
- **Filter and Move** (`prepopulate=False`): After filtering out bumps and identifying episode files, it physically relocates the entire parent *show directories* of these episode files to a specified target directory (e.g., `toonami_filtered`).
- **Prepopulate Selection** (`prepopulate=True`): After filtering out bumps, it collects and returns a list of unique *file paths* for the identified episode files without moving them. This list is typically used as direct input for `CommercialBreaker`.

**Filtering Logic**:
- An input table (e.g., `uncut_encoded_data` or `lineup_v8_uncut`) is read from the database. This table represents a lineup that includes both episode files and bump files.
- The core filter `~df['FULL_FILE_PATH'].str.lower().str.contains(config.network.lower(), na=False)` is applied:
    - Bump files (e.g., "Toonami 3.0 Fullmetal Alchemist To Ads.mp4") will match `config.network.lower()` and thus be *excluded* by the `~` (NOT operator).
    - Episode files (e.g., "/path/to/Fullmetal Alchemist/Season 1/Fullmetal Alchemist - S01E01.mkv") typically will *not* match `config.network.lower()` in their path and thus be *included*.
- The `Code` and `BLOCK_ID` columns are dropped from the filtered data, as the focus is on the episode file paths themselves.
- The result (a list of episode file paths, or their parent directories for moving) is either written to a new table (e.g., `lineup_v8_uncut_filtered`), used to move files, or returned as a list of paths.

**Assumptions**:
- The input table to `EpisodeFilter` contains `FULL_FILE_PATH` for both episodes and bumps.
- Bump filenames consistently include the network name, allowing them to be filtered out.

**Significance**: `EpisodeFilter` plays a crucial role in optimizing the media processing pipeline by ensuring that the time-intensive `CommercialBreaker` tool only processes actual episode content that will be used in the final lineup. By intelligently filtering out bumps from a pre-defined lineup (which already reflects show/bump availability), it prevents unnecessary processing of bump files and episode files that do not have associated bumps, which do not require commercial detection. This targeted approach significantly speeds up the overall workflow, especially when dealing with large media libraries and numerous bumps. In "Filter and Move" mode, it also helps organize the relevant episode source files into a dedicated processing or staging area.

---

## Timestamp and Detection Components

### GetTimestampPlex
**File**: `ToonamiTools/GetTimestampPlex.py`
**Class**: `GetPlexTimestamps`
**Purpose**: Fetches "skip intro" marker timestamps from a Plex server for episodes in a specified library. These timestamps are saved to a text file and can be used by `CommercialBreaker` as a fallback or primary method for identifying intro segments, especially in "Low Power Mode" or "Fast Mode".

**Key Features & Process**:
-   **Initialization**:
    -   Takes Plex server URL (`plex_url`), Plex token (`plex_token`), the name of the Plex library to scan (`library_name`), and a directory to save the output (`save_dir`).
    -   Connects to the Plex server using `plexapi.server.PlexServer`.
-   **Timestamp Extraction (`run` method)**:
    -   Retrieves all media items (shows/movies) from the specified Plex library section.
    -   For each media item, it iterates through its episodes.
    -   For each episode, it fetches the item's full metadata using `plex.fetchItem(f'/library/metadata/{episode.ratingKey}')`.
    -   Checks if the item has `markers` (Plex's feature for things like intros, credits).
    -   If 'intro' markers exist:
        -   Extracts the `start` and `end` time offsets (in milliseconds).
        -   Converts these to seconds.
        -   Retrieves the episode's file path (`item.media[0].parts[0].file`).
        -   Extracts the filename from the path.
        -   Writes a line to `intros.txt` (in the `save_dir`) in the format: `filename.ext = end_time_in_seconds`. (The commented-out line suggests it previously might have saved start and end times).
-   **Inputs**:
    -   Plex server URL and token.
    -   Name of the Plex library containing anime.
    -   Output directory for the timestamp file.
-   **Outputs**:
    -   A text file named `intros.txt` in the `save_dir`. Each line contains an episode filename and the end timestamp of its intro in seconds (e.g., `MyShow - S01E01.mkv = 90.500`).
-   **Error Handling**: Basic print statements for progress and loaded items. Does not explicitly show robust error handling for network or Plex API issues in the provided snippet.

**Significance**:
-   Provides an alternative or supplementary method for `CommercialBreaker` to identify intro segments without relying solely on black frame/silence detection.
-   Can be much faster than visual/audio analysis if Plex has already marked intros.
-   The output `intros.txt` is read by `CommercialBreakerLogic` (specifically `TimestampManager`) to create cut points.

## Commercial Processing Components

### CommercialBreaker System Overview
**Location**: `ComBreak/` directory
**Purpose**: Complete commercial break detection and processing system

The CommercialBreaker system is composed of several specialized components working together to detect commercial break points in videos and optionally cut files at those points.

#### Core Architecture

- **CommercialBreakerLogic.py** (`CommercialBreakerLogic`): Main orchestrator that coordinates the entire detection and cutting process, called by all UIs.
- **CommercialBreakerGUI.py** (`CommercialBreakerGUI`): Main GUI for ComBreak, handles user input and mode selection.
- **EnhancedInputHandler.py** (`EnhancedInputHandler`): Handles both folder and file selection modes, consolidates mixed inputs.
- **VideoLoader.py** (`VideoLoader`): Manages video file discovery and filtering, provides frame-by-frame access.
- **VideoFileManager.py** (`VideoFilesManager`): Tracks processing state and file organization, singleton pattern.

#### Detection Phase Components

- **ChapterExtractor.py** (`ChapterExtractor`): Examines video metadata for embedded chapter markers (highest priority, fastest, most reliable).
- **SilentBlackFrameDetector.py** (`SilentBlackFrameDetector`): Orchestrates complex detection process using:
  - **SilenceDetector**: Identifies silent periods using FFmpeg
  - **VideoPreprocessor**: Downscales only silent segments
  - **BlackFrameAnalyzer**: Analyzes frames for darkness
- **TimestampManager.py** (`TimestampManager`): Handles timestamp file operations, two-stage filtering, Plex timestamp integration
- **VirtualCut.py** (`VirtualCut`): Used only in Cutless Mode to create virtual references instead of physical cuts, outputting to the `commercial_injector_prep` table.


#### Detection Method Priority & Mode Exclusivity

- **Low Power Mode**: Chapter Extraction → Plex Timestamps (from plex_timestamps.txt)
- **Fast Mode**: Chapter Extraction → Plex Timestamps → Silent Black Frame Detection
- **Normal Mode**: Chapter Extraction → Silent Black Frame Detection → Plex Timestamps (fallback)

**Note:** Fast Mode and Low Power Mode are mutually exclusive (cannot be enabled together). Destructive Mode and Cutless Mode are also mutually exclusive. This is enforced in the GUI and logic.

#### Cutting Phase Components

- **VideoCutter.py** (`VideoCutter`): Handles the actual file processing
  - **Traditional Mode**: Physically cuts videos at detected timestamps, creates multiple files per episode (Part 1, Part 2, etc.)
  - **Cutless Mode**: Uses `VirtualCut` to create virtual references, no physical files are created, only database entries

#### Progress Tracking System

- **ProgressManager**: Tracks progress across three distinct processing phases (silence detection, downscaling, frame analysis) with accurate pre-calculation of total steps.

#### Error Handling

- Resilient design: Process continues even if individual files fail, progress tracking remains accurate, resource cleanup is guaranteed.

---

**For a full technical breakdown, see `docs/ComBreakDocs.md` in the repository.**

## Content Enhancement Components

### Bonus! (ExtraBumpsToSheet)
**File**: `ToonamiTools/extrabumpstosheet.py`
**Class**: `FileProcessor`
**Purpose**: Integrates additional video files (referred to as "special bumps" or "bonus" content) from a specified input directory into existing lineup tables in the database. These are inserted at random intervals.

**Key Features & Process**:
-   **Initialization**:
    -   Takes an `input_dir` (where the special bump/bonus video files are located).
    -   Connects to the SQLite database (`[config.network].db`).
    -   Retrieves a list of all table names in the database that match the pattern `lineup_v%` (e.g., `lineup_v2`, `lineup_v8_uncut`). These are the target lineup tables to which bonus content will be added.
-   **File Processing (`process_files` method)**:
    -   Iterates through each identified `lineup_name` (e.g., `lineup_v2`).
    -   Reads the corresponding lineup table from the database into a Pandas DataFrame (`df_input`).
    -   Walks through the `self.input_dir` to find all files and collects their full paths.
    -   Creates a new DataFrame (`df`) from these collected bonus file paths, with columns `FULL_FILE_PATH`, `Code` (empty string), and `BLOCK_ID` (empty string).
    -   Shuffles this `df` of bonus files randomly.
    -   **Insertion Logic**:
        -   Iterates through the shuffled bonus files.
        -   For each bonus file, it calculates an insertion position (`pos`) in the `df_input` (the original lineup). The position is incremented by a random integer between 3 and 7 from the previous insertion point. This ensures bonus content is spread out.
        -   If the calculated `pos` is within the bounds of `df_input`, the current bonus file (as a single-row DataFrame) is inserted at that position.
        -   The loop breaks if `pos` goes beyond the length of `df_input`.
    -   **Database Output**:
        -   The modified `df_input` (now containing the inserted bonus files) is saved back to the database under a new table name, which is the original `lineup_name` with `_bonus` appended (e.g., `lineup_v2_bonus`). The original table is replaced if the `_bonus` table already exists.
-   **Inputs**:
    -   `input_dir`: A folder containing video files to be used as bonus content.
    -   Existing `lineup_v%` tables in the SQLite database.
    -   `config.network` (for database name).
-   **Outputs**:
    -   Creates new tables in the database with `_bonus` suffix (e.g., `lineup_v2_bonus`), containing the original lineup data interspersed with the bonus content.

**Significance**: This tool allows for the dynamic enrichment of pre-generated Toonami lineups with additional content like special Toonami event bumps, music videos, or any other short video pieces the user wants to include, adding variety and customization to the final channel.

## Plex Management Components

### PlexSplitter
**File**: `ToonamiTools/plexautosplitter.py`
**Class**: `PlexAutoSplitter`
**Purpose**: Automates the "split apart" action in Plex for media items that Plex has incorrectly merged (i.e., a single library entry points to multiple distinct video files). This is crucial for ensuring each video part or episode is treated as a separate entity for accurate lineup generation and playback.

**Problem Solved**:
Plex's automatic matching can sometimes incorrectly merge multiple video files (e.g., parts of a multi-part episode, or different episodes that Plex thinks are the same) into a single item in the library. `PlexAutoSplitter` identifies these merged items and programmatically splits them.

**Key Features & Process**:
- **Initialization**:
    - Takes Plex URL, token, and a timeout value from `config.py`.
    - Initializes a `PlexServer` instance from the `plexapi.server` library.
    - Sets up a Selenium WebDriver (Chrome) with specific options (e.g., headless, disabling GPU, specific user agent).
- **Library Iteration**:
    - The main method `split_plex_items_in_library(library_name, series_title=None, season_number=None, episode_number=None)` iterates through a specified Plex library.
    - It can target an entire library, a specific series, a season within a series, or a particular episode.
- **Merged Item Identification (`check_and_split_item` method)**:
    - For each video item, it checks if `len(item.media)` > 1. If true, it indicates that Plex has associated multiple media files with this single library entry, meaning it's a merged item.
- **Splitting Action (`split_item` method)**:
    - If a merged item is found:
        1.  Constructs the Plex Web URL for the item's pre-play screen (e.g., `http://<plex_url>/web/index.html#!/server/<server_machine_id>/details?key=%2Flibrary%2Fmetadata%2F<item_rating_key>`).
        2.  Uses Selenium to navigate to this URL.
        3.  Locates and clicks the "more actions" button (ellipsis).
        4.  Locates and clicks the "Split Apart" option from the context menu.
        5.  Waits for a confirmation modal and clicks "Yes" (or "OK" - the exact text might vary and is handled by trying multiple XPath selectors).
        6.  Logs the action and waits for a short period for Plex to process the split.
- **Error Handling**:
    - Includes `try-except` blocks to catch `NoSuchElementException` (if UI elements are not found) and other general exceptions during the Selenium interactions.
    - Ensures the WebDriver quits properly using a `finally` block.
- **Configuration**:
    - Relies on `config.PLEX_URL`, `config.PLEX_TOKEN`, and `config.PLEX_TIMEOUT`.
    - `config.CHROME_DRIVER_PATH` specifies the path to the ChromeDriver executable.

**Technical Approach**:
- Combines `plexapi` for library navigation and item metadata retrieval.
- Uses `selenium` for web browser automation to perform UI actions (clicking buttons) that are not directly available via the Plex API. This is necessary because the "Split Apart" functionality is primarily a Plex Web UI feature.

**Usage**:
- Typically run after adding new media to Plex or if merged items are suspected.
- Can be invoked programmatically by other scripts or run manually.

**Dependencies**:
- `plexapi`
- `selenium`
- Google Chrome browser and a compatible ChromeDriver.

**Limitations**:
- Relies on the stability of Plex Web UI element selectors (XPaths). Changes in Plex's UI could break the splitting functionality.
- Requires a running Plex server and valid credentials.
- The process can be slow as it involves browser automation and page loads for each split action.

### PlexSplitRenamer
**File**: `ToonamiTools/RenameSplitPlex.py`
**Class**: `PlexLibraryUpdater`
**Purpose**: After items in a Plex library have been split (e.g., by `PlexAutoSplitter`), this tool renames them based on their underlying filenames. This is often necessary because splitting items in Plex might leave them with generic or identical titles, and this tool ensures their titles in Plex match the actual content.

**Key Features & Process**:
-   **Initialization**:
    -   Takes Plex URL (`plex_url`), Plex token (`plex_token`), and the target `library_name`.
    -   Initializes a `PlexServer` instance and gets the specified library section.
    -   Defines a regex pattern `self.pattern = r'\/([^\/]+)\.mp4$'` (or similar for other extensions if generalized) to extract the base filename (without extension and preceding path) from the full file path stored in Plex.
-   **Title Updating (`update_titles` method)**:
    -   Iterates through all video items in the specified Plex library (`self.library.all()`).
    -   For each `video` item:
        -   Retrieves the full file path of its primary media part (`video.media[0].parts[0].file`).
        -   Applies the regex `self.pattern` to this file path to extract the desired base filename, which becomes the `new_title`.
        -   If the regex matches and a `new_title` is extracted:
            -   It checks if the video's current title (`video.title`) already matches the `new_title`. If so, it skips updating to avoid unnecessary API calls.
            -   If the titles differ, it edits the Plex item's title using `video.edit(**{'title.value': new_title, 'title.locked': 1})`.
                -   `title.value`: Sets the new title.
                -   `title.locked`: Sets the title lock to 1 (locked), preventing Plex from automatically changing it later based on its own metadata agents.
            -   Logs the title update.
        -   If the regex does not match the file path, it logs that the pattern didn't match.
-   **Inputs**:
    -   Plex server URL and token.
    -   Name of the Plex library to process.
-   **Actions**:
    -   Directly modifies the titles of items within the Plex library.
-   **Dependencies**:
    -   `plexapi` library.
    -   A running Plex server with accessible credentials.

**Significance**:
-   Complements `PlexAutoSplitter`. After splitting, items might have generic names (e.g., "Show Title - Part 1", "Show Title - Part 1" again if Plex didn't differentiate). This tool ensures each item gets a unique and descriptive title based on its filename (e.g., "Show Title - S01E01 - Episode Name - Part 1").
-   Locking the title (`title.locked: 1`) is important to maintain these custom names against Plex's own metadata refreshes.
-   Provides clarity in the Plex interface and ensures that downstream tools that rely on Plex item titles can correctly identify content.

## Platform Integration Components

### PlexToDizqueTV
**File**: `ToonamiTools/PlexToDizqueTV.py`
**Class**: `PlexToDizqueTVSimplified`
**Purpose**: Transfers a curated lineup of Plex media items (defined in a database table) to a specified DizqueTV channel. It handles fetching media from Plex, converting them to DizqueTV program format, and adding them to the channel. It supports "Cutless Mode" by including custom start/end times if provided in the lineup data.

**Key Features & Process**:
-   **Initialization**:
    -   Takes Plex URL/token, names of anime and Toonami Plex libraries, the database `table` name containing the lineup, DizqueTV URL, target `channel_number`, and a `cutless_mode` boolean flag.
    -   Plex and DizqueTV API clients are initialized in the `run` method.
-   **Library Initialization (`_init_libraries` method)**:
    -   Caches media items from the specified Plex libraries (`anime_library` and `toonami_library`) into dictionaries (`self.anime_media`, `self.toonami_media`) mapping filenames to Plex item objects. This speeds up lookup.
    -   If `cutless_mode` is `False`, loading the `anime_library` is skipped (as cut content is expected to be in the `toonami_library`).
    -   Handles both TV shows (iterating episodes) and movies.
-   **Media Item Retrieval (`get_media_item`, `_find_in_library` methods)**:
    -   Given a `file_path` from the lineup table:
        -   Determines the primary Plex library to search using `determine_library` (if `cutless_mode` is true, it checks filename for network name; otherwise, defaults to `toonami_library`).
        -   Searches the cached media dictionaries first by full filename, then by filename without extension.
        -   Includes Unicode normalization (`_normalize_unicode`) for filenames with special characters.
        -   If `cutless_mode` is true and the item is not found by filename in the anime library, it attempts to parse show title, season, and episode from the filename and find it via `plex.library.section(anime_library).get(show_title).episode(season, episode)`, with fuzzy matching for show titles (`fuzzy_find_show`).
        -   If not found in the primary library, it tries the secondary library (if applicable).
-   **Lineup Processing (`run` method)**:
    -   Connects to Plex and DizqueTV.
    -   Loads the lineup DataFrame from the specified database `table`.
    -   Iterates through each row (media item) in the lineup DataFrame:
        -   Retrieves the `FULL_FILE_PATH`.
        -   Calls `get_media_item` to find the corresponding Plex item.
        -   If the Plex item is found:
            -   Converts the Plex item to a DizqueTV program object using `dtv.convert_plex_item_to_program()`.
            -   If the lineup row contains `startTime` or `endTime` (used in Cutless Mode), these are added to the DizqueTV program's `_data` as `seekPosition` and `endPosition` (in milliseconds).
            -   Adds the configured program to a list `to_add`.
        -   If the Plex item is not found, it's added to a `missing_files` list.
    -   If any files are missing, an exception is raised.
-   **DizqueTV Channel Update**:
    -   Retrieves the DizqueTV channel by `channel_number`. If not found, creates a new one.
    -   Deletes all existing programs from the channel.
    -   Adds the new list of programs (`to_add`) to the channel.
-   **Inputs**:
    -   Plex server URL/token, anime library name, Toonami library name.
    -   DizqueTV server URL, target channel number.
    -   Name of the SQLite database table containing the ordered lineup (with `FULL_FILE_PATH`, and optional `startTime`, `endTime` columns).
    -   `cutless_mode` flag.
    -   `config.py` for show name mappings (used in `fuzzy_find_show`).
-   **Outputs/Actions**:
    -   Modifies a DizqueTV channel by replacing its programming with the new lineup.
    -   Logs progress and any missing files to the console.

**Significance**: This is the component responsible for translating the abstract lineup (stored in the database) into a playable channel on DizqueTV. Its support for `startTime` and `endTime` is critical for the "Cutless Mode" functionality, allowing DizqueTV to play specific segments of original, uncut files to simulate commercial breaks.

### PlexToTunarr
**File**: `ToonamiTools/PlexToTunarr.py`
**Class**: `PlexToTunarr`
**Purpose**: Transfers a curated lineup of Plex media items (defined in a database table) to a specified Tunarr channel. It fetches media from Plex, converts them into Tunarr program format, and updates the channel programming. It also handles the insertion of "flex" (placeholder/filler) content if Toonami-branded items appear consecutively without an intro.

**Key Features & Process**:
-   **Initialization**:
    -   Takes Plex URL/token, Plex `library_name` (typically the Toonami library), database `table` name for the lineup, Tunarr URL, target `channel_number`, `flex_duration`, and an optional `channel_name`.
    -   Connects to Plex.
    -   Loads lineup data from the specified SQLite `table` into a DataFrame.
    -   Initializes `plex_source_info` by calling `get_plex_source_info` to find or create the Plex media source ID in Tunarr.
-   **Tunarr Media Source Management (`get_plex_source_info`, `get_plex_media_source_id`, `create_plex_media_source`)**:
    -   Retrieves existing media sources from Tunarr (`/api/media-sources`).
    -   Tries to find a Plex source matching the `plex_url`.
    -   If no exact match, uses the first available Plex source.
    -   If no Plex source exists, attempts to create one automatically using the provided Plex URL and token.
-   **Tunarr Channel Management (`get_channel_by_number`, `create_channel`, `delete_all_programs`)**:
    -   `get_channel_by_number`: Fetches channel details from Tunarr.
    -   `create_channel`: Creates a new channel in Tunarr if one doesn't exist, using default settings and the first available transcode config.
    -   `delete_all_programs`: Clears existing programming from a channel by posting an empty lineup.
-   **Plex Item to Tunarr Program Conversion (`build_full_program` method)**:
    -   Takes a Plex item object.
    -   Constructs a Tunarr program dictionary with fields like `type: "content"`, `externalSourceType: "plex"`, `externalSourceId` (from `plex_source_info`), `date`, `duration`, `serverFileKey`, `serverFilePath`, `externalKey` (Plex ratingKey), `summary`, `title`, `uniqueId`.
-   **Lineup Posting with Flex Injection (`post_manual_lineup` method)**:
    -   This is the core logic for building the Tunarr channel's programming.
    -   Iterates through the `plex_items` (derived from the input DB table).
    -   **Program Array (`programs`)**:
        -   For each unique Plex item, `build_full_program` is called.
        -   The program's `originalIndex` is set.
        -   A single "flex" program object is created if needed (type: "flex", duration from `self.flex_duration`).
    -   **Lineup Array (`lineup`)**:
        -   This array defines the sequence of programs. Each entry is an object like `{"duration": ..., "index": ..., "type": "index"}` pointing to an item in the `programs` array.
        -   **Flex Injection Logic**:
            -   Tracks if the `prev_was_toonami` (based on title matching `config.network`).
            -   If the previous item was a Toonami item AND the current item is also a Toonami item AND the current item's title does NOT contain "intro" (case-insensitive):
                -   A reference to the "flex" program is inserted into the `lineup` before the current item.
        -   The actual Plex item is then added to the `lineup`.
    -   Handles duplicate Plex items in the sequence by either creating a new persisted=false program object (if it's the last occurrence) or by re-referencing the first occurrence's index in the `programs` array.
    -   The final payload `{ "type": "manual", "lineup": ..., "programs": ... }` is POSTed to `/api/channels/{channel_id}/programming`.
-   **Main Workflow (`run` method)**:
    1.  Fetches all media from the specified Plex `library_name`.
    2.  Filters these `all_media` items based on `FULL_FILE_PATH`s present in the loaded database `table` (lineup).
    3.  Gets or creates the Tunarr channel.
    4.  Deletes all old programs from the channel.
    5.  Calls `post_manual_lineup` to add the new programming.
-   **Inputs**:
    -   Plex server URL/token, Plex library name.
    -   Tunarr server URL, target channel number, flex duration.
    -   Name of the SQLite database table containing the ordered lineup (with `FULL_FILE_PATH`).
    -   `config.network` (for identifying Toonami-branded titles).
-   **Outputs/Actions**:
    -   Modifies a Tunarr channel by replacing its programming.
    -   May create a new Plex media source or channel in Tunarr if they don't exist.
    -   Logs extensively using Python's `logging` module.

**Significance**: This component bridges the gap between the generated Toonami lineup and the Tunarr platform. Its key differentiator from the DizqueTV version is the built-in flex injection logic during lineup construction, tailored for Tunarr's programming model.

### JellyfinToTunarr
**File**: `ToonamiTools/JellyfinToTunarr.py`
**Class**: `JellyfinToTunarr`
**Purpose**: Transfers a curated lineup of Jellyfin media items (defined in a database table) to a specified Tunarr channel. Functionally equivalent to `PlexToTunarr` but designed to work with Jellyfin servers. It fetches media from Jellyfin, converts them into Tunarr program format, and updates the channel programming with automatic flex insertion.

**Key Features & Process**:
-   **Initialization**:
    -   Takes Jellyfin URL/token/user ID, Jellyfin `library_name`, database `table` name for the lineup, Tunarr URL, target `channel_number`, `flex_duration`, and an optional `channel_name`.
    -   Loads the database table containing the ordered lineup (typically populated by prior components like `ToonamiChecker` or `ShowScheduler`).
    -   Calls `get_jellyfin_source_info` to establish or locate a Jellyfin media source in Tunarr.
-   **Media Source Management**:
    -   `get_jellyfin_source_info`: Checks if a Jellyfin media source exists in Tunarr, creates one if missing.
    -   `create_jellyfin_media_source`: Creates a new Jellyfin media source in Tunarr with the provided server URL and access token.
-   **Media Fetching and Filtering**:
    -   `get_jellyfin_library_id`: Resolves the Jellyfin library name to a library ID using Jellyfin's API.
    -   `get_all_jellyfin_media`: Fetches all episodes and movies from the specified Jellyfin library.
    -   `filter_media_by_database`: Filters Jellyfin media items to match entries in the database table (typically by file path or show name).
-   **Format Conversion**:
    -   `convert_jellyfin_to_tunarr_format`: Converts Jellyfin media items to Tunarr program format, including duration, metadata, and external source references.
    -   Handles Jellyfin-specific metadata extraction like series names, season/episode numbers.
-   **Channel Management**:
    -   `get_channel_by_number`, `create_channel`: Manages Tunarr channel creation and lookup.
    -   `delete_all_programs`: Clears existing programming from the target channel.
    -   `post_manual_lineup`: Uploads the converted program lineup to Tunarr, automatically inserting flex content between consecutive programs.
-   **Main Execution (`run` method)**:
    1.  Fetches all media from the Jellyfin library.
    2.  Filters media based on database entries (if database is populated).
    3.  Gets or creates the Tunarr channel.
    4.  Deletes all old programs from the channel.
    5.  Converts Jellyfin items to Tunarr format and posts the new programming.
-   **Inputs**:
    -   Jellyfin server URL/token/user ID, Jellyfin library name.
    -   Tunarr server URL, target channel number, flex duration.
    -   Name of the SQLite database table containing the ordered lineup.
-   **Outputs/Actions**:
    -   Modifies a Tunarr channel by replacing its programming with Jellyfin-sourced content.
    -   May create a new Jellyfin media source or channel in Tunarr if they don't exist.
    -   Logs extensively using Python's `logging` module.

**Significance**: This component enables Jellyfin users to create Toonami-style channels in Tunarr, providing an alternative to Plex for users who prefer open-source media server solutions. It maintains feature parity with `PlexToTunarr` while adapting to Jellyfin's API structure and authentication system.

**Important Notes**:
-   Only works with Tunarr (DizqueTV does not support Jellyfin).
-   Requires Jellyfin server URL to be provided during authentication (unlike Plex which can auto-discover servers).
-   Uses Jellyfin's REST API for all media operations.

### FlexInjector
**File**: `ToonamiTools/FlexInjector.py`
**Class**: `DizqueTVManager`
**Purpose**: Modifies an existing DizqueTV channel's programming to insert "flex" content (offline placeholders) between consecutive Toonami-branded items, unless the second item is an "Intro". This is used to simulate commercial breaks or transitions.

**Key Features & Process**:
-   **Initialization**:
    -   Takes DizqueTV platform URL (`platform_url`), target `channel_number`, flex `duration` (string like "MM:SS"), and `network` name (e.g., "Toonami" from `config.network`).
    -   Constructs the DizqueTV API URL.
-   **Time Conversion (`convert_to_milliseconds` method)**:
    -   Converts a "MM:SS" duration string into milliseconds.
-   **Flex Target Identification (`is_flex_target` method)**:
    -   Checks if a given program `title` contains the `self.network` name (case-insensitive). This identifies Toonami-branded content.
-   **Flex Insertion Logic (`insert_flex` method)**:
    -   Takes the `channel_data` (a dictionary representing the channel's programming, typically fetched from DizqueTV API).
    -   Calculates `flex_length` in milliseconds.
    -   Iterates through the `programs_list` from `channel_data`.
    -   Appends the current program to a `new_programs` list.
    -   **Conditions for inserting flex**:
        -   If the current program is a `flex_target` (Toonami item) AND
        -   There is a next program AND
        -   The next program is also a `flex_target` (Toonami item) AND
        -   The next program's title does NOT contain "Intro" (case-insensitive) AND
        -   The next program is NOT already an offline/flex entry (`'isOffline' not in programs_list[i + 1]`).
        -   Then, an `is_offline_entry` (flex item: `{'duration': flex_length, 'isOffline': True}`) is appended to `new_programs`.
    -   Also handles a specific case: if the *next* item's title contains "Intro", a flex entry is added *before* that intro, regardless of the current item's branding. This seems to ensure a break before intros following any content.
    -   If a program in the original list is already an offline entry (`'isOffline' in program`), its duration is updated to `flex_length`.
    -   Returns the `channel_data` with the modified `programs` list.
-   **Main Workflow (`main` method)**:
    1.  Fetches the current programming for the specified `channel_number` from the DizqueTV API (`/api/channel/{channel_number}`).
    2.  Calls `insert_flex` to modify the fetched channel data.
    3.  Posts the modified channel data back to DizqueTV API (`/api/channel`) to update the channel.
    4.  Logs progress and success/failure.
-   **Inputs**:
    -   DizqueTV server URL.
    -   Target channel number.
    -   Flex duration string (e.g., "02:30").
    -   Network name (e.g., "Toonami") for identifying relevant programs.
-   **Outputs/Actions**:
    -   Modifies the programming of an existing DizqueTV channel by inserting or updating flex/offline items.

**Significance**: This tool provides a way to dynamically add simulated commercial breaks or transition fillers into a DizqueTV channel after its initial programming has been set up by `PlexToDizqueTV`. It allows for fine-tuning the pacing of the Toonami block.

## Extra Tools and Utilities

### Manual Show Adder
**File**: `ExtraTools/ManualShowAdder.py`
**Purpose**: Adds custom shows to Toonami lineup

**Use Cases**:
- Adding shows that "should have been" on Toonami
- Integrating custom or fan-favorite content
- Expanding beyond historical Toonami catalog

**Requirements**:
- Show must be cut (uses traditional cutting)
- Requires custom bumps ("to ads", "back", optionally "generic")
- Automatically integrates with existing lineup system

**Note**: The file `ExtraTools/ManualShowAdder.py` was not provided in the codebase. The documentation above is based on the description in the `README.md` and the placeholder in `Component-Documentation.md`. Functionality details cannot be confirmed without the source code.

### Manual Timestamp Editor
**File**: `ExtraTools/ManualTimestampEditor.py`
**Class**: `FolderMatchingTool` (Tkinter GUI application)
**Purpose**: Provides a graphical interface for users to manually create or edit timestamp files (`.txt`) associated with video files (`.mkv`). These timestamp files are used by `CommercialBreaker` to determine cut points.

**Key Features & Process**:
-   **GUI Application**: Built using Tkinter.
-   **Folder Selection**:
    -   Allows the user to select an "Anime Folder" (input video files) and a "Cut Folder" (output/timestamp files).
    -   `select_in_folder`: Stores the path to the anime folder.
    -   `select_out_folder`: Stores the path to the cut/timestamp folder.
-   **Timestamp File Management (`process_folders` method)**:
    -   When "Edit Timestamps" is clicked:
        -   Walks through the selected "Anime Folder".
        -   For each `.mkv` file found, it determines the corresponding path for a `.mkv.txt` timestamp file in the "Cut Folder" (maintaining the relative directory structure).
        -   If a timestamp file does not exist, it creates an empty one. This ensures every video file can have its timestamps edited.
-   **Timestamp Editing Interface**:
    -   A new Toplevel window ("Timestamps") is created.
    -   A `Text` widget (`self.text_box`) on the left displays the content of the selected timestamp file.
    -   A `Frame` on the right lists all `.mkv.txt` files found in the "Cut Folder", organized by subfolder.
        -   Clicking on a filename in this list calls `display_file_contents`.
    -   `display_file_contents(file_path)`:
        -   If another file was being edited, its current content from `self.text_box` is saved to a temporary file.
        -   If the `file_path` is being opened for the first time in this session, its content is copied to a new temporary file (original is preserved until explicit save).
        -   The content of the (potentially temporary) timestamp file is loaded into `self.text_box`.
-   **Saving Changes (`save_changes` method)**:
    -   When the "Save" button in the "Timestamps" window is clicked:
        -   Iterates through all `self.temp_files` (which maps original file paths to their temporary counterparts).
        -   Copies the content from each temporary file back to the original timestamp file, overwriting it.
        -   Deletes the temporary files.
-   **Temporary File Usage**: Edits are made to temporary copies of the timestamp files. Originals are only overwritten upon explicit save. This provides a safety net against accidental changes.
-   **Inputs**:
    -   User-selected "Anime Folder" (containing `.mkv` videos).
    -   User-selected "Cut Folder" (where `.mkv.txt` timestamp files are/will be stored).
    -   Manual text input by the user into the text box.
-   **Outputs**:
    -   Creates or modifies `.txt` files in the "Cut Folder", containing timestamps (presumably one per line, representing cut points in seconds or HH:MM:SS.milliseconds format, though the exact format isn't dictated by this editor itself but by what `CommercialBreaker` expects).

**Significance**: This tool offers a manual override and fine-tuning capability for the commercial break points identified by `CommercialBreaker`. If automated detection is imperfect or if users want precise control, they can use this GUI to adjust the timestamps directly.

### Part Renamer
**File**: `ExtraTools/CutFailRenamer.py`
**Class**: `CutFileRenamer`
**Purpose**: Renames video files (specifically `.mp4` parts) in a directory structure, adjusting their part numbers. This is typically used to correct filenames if a previous cutting process was interrupted or resulted in an off-by-one error in part numbering (e.g., parts starting from 000 instead of 1, or needing to increment all part numbers).

**Key Features & Process**:
-   **Initialization**:
    -   Takes an `input_dir` which is the root directory containing the cut video files to be processed.
-   **File Renaming Logic (`rename_files` method)**:
    -   Walks through the `input_dir` and its subdirectories.
    -   For each file found:
        -   Checks if the file ends with ".mp4".
        -   Splits the filename by "Part " to identify if it's a multi-part file.
        -   If it is a part file and the part identifier (e.g., "000" from "Part 000.mp4") is a digit:
            -   Extracts the `part_number` (integer).
            -   Constructs a `new_name` by replacing the old part string (e.g., "Part 000") with a new part string where the number is incremented by 1 (e.g., "Part 1"). The original code example `f"Part {str(part_number).zfill(3)}"` for the *old* part string and `f"Part {part_number + 1}"` for the *new* part string suggests it's designed to re-index parts that might be 0-indexed or to shift all part numbers up by one.
            -   The line `os.rename(old_name, new_path)` is commented out in the provided snippet, so it currently only prints what it *would* rename. To make it functional, this line would need to be uncommented.
        -   If the file doesn't match the expected pattern, it's skipped.
-   **Example Usage (in the script)**:
    -   `input_dir = r"M:\Cut"`
    -   An instance of `CutFileRenamer` is created and `rename_files()` is called.
-   **Inputs**:
    -   `input_dir`: Path to the directory containing cut `.mp4` files with "Part XXX" in their names.
-   **Outputs/Actions**:
    -   (If `os.rename` is uncommented) Renames files in place within the `input_dir`.
    -   Prints intended renaming actions or skipped files to the console.

**Significance**: This is a utility tool for correcting filename inconsistencies that can arise from the video cutting process, especially if `CommercialBreaker` or another tool produces parts that need re-numbering for consistency or compatibility with Plex/other media servers' stacking behavior. The current implementation seems geared towards incrementing part numbers (e.g., "Part 000" -> "Part 1", "Part 001" -> "Part 2").

## Utility Components

### FolderMaker
**File**: `ToonamiTools/FolderMaker.py`
**Class**: `FolderMaker`
**Purpose**: Creates a predefined set of necessary subdirectories within a given input directory. This ensures that the various tools in the CommercialBreaker & Toonami Tools ecosystem have the expected folder structure to read from and write to.

**Key Features & Process**:
-   **Initialization**:
    -   Takes a `dir_input` which is the base directory where subfolders will be created.
    -   Has a predefined list of `self.folders = ['cut', 'toonami_filtered']`. These are the names of the subdirectories it will create.
-   **Folder Creation (`run` method)**:
    -   Iterates through the `self.folders` list.
    -   For each `folder` name in the list, it constructs the full path using `os.path.join(self.dir_input, folder)`.
    -   Uses `os.makedirs(path, exist_ok=True)` to create the directory.
        -   `exist_ok=True` means that if the directory already exists, the function will not raise an error, making the operation idempotent.
    -   Prints a confirmation message for each folder created.
-   **Inputs**:
    -   `dir_input`: The parent directory where the subfolders `cut` and `toonami_filtered` will be created. This is typically the "Working Folder" selected by the user in the GUI.
-   **Outputs/Actions**:
    -   Creates the 'cut' and 'toonami_filtered' subdirectories inside `dir_input` if they don't already exist.
    -   Prints creation status to the console.

**Significance**:
-   A simple but essential utility that sets up the foundational directory structure used by many other components in the pipeline.
-   `cut` folder: Typically used by `CommercialBreaker` as an output directory for timestamp files or physically cut video segments. Also used by `AnimeFileOrganizer` (CommercialInjectorPrep).
-   `toonami_filtered` folder: Used by `FilterAndMove` (EpisodeFilter) as a destination for moved show directories.
-   Ensures consistency and prevents errors that might arise if tools expect certain directories that haven't been created. Called early in the `prepare_content` workflow in `FrontEndLogic.py`.

---

This component ecosystem works together to transform a standard anime library into an authentic Toonami experience, with each tool handling a specific aspect of the complex pipeline required for professional-quality results.