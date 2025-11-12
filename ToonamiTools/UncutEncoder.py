import os
import re
from API.utils.DatabaseManager import get_db_manager
from API.utils.ErrorManager import get_error_manager
from itertools import cycle
import config
from .utils import show_name_mapper
from .utils.FilenameParser import FilenameParser


class UncutEncoder:
    def __init__(self):
        self.file_paths = []
        self.block_ids = []
        self.bumps_data = None
        self.intro_bump_cycle = {}
        self.generic_bump_cycle = {}
        self.default_bump_cycle = None  # Cycling default bumps
        self.db_manager = get_db_manager()
        self.error_manager = get_error_manager()

    def apply_show_name_mappings(self, show_name):
        mapped_name = show_name_mapper.map(show_name, strategy='all')
        return mapped_name

    def load_bumps_data(self):
        try:
            self.bumps_data = self.db_manager.fetchall_as_dicts('SELECT * FROM singles_data')
        except Exception as e:
            self.error_manager.send_critical(
                source="UncutEncoder",
                operation="load_bumps_data",
                message="Cannot access bump data",
                details=str(e),
                suggestion="Something went wrong accessing your processed bumps. Try running Prepare Content again"
            )
            raise

        if len(self.bumps_data) == 0:
            self.error_manager.send_error_level(
                source="UncutEncoder",
                operation="load_bumps_data",
                message="No single-show bumps found",
                details="The singles_data table is empty - no intro or generic bumps are available",
                suggestion="You need at least some single-show bumps for the uncut lineup. Add intro or generic bumps to your bump folder"
            )
            raise Exception("No single-show bumps available")

        # Normalize bump show names for consistent matching against BLOCK_ID-derived names
        for row in self.bumps_data:
            sn1 = row.get('SHOW_NAME_1', '')
            mapped = show_name_mapper.map(str(sn1), strategy='all')
            cleaned = show_name_mapper.clean(mapped, mode='matching')
            row['SHOW_NAME_1'] = cleaned

        # Check for default/fallback bumps
        default_bumps = [
            row['FULL_FILE_PATH'] for row in self.bumps_data
            if row.get('SHOW_NAME_1') and (
                'clydes' in row['SHOW_NAME_1'].lower() or
                'robot' in row['SHOW_NAME_1'].lower()
            )
        ]

        if default_bumps:
            self.default_bump_cycle = cycle(default_bumps)
        else:
            self.error_manager.send_warning(
                source="UncutEncoder",
                operation="load_bumps_data",
                message="No generic fallback bumps found",
                details="No 'clydes' or 'robot' bumps found to use as defaults",
                suggestion="Consider adding some generic Toonami bumps (with 'clydes' or 'robot' in the name) as fallbacks for shows without specific bumps"
            )

    def find_files(self):
        # Query the database for the full file paths
        query = "SELECT Full_File_Path FROM toonami_episodes"
        try:
            rows = self.db_manager.fetchall(query)
            file_paths = [row[0] for row in rows]
        except Exception as e:
            self.error_manager.send_error_level(
                source="UncutEncoder",
                operation="find_files",
                message="Cannot read episode data",
                details=str(e),
                suggestion="Something went wrong accessing your episode list. Try running Prepare Content again"
            )
            raise

        if len(file_paths) == 0:
            self.error_manager.send_error_level(
                source="UncutEncoder",
                operation="find_files",
                message="No episodes found",
                details="The toonami_episodes table is empty",
                suggestion="No Toonami shows were found in your library. Check that your anime files are named correctly and try again"
            )
            raise Exception("No episodes to process")

        # Extract episode data with show, season, episode info
        episode_data = []
        pattern = re.compile(r"/([^/]+)/Season (\d+)/[^/]+ - S(\d+)E(\d+)")

        for full_path in file_paths:
            normalized_path = os.path.normpath(full_path)
            if normalized_path.endswith((".mkv", ".mp4")):
                match = pattern.search(normalized_path.replace('\\', '/'))
                if match:
                    # Extract show name from directory and strip any year in parentheses
                    show_name = FilenameParser.strip_year_from_show_name(match[1])
                    season = int(match[3])  # Use S number from pattern
                    episode = int(match[4])  # Use E number from pattern
                    # Store path, extracted info for sorting
                    episode_data.append((normalized_path, show_name, season, episode))
                else:
                    episode_data.append((normalized_path, "", 0, 0))

        # Sort by show, season, episode
        episode_data.sort(key=lambda x: (x[1], x[2], x[3]))

        # Update file_paths and block_ids
        self.file_paths = []
        self.block_ids = []
        for path, *_ in episode_data:
            self.file_paths.append(path)
            match = pattern.search(path.replace('\\', '/'))
            if match:
                # Strip year from show name before creating BLOCK_ID
                show_name = FilenameParser.strip_year_from_show_name(match[1])
                block_id = show_name_mapper.to_block_id(show_name)
                season = match[3]
                episode = match[4]
                self.block_ids.append(f"{block_id}_S{season.zfill(2)}E{episode.zfill(2)}")
            else:
                self.block_ids.append("")

        # Check if we failed to parse any episodes
        failed_files = [self.file_paths[i] for i, bid in enumerate(self.block_ids) if bid == ""]
        if failed_files:
            file_list = "\n".join([f"• {os.path.basename(f)}" for f in failed_files])
            self.error_manager.send_warning(
                source="UncutEncoder",
                operation="find_files",
                message=f"{len(failed_files)} files have non-standard naming and cannot be processed",
                details=f"These files need to be renamed:\n{file_list}",
                suggestion="Please rename the files according to the conventions: https://github.com/theweebcoders/CommercialBreaker/wiki/File-Naming-Conventions"
            )

    def insert_intro_bumps(self):
        shows_without_bumps = set()
        shows_with_bumps = set()

        for i in range(len(self.file_paths) - 1, -1, -1):
            block_id = self.block_ids[i]
            if not block_id:  # Skip files that couldn't be parsed
                continue

            # Derive show_name from BLOCK_ID, then map+clean to the same DB key form
            show_name = block_id.split('_S')[0].replace('_', ' ')
            mapped_name = show_name_mapper.map(show_name, strategy='all')
            show_name = show_name_mapper.clean(mapped_name, mode='matching')

            intro_bump = None

            # Try to find intro bumps
            intro_bumps = [
                row['FULL_FILE_PATH'] for row in self.bumps_data
                if row.get('SHOW_NAME_1') == show_name and
                row.get('PLACEMENT_2') and
                'intro' in row['PLACEMENT_2'].lower()
            ]

            if intro_bumps:
                if show_name not in self.intro_bump_cycle:
                    self.intro_bump_cycle[show_name] = cycle(intro_bumps)
                intro_bump = next(self.intro_bump_cycle[show_name])
                shows_with_bumps.add(show_name)

            # Try generic bumps if no intro found
            else:
                generic_bumps = [
                    row['FULL_FILE_PATH'] for row in self.bumps_data
                    if row.get('SHOW_NAME_1') == show_name and
                    row.get('PLACEMENT_2') and
                    'generic' in row['PLACEMENT_2'].lower()
                ]

                if generic_bumps:
                    if show_name not in self.generic_bump_cycle:
                        self.generic_bump_cycle[show_name] = cycle(generic_bumps)
                    intro_bump = next(self.generic_bump_cycle[show_name])
                    shows_with_bumps.add(show_name)

                # Use default bumps as last resort
                else:
                    shows_without_bumps.add(show_name)
                    if self.default_bump_cycle:
                        intro_bump = next(self.default_bump_cycle)
                    else:
                        # No fallback available - this is a critical issue
                        self.error_manager.send_error_level(
                            source="UncutEncoder",
                            operation="insert_intro_bumps",
                            message=f"No bumps available for show: {show_name}",
                            details=f"'{show_name}' has no intro, generic, or fallback bumps",
                            suggestion="Add bumps for this show or generic Toonami bumps to continue"
                        )
                        raise Exception(f"No bumps available for {show_name}")

            if intro_bump:
                self.file_paths.insert(i, intro_bump)
                self.block_ids.insert(i, block_id)

        # Report shows without specific bumps
        if shows_without_bumps:
            if self.default_bump_cycle:
                self.error_manager.send_info(
                    source="UncutEncoder",
                    operation="insert_intro_bumps",
                    message=f"{len(shows_without_bumps)} shows using generic bumps",
                    details=f"{len(shows_without_bumps)} shows don't have specific intro bumps",
                    suggestion="Consider adding intro bumps for these shows for a better experience"
                )
            # If no default_bump_cycle, we already raised an error above

    def create_table(self):
        print("Creating table in the database")
        data = [{'FULL_FILE_PATH': fp, 'BLOCK_ID': bid}
                for fp, bid in zip(self.file_paths, self.block_ids)]

        try:
            with self.db_manager.transaction() as conn:
                conn.execute("DROP TABLE IF EXISTS uncut_encoded_data")

                if data:
                    columns = list(data[0].keys())
                    column_names = ','.join([f'"{col}"' for col in columns])
                    placeholders = ','.join(['?' for _ in columns])
                    conn.execute(f"CREATE TABLE uncut_encoded_data ({column_names})")
                    conn.executemany(
                        f"INSERT INTO uncut_encoded_data VALUES ({placeholders})",
                        [tuple(row[col] for col in columns) for row in data]
                    )
        except Exception as e:
            self.error_manager.send_error_level(
                source="UncutEncoder",
                operation="create_table",
                message="Failed to save uncut lineup data",
                details=str(e),
                suggestion="There was an issue saving your lineup. Try running Prepare Content again"
            )
            raise

        print("Table created in the database.")

    def run(self):
        try:
            self.load_bumps_data()
            self.find_files()
            self.insert_intro_bumps()
            self.create_table()
            print("Process completed.")
        except Exception:
            # Errors already logged by individual methods
            raise
