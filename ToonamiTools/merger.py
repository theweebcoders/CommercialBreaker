import pandas as pd
import random
import sqlite3
from config import *
import re

class ShowScheduler:
    def __init__(self, reuse_episode_blocks=True, continue_from_last_used_episode_block=False, apply_ns3_logic=False, uncut=False):
        self.conn = sqlite3.connect('toonami.db')
        if continue_from_last_used_episode_block == True:
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name='last_used_episode_block';"
            if self.conn.execute(query).fetchone():
                self.last_used_episode_block = self.load_last_used_episode_block()
                print("Continuing from last used episode blocks")
            else:
                self.last_used_episode_block = {}
                print("Resetting episode tracking for the last spreadsheet.")
        else:
                self.last_used_episode_block = {}
                print("Resetting episode tracking for the last spreadsheet.")
        self.last_spreadsheet = None
        self.encoder_df = None
        self.commercial_injector_df = None
        self.decoder = None
        self.decoded_df = None
        self.show_episode_blocks = None
        self.reuse_episode_blocks = True # Step 1
        self.shows_with_no_more_blocks = set() # Step 1
        self.continue_from_last_used_episode_block = continue_from_last_used_episode_block
        self.ns3_special_indices = []  # Initialize the list to store specific indices for NS3 bumps that follow NS2 bumps and flow
        self.apply_ns3_logic = apply_ns3_logic
        self.uncut = uncut

    def set_paths(self, encoder_table, commercial_table):
        print("Setting file paths...")
        print("Loading encoder data from", encoder_table)
        print("Loading commercial injector data from", commercial_table)
        print("Loading codes from codes")
        self.conn = sqlite3.connect('toonami.db')
        self.encoder_df = pd.read_sql(f'SELECT * FROM {encoder_table}', self.conn)
        self.commercial_injector_df = pd.read_sql(f'SELECT * FROM {commercial_table}', self.conn)
        self.commercial_injector_df['show_name'] = self.commercial_injector_df['BLOCK_ID'].str.rsplit(pat='_S', n=1).str[0].str.replace('_', ' ').str.lower()
        self._load_codes()
        self.decoded_df = self._decode_shows()
        self._normalize_show_names()
        self.show_episode_blocks = self._group_shows()

    def _load_codes(self):
        print("Loading codes...")
        codes_df = pd.read_sql('SELECT * FROM codes', self.conn)
        self.decoder = {row['Code']: row['Name'].lower() for index, row in codes_df.iterrows()}

    def _decode_shows(self):
        print("Decoding shows...")
        decoded_df = self.encoder_df.copy()
        decoded_df['shows'] = decoded_df['Code'].apply(self._extract_show_codes)
        return decoded_df

    def _normalize_show_names(self):
        self.decoded_df['shows'] = self.decoded_df['shows'].apply(lambda shows: [self._normalize_show_name(show) for show in shows])
        self.commercial_injector_df['show_name'] = self.commercial_injector_df['show_name'].apply(self._normalize_show_name)

    def _normalize_show_name(self, show):
        normalized_show = show_name_mapping.get(show.lower(), show)
        return normalized_show

    def _extract_show_codes(self, code):
        parts = code.split('-')
        show_codes = [part.split(':')[1] for part in parts if part.startswith('S')]
        decoded_show_codes = [self.decoder[show_code] for show_code in show_codes]
        return decoded_show_codes

    def _group_shows(self):
        return self.commercial_injector_df.groupby('show_name').apply(lambda x: x.groupby('BLOCK_ID').apply(lambda y: y[["FULL_FILE_PATH", "BLOCK_ID"]].values.tolist()).values.tolist()).to_dict()

    def get_next_episode_block(self, show):
        show_name_in_df = show
        show_df = self.commercial_injector_df[self.commercial_injector_df["show_name"] == show_name_in_df]

        if show_df.empty:
            print(f"Warning: No episode blocks found for show {show}.")
            return None

        if show in self.last_used_episode_block:
            last_block = self.last_used_episode_block[show]
            next_blocks = show_df[show_df["BLOCK_ID"] > last_block]
            if next_blocks.empty:
                if self.reuse_episode_blocks:
                    print(f"No more new episode blocks for show {show}. Reusing from the beginning.")
                    next_block = show_df.iloc[0]
                else:
                    print(f"No more new episode blocks for show {show}. Skipping further scheduling for this show.")
                    self.shows_with_no_more_blocks.add(show)
                    return None
            else:
                next_block = next_blocks.iloc[0]
        else:
            next_block = show_df.iloc[0]

        self.last_used_episode_block[show] = next_block["BLOCK_ID"]
        return next_block

    def get_unused_shows(self):
        # Get the shows that are actually used in final_df based on decoded_df
        used_shows = set()
        for idx, row in self.decoded_df.iterrows():
            used_shows.update(row["shows"])
        
        # Get all unique shows in commercial_injector_df
        all_shows = set(self.commercial_injector_df['show_name'].unique())
        
        # Identify and print unused shows
        unused_shows = all_shows - used_shows

        # add 
        unused_shows_df = self.commercial_injector_df[self.commercial_injector_df['show_name'].isin(unused_shows)]
        return unused_shows_df

    def locate_lines_of_fourth_unique_block_id(self, final_df):
        anchor_rows = []
        for idx, row in final_df.iterrows():
            if re.search(r'NS3', str(row['Code'])):  # If an NS3 code is found
                # Initialize and find the starting NS code
                start_idx = idx
                start_ns_code = None
                while start_idx >= 0:
                    if re.search(r'NS\d', str(final_df.iloc[start_idx]['Code'])):
                        start_ns_code = final_df.iloc[start_idx]['Code']
                        break
                    start_idx -= 1
                
                # Initialize and find the ending NS code
                end_idx = idx
                end_ns_code = None
                while end_idx < len(final_df):
                    if re.search(r'NS\d', str(final_df.iloc[end_idx]['Code'])) and final_df.iloc[end_idx]['Code'] != start_ns_code:
                        end_ns_code = final_df.iloc[end_idx]['Code']
                        break
                    end_idx += 1

                # Sequence through episode blocks in this section
                section_df = final_df.iloc[start_idx:end_idx]
                unique_blocks = []
                for block_id in section_df['BLOCK_ID'].dropna():
                    if block_id not in unique_blocks:
                        unique_blocks.append(block_id)
                
                # Find the fourth unique Block_ID if it exists
                fourth_unique_block_id = unique_blocks[3] if len(unique_blocks) >= 4 else None
                
                if fourth_unique_block_id:
                    # Find the lines (indices) where this fourth unique Block_ID appears in the section
                    lines_of_fourth_block = section_df.index[section_df['BLOCK_ID'] == fourth_unique_block_id].tolist()
                    
                    if lines_of_fourth_block:
                        # Capture the row just above the first line of the fourth unique block as the anchor row
                        anchor_row = final_df.iloc[lines_of_fourth_block[0] - 1]
                        anchor_rows.append(anchor_row)
                
        return anchor_rows


    def add_unused_shows_to_schedule(self, final_df, unused_shows_df, anchor_rows):
        for anchor_row in anchor_rows:
            # Find the index of the anchor row in the current DataFrame
            anchor_idx = final_df.index[
                (final_df['FULL_FILE_PATH'] == anchor_row['FULL_FILE_PATH']) & 
                (final_df['Code'] == anchor_row['Code']) & 
                (final_df['BLOCK_ID'] == anchor_row['BLOCK_ID'])
            ].tolist()[0]
            
            space = anchor_idx + 1 
            # Select an unused show randomly
            selected_show = random.choice(unused_shows_df['show_name'].unique())
            
            # Use the get_next_episode_block method to get the next block for the selected show
            next_block = self.get_next_episode_block(selected_show)
            
            if next_block is not None:
                # Fetch the episode block details for the next block
                selected_block_df = self.commercial_injector_df[
                    self.commercial_injector_df['BLOCK_ID'] == next_block["BLOCK_ID"]
                ]

                # Insert the episode block details into the DataFrame
                final_df = pd.concat([final_df.iloc[:space], selected_block_df, final_df.iloc[space:]]).reset_index(drop=True)
                #drop priorty and show name ccolumns
                if 'Priority' in final_df.columns:
                    final_df.drop(columns=['Priority', 'show_name'], inplace=True)
                else:
                    final_df.drop(columns=['show_name'], inplace=True)
        
        return final_df


    def generate_schedule(self):
        print("Generating schedule...")
        final_df = pd.DataFrame(columns=["FULL_FILE_PATH", "Code", "BLOCK_ID"])
        last_show_name = None
        delete_intro = False
        last_bump_for_show = {}  # To keep track of the last bump that used a show
        skip_first_show = False  # A flag to decide whether to skip the first show or not

        for idx, row in self.decoded_df.iterrows():
            shows = row["shows"]

            if self.apply_ns3_logic and idx > 0 and "-NS3" in row["Code"] and "-NS2" in self.decoded_df.iloc[idx - 1]["Code"]:
                previous_ns2_show = self.decoded_df.iloc[idx - 1]["shows"][0]
                current_ns3_show = shows[0]
                if previous_ns2_show == current_ns3_show:
                    skip_first_show = True

            if all(show not in self.shows_with_no_more_blocks for show in shows):
                if "-NS3" in row["Code"]:
                    final_df = pd.concat([final_df, pd.DataFrame([row[["FULL_FILE_PATH", "Code"]].to_dict()])], ignore_index=True)
                    if skip_first_show:
                        special_index = final_df.index[-1] 
                        self.ns3_special_indices.append(special_index)  # Append the index to the list
                    # Set delete_intro flag to True for NS3, unless specific scenario is matched
                    if not skip_first_show:
                        delete_intro = True
                    
                    # If there's a next -NS3 bump, and its first show matches the current last show
                    if idx < len(self.decoded_df) - 1 and "-NS3" in self.decoded_df.iloc[idx + 1]["Code"] and self.decoded_df.iloc[idx + 1]["shows"][0] == shows[-1]:
                        shows_to_place = shows[:-1]
                    else:
                        shows_to_place = shows

                    # If the current NS3 bump had the condition with NS2 bump matched
                    if skip_first_show:
                        shows_to_place = shows_to_place[1:]
                        skip_first_show = False

                    for show in shows_to_place:
                        next_block = self.get_next_episode_block(show)
                        if next_block is not None:
                            episode_blocks = self.commercial_injector_df[self.commercial_injector_df["BLOCK_ID"] == next_block["BLOCK_ID"]]
                            if delete_intro:
                                episode_blocks = episode_blocks.iloc[1:]
                                delete_intro = False
                            final_df = pd.concat([final_df, episode_blocks[["FULL_FILE_PATH", "BLOCK_ID"]].assign(Code="")], ignore_index=True)
                            last_show_name = show
                            last_bump_for_show[show] = final_df.index[-1]  # Track the last bump for this show

                elif "-NS2" in row["Code"]:
                    show_name_1, show_name_2 = shows
                    if last_show_name != show_name_2:
                        next_block = self.get_next_episode_block(show_name_2)
                        if next_block is not None:
                            episode_blocks = self.commercial_injector_df[self.commercial_injector_df["BLOCK_ID"] == next_block["BLOCK_ID"]]
                            final_df = pd.concat([final_df, episode_blocks[["FULL_FILE_PATH", "BLOCK_ID"]].assign(Code="")], ignore_index=True)
                            last_show_name = show_name_2
                    final_df = pd.concat([final_df, pd.DataFrame([row[["FULL_FILE_PATH", "Code"]].to_dict()])], ignore_index=True)
                    delete_intro = True
                    next_block = self.get_next_episode_block(show_name_1)
                    if next_block is not None:
                        episode_blocks = self.commercial_injector_df[self.commercial_injector_df["BLOCK_ID"] == next_block["BLOCK_ID"]]
                        if delete_intro:
                            episode_blocks = episode_blocks.iloc[1:]
                            delete_intro = False
                        final_df = pd.concat([final_df, episode_blocks[["FULL_FILE_PATH", "BLOCK_ID"]].assign(Code="")], ignore_index=True)
                        last_show_name = show_name_1

                if idx < len(self.decoded_df) - 1:
                    next_row = self.decoded_df.iloc[idx + 1]
                    next_shows = next_row["shows"]
                    #we do interweaving from here
                    if next_shows[0] != last_show_name and not (
                        ("-NS3" in next_row["Code"] and next_shows[0] == shows[-1]) or
                        ("-NS2" in next_row["Code"] and last_show_name == next_shows[1])
                    ):
                        final_df = pd.concat([final_df], ignore_index=True)
                    #to here
            else:
                print(f"Skipping bump for show(s) {shows} as episode blocks have run out.")
                for show in shows:
                    if show in self.shows_with_no_more_blocks:
                        last_bump_idx = last_bump_for_show.get(show)
                        if last_bump_idx is not None:
                            print(f"Removing bump for show {show} that just ran out.")
                            final_df.drop(index=last_bump_idx, inplace=True)
                            final_df.reset_index(drop=True, inplace=True)  # Reset index after drop

        print("Schedule generation complete.")
        return final_df

    def get_ns3_special_indices(self):  # Method to retrieve the list
        return self.ns3_special_indices
    
    def adjust_final_df_based_on_ns3_indices(self, final_df):
        if not self.apply_ns3_logic:
            return final_df

        for index in self.ns3_special_indices:
            # Ensure that we're not accessing a row less than 0.
            if index >= 2 and index < len(final_df):
                final_df.iloc[index - 2] = final_df.iloc[index].copy()
            else:
                print(f"Skipping index {index} as it leads to out-of-bounds index {index - 2}")

        # Delete rows while avoiding index complications
        for index in sorted(self.ns3_special_indices, reverse=True):
            # Ensure that we're not accessing a row beyond the length of the dataframe.
            if index < len(final_df):
                final_df.drop(index, inplace=True)
            else:
                print(f"Skipping index {index} as it is out-of-bounds")

        final_df.reset_index(drop=True, inplace=True)
        return final_df


    def set_reuse_episode_blocks(self, reuse):
        self.reuse_episode_blocks = reuse

    def save_schedule(self, final_df, save_table):
        print("Saving schedule to", save_table)
        final_df.to_sql(save_table, self.conn, index=False, if_exists='replace')

    def save_last_used_episode_block(self):
        df = pd.DataFrame(list(self.last_used_episode_block.items()), columns=['show', 'last_used_block'])
        df.to_sql('last_used_episode_block', self.conn, index=False, if_exists='replace')
        print("Last used episode blocks have been saved.")

        
    def load_last_used_episode_block(self):
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name='last_used_episode_block';"
        if self.conn.execute(query).fetchone():
            df = pd.read_sql('SELECT * FROM last_used_episode_block', self.conn)
            return df.set_index('show')['last_used_block'].to_dict()
        else:
            print("No existing last used episode blocks found.")
            return None

    def run(self, encoder_table, commercial_table, save_table):
        if "multi" in encoder_table.lower() and self.continue_from_last_used_episode_block == False:
            self.last_used_episode_block = {}
            print("Resetting episode tracking for the last spreadsheet.")

        print("Running the show scheduler...")
        self.set_paths(encoder_table, commercial_table)
        if not self.encoder_df['Code'].str.contains('-NS2').any() or self.uncut:
            self.apply_ns3_logic = False
            print("No NS2 bumps found. Skipping NS3 logic.")
        else:
            self.apply_ns3_logic = True
            print("NS2 bumps found. Applying NS3 logic.")
        final_df = self.generate_schedule()
        
        # Adjust the final_df based on the special -NS3 indices
        final_df = self.adjust_final_df_based_on_ns3_indices(final_df)

        if self.continue_from_last_used_episode_block == True:
            unused_shows_df = self.get_unused_shows()
            
            # Check if the DataFrame is effectively empty
            if unused_shows_df.empty or len(unused_shows_df.index) == 0:
                print("No unused shows available. Skipping related operations.")
            else:
                anchor_rows = self.locate_lines_of_fourth_unique_block_id(final_df)
                final_df = self.add_unused_shows_to_schedule(final_df, unused_shows_df, anchor_rows)

        self.save_schedule(final_df, save_table)
        
        if self.continue_from_last_used_episode_block == True:
            self.save_last_used_episode_block()
            print("Last used episode blocks have been saved.")
        
        print("Schedule successfully saved to", save_table)