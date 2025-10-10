import pandas as pd
import random
from API.utils.DatabaseManager import get_db_manager
import re
import config
from .utils import show_name_mapper


class ShowScheduler:
    """
    ShowScheduler organizes shows into a schedule, reusing episode blocks if needed,
    continuing from the last used episode block, and applying optional NS3 logic
    (for multi-show transitions). It can handle both cut and uncut channels.
    """

    def __init__(
        self,
        reuse_episode_blocks=True,
        continue_from_last_used_episode_block=False,
        apply_ns3_logic=False,
        uncut=False
    ):
        """
        Initialize ShowScheduler.

        :param reuse_episode_blocks: If True, once episode blocks are exhausted,
                                     they can be reused from the beginning.
        :param continue_from_last_used_episode_block: If True, the scheduler
                                                      continues from the last
                                                      used episode block for
                                                      each show in a new schedule.
        :param apply_ns3_logic: Whether or not to apply special -NS3 logic that
                                rearranges certain multi-show transitions.
        :param uncut: If True, the schedule is for uncut anime; otherwise,
                      it's for cut anime.
        """
        # Database connection
        self.db_manager = get_db_manager()
        
        # Dataframes
        self.encoder_df = None
        self.decoded_df = None
        self.commercial_injector_df = None
        self.decoder = {}
        self.show_episode_blocks = None

        # Configuration toggles
        self.reuse_episode_blocks = reuse_episode_blocks
        self.shows_with_no_more_blocks = set()
        self.continue_from_last_used_episode_block = continue_from_last_used_episode_block
        self.apply_ns3_logic = apply_ns3_logic
        self.uncut = uncut

        # Storage for special handling
        self.ns3_special_indices = []

        # Possibly load previously used blocks if continuing
        if continue_from_last_used_episode_block:
            if self.db_manager.table_exists("last_used_episode_block"):
                self.last_used_episode_block = self.load_last_used_episode_block()
                print("Continuing from last used episode blocks")
            else:
                print("Resetting episode tracking for the last spreadsheet.")
        else:
            # If not continuing, reset
            self.last_used_episode_block = {}
            print("Resetting episode tracking for the last spreadsheet.")

    #####################################################
    #                 SETUP & CONFIG METHODS            #
    #####################################################

    def set_paths(self, encoder_table, commercial_table):
        """
        Set the DB table paths and load relevant data frames.
    
        :param encoder_table: Name of the table containing encoded data
                              (with show codes).
        :param commercial_table: Name of the table containing commercial
                                 injector data (with BLOCK_ID references).
        """
        print("Setting file paths...")
        print(f"Loading encoder data from {encoder_table}")
        print(f"Loading commercial injector data from {commercial_table}")
        print("Loading codes from codes")
    
        with self.db_manager.transaction() as conn:
            self.encoder_df = pd.read_sql(f"SELECT * FROM {encoder_table}", conn)
        self._load_codes()
        self.decoded_df = self._decode_shows()
    
        # Get unique shows from the encoder table
        used_shows = set()
        for shows_list in self.decoded_df["shows"]:
            used_shows.update(shows_list)
    
        # Use show_name_mapper to get all possible BLOCK_ID prefixes
        block_id_prefixes = set()
        for show in used_shows:
            block_id_prefixes.update(show_name_mapper.get_block_id_prefixes(show))
        
        # Convert set to list for SQL query
        block_id_prefixes = list(block_id_prefixes)
        
        # The BLOCK_ID format is SHOW_NAME_S##E## (note the _S pattern)
        where_conditions = " OR ".join([f"BLOCK_ID LIKE '{prefix}_S%'" for prefix in block_id_prefixes])
    
        # Load only relevant rows from commercial_injector table
        if where_conditions:
            query = f"SELECT * FROM {commercial_table} WHERE {where_conditions}"
            with self.db_manager.transaction() as conn:
                self.commercial_injector_df = pd.read_sql(query, conn)
            print(f"Loaded {len(self.commercial_injector_df)} rows for {len(used_shows)} shows")
            
            # Extract show_name from BLOCK_ID by splitting at "_S", then normalize
            self.commercial_injector_df["show_name"] = (
                self.commercial_injector_df["BLOCK_ID"]
                .str.rsplit(pat="_S", n=1)
                .str[0]
                .str.replace("_", " ")
                .str.lower()
            )
            
            self._normalize_show_names()
            self.show_episode_blocks = self._group_shows()
            
            # Verify we found episodes for all shows
            missing_shows = []
            normalized_used_shows = [self._normalize_show_name(show) for show in used_shows]
            for show in normalized_used_shows:
                if show not in self.show_episode_blocks or not self.show_episode_blocks[show]:
                    missing_shows.append(show)
            
            if missing_shows:
                print(f"WARNING: Failed to find episodes for shows: {missing_shows}")
                print("Falling back to loading full commercial_injector table...")
                
                # JUST LOAD THE WHOLE TABLE - NO OPTIMIZATION
                with self.db_manager.transaction() as conn:
                    self.commercial_injector_df = pd.read_sql(f"SELECT * FROM {commercial_table}", conn)
                print(f"Loaded all {len(self.commercial_injector_df)} rows (fallback mode)")
                
                # Re-extract and normalize
                self.commercial_injector_df["show_name"] = (
                    self.commercial_injector_df["BLOCK_ID"]
                    .str.rsplit(pat="_S", n=1)
                    .str[0]
                    .str.replace("_", " ")
                    .str.lower()
                )
                
                self._normalize_show_names()
                self.show_episode_blocks = self._group_shows()
        else:
            # NO OPTIMIZATION - JUST LOAD EVERYTHING
            with self.db_manager.transaction() as conn:
                self.commercial_injector_df = pd.read_sql(f"SELECT * FROM {commercial_table}", conn)
            print(f"Loaded all {len(self.commercial_injector_df)} rows (no show filtering)")
            
            # Extract show_name from BLOCK_ID by splitting at "_S", then normalize
            self.commercial_injector_df["show_name"] = (
                self.commercial_injector_df["BLOCK_ID"]
                .str.rsplit(pat="_S", n=1)
                .str[0]
                .str.replace("_", " ")
                .str.lower()
            )
            
            self._normalize_show_names()
            self.show_episode_blocks = self._group_shows()

    def _load_codes(self):
        """
        Load the 'codes' table from the DB to decode show codes in
        the encoder dataframe.
        """
        print("Loading codes...")
        with self.db_manager.transaction() as conn:
            codes_df = pd.read_sql("SELECT * FROM codes", conn)
        self.decoder = {row["Code"]: row["Name"].lower() for _, row in codes_df.iterrows()}

    def _decode_shows(self):
        """
        Decode the 'Code' field in encoder_df into a list of show names.
        """
        print("Decoding shows...")
        decoded_df = self.encoder_df.copy()
        decoded_df["shows"] = decoded_df["Code"].apply(self._extract_show_codes)
        return decoded_df

    def _normalize_show_names(self):
        """
        Normalize show names in both the decoded_df and commercial_injector_df
        to unify naming.
        """
        self.decoded_df["shows"] = self.decoded_df["shows"].apply(
            lambda shows_list: [self._normalize_show_name(s) for s in shows_list]
        )
        self.commercial_injector_df["show_name"] = self.commercial_injector_df["show_name"].apply(
            self._normalize_show_name
        )

    def _extract_show_codes(self, code):
        """
        Extract 'S...' codes from a string, use decoder to map them back
        to show names, and return a list of show names.
        """
        parts = code.split("-")
        show_codes = [part.split(":")[1] for part in parts if part.startswith("S")]
        decoded_show_codes = [self.decoder[sc] for sc in show_codes]
        return decoded_show_codes

    def _normalize_show_name(self, show):
        """
        Return normalized show name using show_name_mapper,
        if it exists; otherwise, return the original show name.
        """
        # Apply the same normalization as other modules: map all, then clean for matching
        mapped = show_name_mapper.map(show, strategy='all')
        return show_name_mapper.clean(mapped, mode='matching')

    def _group_shows(self):
        """
        Group the commercial_injector_df by show_name and BLOCK_ID,
        returning a dict of episode blocks for each show.
        """
        grouped = self.commercial_injector_df.groupby("show_name").apply(
            lambda x: x.groupby("BLOCK_ID").apply(
                lambda y: y[["FULL_FILE_PATH", "BLOCK_ID"]].values.tolist()
            ).values.tolist()
        )
        return grouped.to_dict()

    #####################################################
    #             CORE SCHEDULER METHODS                #
    #####################################################

    def run(self, encoder_table, commercial_table, save_table):
        """
        Main method to run the entire scheduling process:
         - Reset last_used_episode_block if needed
         - Load data, decode, and generate schedule
         - Apply NS3 adjustments if configured
         - If continuing from the last used episode block, attempt to
           insert unused shows
         - Save final schedule
         - Save updated last used blocks if continuing
        """
        # Possibly reset usage tracking if no continuity
        if "multi" in encoder_table.lower() and not self.continue_from_last_used_episode_block:
            self.last_used_episode_block = {}
            print("Resetting episode tracking for the last spreadsheet.")

        print("Running the show scheduler...")
        self.set_paths(encoder_table, commercial_table)

        # Determine whether we apply NS3 logic
        if not self.encoder_df["Code"].str.contains("-NS2").any() or self.uncut:
            self.apply_ns3_logic = False
            print("No NS2 bumps found or uncut mode. Skipping NS3 logic.")
        else:
            self.apply_ns3_logic = True
            print("NS2 bumps found. Applying NS3 logic.")

        final_df = self.generate_schedule()
        final_df = self.adjust_final_df_based_on_ns3_indices(final_df)

        # Optionally add unused shows if continuing from last used block
        if self.continue_from_last_used_episode_block:
            unused_shows_df = self.get_unused_shows()
            if not unused_shows_df.empty:
                anchor_rows = self.locate_lines_of_fourth_unique_block_id(final_df)
                final_df = self.add_unused_shows_to_schedule(final_df, unused_shows_df, anchor_rows)
            else:
                print("No unused shows available. Skipping related operations.")

        self.save_schedule(final_df, save_table)

        # If continuing from last used block, save our updated usage
        if self.continue_from_last_used_episode_block:
            self.save_last_used_episode_block()
            print("Last used episode blocks have been saved.")

        print(f"Schedule successfully saved to {save_table}")

    def generate_schedule(self):
        """
        Main method to generate the schedule using the decoded_df, reordering
        blocks, applying optional NS2/NS3 logic, and reusing blocks as necessary.
        """
        print("Generating schedule...")
        final_df = pd.DataFrame(columns=["FULL_FILE_PATH", "Code", "BLOCK_ID"])

        # For tracking certain row states
        last_show_name = None
        delete_intro = False
        last_bump_for_show = {}
        skip_first_show = False

        for idx, row in self.decoded_df.iterrows():
            shows = row["shows"]
            code_value = row["Code"] or ""

            # Detect if we have an NS2->NS3 chain from the previous row
            skip_first_show = self._detect_ns2_ns3_chain(idx, shows)

            # Check if any show is exhausted, skip if so
            if self._skip_exhausted_shows(shows, final_df, last_bump_for_show):
                continue

            if "-NS3" in code_value:
                # Handle an NS3 row
                final_df, last_show_name = self._handle_ns3_row(
                    final_df, row, idx, shows, skip_first_show, last_bump_for_show, delete_intro
                )
                skip_first_show = False  # Reset after usage
            elif "-NS2" in code_value:
                # Handle an NS2 row
                final_df, last_show_name, delete_intro = self._handle_ns2_row(
                    final_df, row, shows, last_show_name
                )
            else:
                # Potentially handle other code or do default append
                pass

            # Attempt to handle "interweaving" if next row is different
            final_df = self._attempt_interweave(idx, final_df, last_show_name, shows)

        print("Schedule generation complete.")
        return final_df

    def _detect_ns2_ns3_chain(self, idx, current_shows):
        """
        Check if the current row is an NS3 row following an NS2 row,
        involving the same show. If so, skip the first show from the
        NS3 row's show list.
        """
        if self.apply_ns3_logic and idx > 0:
            current_code = self.decoded_df.iloc[idx]["Code"] or ""
            prev_code = self.decoded_df.iloc[idx - 1]["Code"] or ""
            if ("-NS3" in current_code) and ("-NS2" in prev_code):
                prev_ns2_show = self.decoded_df.iloc[idx - 1]["shows"][0]
                current_ns3_show = current_shows[0]
                return prev_ns2_show == current_ns3_show
        return False

    def _skip_exhausted_shows(self, shows, final_df, last_bump_for_show):
        """
        If any show in 'shows' is exhausted, skip them.
        Also remove the last bump for that show from final_df if found.
        """
        if any(s in self.shows_with_no_more_blocks for s in shows):
            print(f"Skipping bump for show(s) {shows} as episode blocks have run out.")
            for s in shows:
                if s in self.shows_with_no_more_blocks:
                    last_bump_idx = last_bump_for_show.get(s)
                    if last_bump_idx is not None:
                        print(f"Removing bump for show {s} that just ran out.")
                        final_df.drop(index=last_bump_idx, inplace=True, errors="ignore")
                        final_df.reset_index(drop=True, inplace=True)
            return True
        return False

    def _handle_ns3_row(self, final_df, row, idx, shows, skip_first_show, last_bump_for_show, delete_intro):
        """
        Handle an NS3 row, potentially skipping the first show if skip_first_show is True.
        If the next row is also an NS3 with the same tail show, drop the last show
        in the current list. Then insert episodes for the remaining shows in order.
        """
        final_df = pd.concat(
            [final_df, pd.DataFrame([row[["FULL_FILE_PATH", "Code"]].to_dict()])],
            ignore_index=True
        )

        # Possibly delete intro for the first inserted show
        if not skip_first_show:
            delete_intro = True

        # If the next row also has -NS3 and shares a show, skip the last show in this row
        if (
            idx < len(self.decoded_df) - 1
            and "-NS3" in (self.decoded_df.iloc[idx + 1]["Code"] or "")
            and (self.decoded_df.iloc[idx + 1]["shows"][0] == shows[-1])
        ):
            shows_to_place = shows[:-1]
        else:
            shows_to_place = shows

        # Skip first show if triggered
        if skip_first_show:
            shows_to_place = shows_to_place[1:]

        # Insert episode blocks
        for show in shows_to_place:
            final_df, delete_intro = self._insert_episode_block(
                final_df, show, delete_intro, last_bump_for_show
            )

        last_show_name = shows_to_place[-1] if shows_to_place else None
        return final_df, last_show_name

    def _handle_ns2_row(self, final_df, row, shows, last_show_name):
        """
        Handle an NS2 row. If the final schedule's last show differs from
        show_name_2, we first insert show_name_2's block. Then we append the NS2 row
        and insert show_name_1's block (with a possible intro deletion).
        """
        show_name_1, show_name_2 = shows
        delete_intro = False

        # Compute availability of the required blocks first
        block2 = self.get_next_episode_block(show_name_2) if last_show_name != show_name_2 else self.get_next_episode_block(show_name_2)
        block1 = self.get_next_episode_block(show_name_1)

        # If neither side has an episode to place, skip this NS2 row
        if block1 is None and (block2 is None or last_show_name == show_name_2):
            return final_df, last_show_name, delete_intro

        # Insert next block for show_name_2 if needed and available (before the NS2 bump)
        if last_show_name != show_name_2 and block2 is not None:
            block_df2 = self.commercial_injector_df[
                self.commercial_injector_df["BLOCK_ID"] == block2["BLOCK_ID"]
            ]
            final_df = pd.concat(
                [final_df, block_df2[["FULL_FILE_PATH", "BLOCK_ID"]].assign(Code="")],
                ignore_index=True
            )
            last_show_name = show_name_2

        # Only append the NS2 row if we can follow it with show_name_1's episode block
        if block1 is not None:
            final_df = pd.concat(
                [final_df, pd.DataFrame([row[["FULL_FILE_PATH", "Code"]].to_dict()])],
                ignore_index=True
            )

            # Next block for show_name_1, with possible intro deletion
            delete_intro = True
            block_df1 = self.commercial_injector_df[
                self.commercial_injector_df["BLOCK_ID"] == block1["BLOCK_ID"]
            ]
            if delete_intro and not block_df1.empty:
                block_df1 = block_df1.iloc[1:]
                delete_intro = False
            final_df = pd.concat(
                [final_df, block_df1[["FULL_FILE_PATH", "BLOCK_ID"]].assign(Code="")],
                ignore_index=True
            )
            last_show_name = show_name_1

        return final_df, last_show_name, delete_intro

    def _attempt_interweave(self, idx, final_df, last_show_name, shows):
        """
        Attempt to handle "interweaving" if the next row's first show differs
        from the last_show_name. This logic appends a blank row to final_df in some cases,
        preserving the original intent of spacing or boundary between transitions.
        """
        if idx < len(self.decoded_df) - 1:
            next_row = self.decoded_df.iloc[idx + 1]
            next_code = next_row["Code"] or ""
            next_shows = next_row["shows"]
            # Insert a break if the upcoming show is different and there's no direct handoff
            if (
                next_shows[0] != last_show_name
                and not (
                    ("-NS3" in next_code and next_shows[0] == shows[-1])
                    or ("-NS2" in next_code and last_show_name == next_shows[-1])
                )
            ):
                final_df = pd.concat([final_df], ignore_index=True)
        return final_df

    def _insert_episode_block(self, final_df, show, delete_intro, last_bump_for_show):
        """
        Insert the next episode block for 'show' into final_df.
        If delete_intro is True, remove the first row of the block (the intro).
        """
        next_block = self.get_next_episode_block(show)
        if next_block is not None:
            block_df = self.commercial_injector_df[
                self.commercial_injector_df["BLOCK_ID"] == next_block["BLOCK_ID"]
            ]
            if delete_intro and not block_df.empty:
                block_df = block_df.iloc[1:]
                delete_intro = False
            final_df = pd.concat(
                [final_df, block_df[["FULL_FILE_PATH", "BLOCK_ID"]].assign(Code="")],
                ignore_index=True
            )
            last_bump_for_show[show] = final_df.index[-1]
        return final_df, delete_intro

    #####################################################
    #         GETTING & INSERTING EPISODE BLOCKS        #
    #####################################################

    def get_next_episode_block(self, show):
        """
        Return the next episode block for the specified show, taking
        into account the last used episode block if continuing. If
        reuse_episode_blocks is True and we've exhausted new blocks,
        start over from the beginning.
        """
        show_df = self.commercial_injector_df[self.commercial_injector_df["show_name"] == show]
        if show_df.empty:
            print(f"Warning: No episode blocks found for show {show}.")
            return None

        if show in self.last_used_episode_block:
            last_block_id = self.last_used_episode_block[show]
            next_blocks = show_df[show_df["BLOCK_ID"] > last_block_id]
            if next_blocks.empty:
                if self.reuse_episode_blocks:
                    print(f"No more new episode blocks for show {show}. Reusing from the beginning.")
                    next_block = show_df.iloc[0]
                else:
                    print(f"No more new episode blocks for show {show}. Skipping further scheduling.")
                    self.shows_with_no_more_blocks.add(show)
                    return None
            else:
                next_block = next_blocks.iloc[0]
        else:
            next_block = show_df.iloc[0]

        self.last_used_episode_block[show] = next_block["BLOCK_ID"]
        return next_block

    def set_reuse_episode_blocks(self, reuse):
        """
        Enable or disable reusing episode blocks once they have been exhausted.
        """
        self.reuse_episode_blocks = reuse

    #####################################################
    #           NS3 SPECIAL INDEX HANDLING             #
    #####################################################

    def get_ns3_special_indices(self, final_df):
        """
        Find indices of rows in final_df that end with -NS3 after a row that
        ends with -NS2, and they share the same show code. This is used for
        specialized logic to rearrange certain bumps.
        """
        ns3_special_indices = []
        rows_with_codes = [
            (idx, row["Code"]) for idx, row in final_df.iterrows() if row["Code"] and row["Code"].strip() != ""
        ]

        for i in range(len(rows_with_codes) - 1):
            idx, current_code = rows_with_codes[i]
            next_idx, next_code = rows_with_codes[i + 1]
            if current_code.endswith("-NS2") and next_code.endswith("-NS3"):
                # Attempt to match the same show if we want a stricter check
                current_show = re.search(r"-S1:(\w+)-", current_code)
                next_show = re.search(r"-S1:(\w+)-", next_code)
                if current_show and next_show and current_show.group(1) == next_show.group(1):
                    ns3_special_indices.append(next_idx)
        return ns3_special_indices

    def adjust_final_df_based_on_ns3_indices(self, final_df):
        """
        Adjust final_df based on the special indices found by get_ns3_special_indices
        by swapping rows or removing rows as needed.
        """
        if not self.apply_ns3_logic:
            return final_df

        self.ns3_special_indices = self.get_ns3_special_indices(final_df)

        # Attempt a simplistic approach to reordering or removing
        for index in self.ns3_special_indices:
            if (index >= 2) and (index < len(final_df)):
                # Swap the row at index with the row at index-2
                final_df.iloc[index - 2], final_df.iloc[index] = (
                    final_df.iloc[index].copy(),
                    final_df.iloc[index - 2].copy()
                )
            else:
                print(f"Skipping index {index} as it leads to out-of-bounds index {index - 2}")

        # Remove the swapped rows to handle partial transitions
        for index in sorted(self.ns3_special_indices, reverse=True):
            if index < len(final_df):
                final_df.drop(index, inplace=True)
            else:
                print(f"Skipping index {index} as it is out-of-bounds")

        final_df.reset_index(drop=True, inplace=True)
        return final_df

    #####################################################
    #        UNUSED SHOWS & ANCHOR ROWS                 #
    #####################################################

    def get_unused_shows(self):
        """
        Identify and return DataFrame rows from commercial_injector_df
        that correspond to shows not used in final_df (based on decoded_df).
        """
        used_shows = set()
        for _, row in self.decoded_df.iterrows():
            used_shows.update(row["shows"])

        all_shows = set(self.commercial_injector_df["show_name"].unique())
        unused_shows = all_shows - used_shows
        return self.commercial_injector_df[self.commercial_injector_df["show_name"].isin(unused_shows)]

    def locate_lines_of_fourth_unique_block_id(self, final_df):
        """
        Locate the row(s) in final_df just before the fourth unique BLOCK_ID
        within any sequence. This is used to anchor insertion of additional shows.
        """
        anchor_rows = []
        for idx, row in final_df.iterrows():
            if re.search(r"NS3", str(row["Code"])):
                # Find the start and end indices for the section containing the NS3 code
                start_idx = idx
                start_ns_code = None
                while start_idx >= 0:
                    if re.search(r"NS\d", str(final_df.iloc[start_idx]["Code"])):
                        start_ns_code = final_df.iloc[start_idx]["Code"]
                        break
                    start_idx -= 1

                end_idx = idx
                end_ns_code = None
                while end_idx < len(final_df):
                    if (
                        re.search(r"NS\d", str(final_df.iloc[end_idx]["Code"]))
                        and final_df.iloc[end_idx]["Code"] != start_ns_code
                    ):
                        end_ns_code = final_df.iloc[end_idx]["Code"]
                        break
                    end_idx += 1

                section_df = final_df.iloc[start_idx:end_idx]
                unique_blocks = []
                for block_id in section_df["BLOCK_ID"].dropna():
                    if block_id not in unique_blocks:
                        unique_blocks.append(block_id)

                # If there's a fourth unique block, anchor above it
                if len(unique_blocks) >= 4:
                    fourth_unique_block_id = unique_blocks[3]
                    lines_of_fourth_block = section_df.index[
                        section_df["BLOCK_ID"] == fourth_unique_block_id
                    ].tolist()

                    if lines_of_fourth_block:
                        anchor_row_index = lines_of_fourth_block[0] - 1
                        if anchor_row_index >= 0:
                            anchor_row = final_df.iloc[anchor_row_index]
                            anchor_rows.append(anchor_row)
        return anchor_rows

    def add_unused_shows_to_schedule(self, final_df, unused_shows_df, anchor_rows):
        """
        For each anchor row, pick a random unused show, insert its next block
        after the anchor.
        """
        for anchor_row in anchor_rows:
            anchor_idx_list = final_df.index[
                (final_df["FULL_FILE_PATH"] == anchor_row["FULL_FILE_PATH"])
                & (final_df["Code"] == anchor_row["Code"])
                & (final_df["BLOCK_ID"] == anchor_row["BLOCK_ID"])
            ].tolist()

            if not anchor_idx_list:
                continue

            anchor_idx = anchor_idx_list[0]
            space = anchor_idx + 1
            selected_show = random.choice(unused_shows_df["show_name"].unique())
            next_block = self.get_next_episode_block(selected_show)
            if next_block is not None:
                selected_block_df = self.commercial_injector_df[
                    self.commercial_injector_df["BLOCK_ID"] == next_block["BLOCK_ID"]
                ]
                final_df = pd.concat(
                    [final_df.iloc[:space], selected_block_df, final_df.iloc[space:]],
                    ignore_index=True
                )

                # Drop priority, show_name columns if present
                if "Priority" in final_df.columns:
                    final_df.drop(columns=["Priority", "show_name"], inplace=True, errors="ignore")
                else:
                    final_df.drop(columns=["show_name"], inplace=True, errors="ignore")

        return final_df

    #####################################################
    #            SAVE & LOAD BLOCK ID USAGE             #
    #####################################################

    def save_schedule(self, final_df, save_table):
        """
        Save the final schedule to a specified table in the DB.
        """
        print(f"Saving schedule to {save_table}")
        with self.db_manager.transaction() as conn:
            final_df.to_sql(save_table, conn, index=False, if_exists="replace")

    def save_last_used_episode_block(self):
        """
        Write the dictionary of last used blocks (show -> BLOCK_ID) to the
        last_used_episode_block table in the DB.
        """
        df = pd.DataFrame(list(self.last_used_episode_block.items()), columns=["show", "last_used_block"])
        with self.db_manager.transaction() as conn:
            df.to_sql("last_used_episode_block", conn, index=False, if_exists="replace")
        print("Last used episode blocks have been saved.")

    def load_last_used_episode_block(self):
        """
        Load the table last_used_episode_block from the DB (if it exists) and
        return a dict mapping show -> last used BLOCK_ID.
        """
        if self.db_manager.table_exists("last_used_episode_block"):
            with self.db_manager.transaction() as conn:
                df = pd.read_sql("SELECT * FROM last_used_episode_block", conn)
            return df.set_index("show")["last_used_block"].to_dict()
        else:
            print("No existing last used episode blocks found.")
            return {}
