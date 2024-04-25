import sqlite3
import ToonamiTools
import config
import threading
import time


class LogicController():
    def __init__(self):
        self.db_path = f'{config.network}.db'
        self._setup_database()
        self._new_server_choice_subscribers = []
        self._new_library_choice_subscribers = []
        self._status_update_subscribers = []
        self.plex_servers = []
        self.plex_libraries = []
        self.filter_complete_event = threading.Event()

    def _setup_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_data (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def _set_data(self, key, value):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO app_data (key, value)
                VALUES (?, ?)
            """, (key, value))
            conn.commit()

    def _get_data(self, key):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_data WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
        
    def _check_table_exists(self, table_name):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            return cursor.fetchone() is not None

    def subscribe_to_new_server_choices(self, callback):
        if callable(callback):
            self._new_server_choice_subscribers.append(callback)

    def subscribe_to_new_library_choices(self, callback):
        if callable(callback):
            self._new_library_choice_subscribers.append(callback)

    def subscribe_to_status_updates(self, callback):
        """Subscribe to status updates."""
        if callable(callback):
            self._status_update_subscribers.append(callback)

    def _broadcast_status_update(self, message):
        """Notify all subscribers about a status update."""
        for subscriber in self._status_update_subscribers:
            subscriber(message)

    def is_filtered_complete(self):
        return self.filter_complete_event.is_set()
        
    def reset_filter_event(self):
        self.filter_complete_event.clear()

    def set_filter_event(self):
        self.filter_complete_event.set()



    def login_to_plex(self):
        def login_thread():
            try:
                # Create PlexServerList instance, fetch token and populate dropdown
                self._broadcast_status_update("Logging in to Plex...")
                self.server_list = ToonamiTools.PlexServerList()
                self.server_list.run()
                self._broadcast_status_update("Plex login successful. Fetching servers...")

                # Update the list of servers
                self.plex_servers = self.server_list.plex_servers
                self._broadcast_status_update("Plex servers fetched!")

                # Announce that new server choices are available
                for subscriber in self._new_server_choice_subscribers:
                    subscriber()

            except Exception as e:
                print(f"An error occurred while logging in to Plex: {e}")

        thread = threading.Thread(target=login_thread)
        thread.start()

    def on_server_selected(self, selected_server):
        self.fetch_libraries(selected_server)

    def fetch_libraries(self, selected_server):
        def fetch_libraries_thread():
            try:
                # Create PlexLibraryManager and PlexLibraryFetcher instances
                self._broadcast_status_update(f"Fetching libraries for {selected_server}...")
                self.library_manager = ToonamiTools.PlexLibraryManager(selected_server, self.server_list.plex_token)
                self.library_manager.run()

                self.library_fetcher = ToonamiTools.PlexLibraryFetcher(self.library_manager.plex_url, self.server_list.plex_token)
                self.library_fetcher.run()

                # Update the list of libraries
                self.plex_libraries = self.library_fetcher.libraries
                self._broadcast_status_update("Libraries fetched successfully!")

                # announce that new library choices are available
                for subscriber in self._new_library_choice_subscribers:
                    subscriber()

            except Exception as e:  # Replace with more specific exceptions if known
                print(f"An error occurred while fetching libraries: {e}")

        thread = threading.Thread(target=fetch_libraries_thread)
        thread.start()

    def on_continue_first(self, selected_anime_library, selected_toonami_library, dizquetv_url):
        # Use the database value if the widget value starts with "eg. ", otherwise use the widget value

        if selected_anime_library.startswith("eg. ") or not selected_anime_library:
            selected_anime_library = self._get_data("selected_anime_library")

        if selected_toonami_library.startswith("eg. ") or not selected_toonami_library:
            selected_toonami_library = self._get_data("selected_toonami_library")

        if dizquetv_url.startswith("eg. ") or not dizquetv_url:
            dizquetv_url = self._get_data("dizquetv_url")

        plex_url = self.library_manager.plex_url
        if plex_url.startswith("eg. ") or not plex_url:
            plex_url = self._get_data("plex_url")

        plex_token = self.library_manager.plex_token
        if plex_token.startswith("eg. ") or not plex_token:
            plex_token = self._get_data("plex_token")

        # Save the fetched data to the database
        self._set_data("selected_anime_library", selected_anime_library)
        self._set_data("selected_toonami_library", selected_toonami_library)
        self._set_data("plex_url", plex_url)
        self._set_data("plex_token", plex_token)
        self._set_data("dizquetv_url", dizquetv_url)

        # Optional: Print values for verification
        print(selected_anime_library, selected_toonami_library, plex_url, plex_token, dizquetv_url)
        self._broadcast_status_update("Idle")

    def on_continue_second(self, selected_anime_library, selected_toonami_library, plex_url, plex_token, dizquetv_url):
        # Check each widget value, if it starts with "eg. ", fetch the value from the database

        if selected_anime_library.startswith("eg. ") or not selected_anime_library:
            selected_anime_library = self._get_data("selected_anime_library")

        if selected_toonami_library.startswith("eg. ") or not selected_toonami_library:
            selected_toonami_library = self._get_data("selected_toonami_library")

        if plex_url.startswith("eg. ") or not plex_url:
            plex_url = self._get_data("plex_url")

        if plex_token.startswith("eg. ") or not plex_token:
            plex_token = self._get_data("plex_token")

        if dizquetv_url.startswith("eg. ") or not dizquetv_url:
            dizquetv_url = self._get_data("dizquetv_url")

        # Save the fetched data to the database
        self._set_data("selected_anime_library", selected_anime_library)
        self._set_data("selected_toonami_library", selected_toonami_library)
        self._set_data("plex_url", plex_url)
        self._set_data("plex_token", plex_token)
        self._set_data("dizquetv_url", dizquetv_url)

        # Optional: Print values for verification
        print(selected_anime_library, selected_toonami_library, plex_url, plex_token, dizquetv_url)
        self._broadcast_status_update("Idle")

    def on_continue_third(self, anime_folder, bump_folder, special_bump_folder, working_folder):
        # Check each widget value, if it's blank, fetch the value from the database
        if not anime_folder:
            anime_folder = self._get_data("anime_folder")

        if not bump_folder:
            bump_folder = self._get_data("bump_folder")

        if not special_bump_folder:
            special_bump_folder = self._get_data("special_bump_folder")

        if not working_folder:
            working_folder = self._get_data("working_folder")

        # Save the fetched data to the database
        self._set_data("anime_folder", anime_folder)
        self._set_data("bump_folder", bump_folder)
        self._set_data("special_bump_folder", special_bump_folder)
        self._set_data("working_folder", working_folder)

        # Optional: Print values for verification
        print(anime_folder, bump_folder, special_bump_folder, working_folder)
        self._broadcast_status_update("Idle")

    def on_continue_fourth(self):
        self._broadcast_status_update("Idle")

    def on_continue_fifth(self):
        self._broadcast_status_update("Idle")

    def on_continue_sixth(self):
        self._broadcast_status_update("Idle")

    def on_continue_seventh(self):
        self._broadcast_status_update("Idle")

    def prepare_content(self, display_show_selection):
        def prepare_content_thread():
            # Update the values based on the current state of the checkboxes
            self._broadcast_status_update("Preparing bumps...")
            working_folder = self._get_data("working_folder")
            anime_folder = self._get_data("anime_folder")
            bump_folder = self._get_data("bump_folder")
            merger_bumps_list_1 = 'multibumps_v2_data_reordered'
            merger_bumps_list_2 = 'multibumps_v3_data_reordered'
            merger_bumps_list_3 = 'multibumps_v9_data_reordered'
            merger_bumps_list_4 = 'multibumps_v8_data_reordered'
            merger_out_1 = 'lineup_v2_uncut'
            merger_out_2 = 'lineup_v3_uncut'
            merger_out_3 = 'lineup_v9_uncut'
            merger_out_4 = 'lineup_v8_uncut'
            uncut_encoder_out = 'uncut_encoded_data'
            fmaker = ToonamiTools.FolderMaker(working_folder)
            easy_checker = ToonamiTools.ToonamiChecker(anime_folder)
            lineup_prep = ToonamiTools.MediaProcessor(bump_folder)
            easy_encoder = ToonamiTools.ToonamiEncoder()
            uncutencoder = ToonamiTools.UncutEncoder()
            ml = ToonamiTools.Multilineup()
            merger = ToonamiTools.ShowScheduler(uncut=True)
            fmaker.run()
            unique_show_names, toonami_episodes = easy_checker.prepare_episode_data()
            self._broadcast_status_update("Waiting for selection...")
            selected_shows = display_show_selection(unique_show_names)
            easy_checker.process_selected_shows(selected_shows, toonami_episodes)
            self._broadcast_status_update("Preparing uncut lineup...")
            lineup_prep.run()
            easy_encoder.encode_and_save()
            ml.reorder_all_tables()
            uncutencoder.run()
            merger.run(merger_bumps_list_1, uncut_encoder_out, merger_out_1)
            merger.run(merger_bumps_list_2, uncut_encoder_out, merger_out_2)
            merger.run(merger_bumps_list_3, uncut_encoder_out, merger_out_3)
            merger.run(merger_bumps_list_4, uncut_encoder_out, merger_out_4)
            self._broadcast_status_update("Content preparation complete!")
        thread = threading.Thread(target=prepare_content_thread)
        thread.start()

    def move_filtered(self):
        def move_filtered_thread():
            self._broadcast_status_update("Moving filtered shows...")
            fmove = ToonamiTools.FilterAndMove()
            working_folder = self._get_data("working_folder")
            filter_output_folder = working_folder + "/toonami_filtered/"
            fmove.run(filter_output_folder)
            self._broadcast_status_update("Filtered shows moved!")
            self.filter_complete_event.set()
        thread = threading.Thread(target=move_filtered_thread)
        thread.start()

    def get_plex_timestamps(self):
        def get_plex_timestamps_thread():
            self._broadcast_status_update("Getting Timestamps from Plex...")
            working_folder = self._get_data("working_folder")
            toonami_filtered_folder = working_folder + "/toonami"
            plex_ts_url = self._get_data("plex_url")
            plex_ts_token = self._get_data("plex_token")
            plex_ts_anime_library_name = self._get_data("selected_anime_library")
            GetTimestamps = ToonamiTools.GetPlexTimestamps(plex_ts_url, plex_ts_token, plex_ts_anime_library_name, toonami_filtered_folder)
            GetTimestamps.run()  # Calling the run method on the instance
            self._broadcast_status_update("Plex timestamps fetched!")

        thread = threading.Thread(target=get_plex_timestamps_thread)
        thread.start()

    def prepare_cut_anime(self):
        def prepare_cut_anime_thread():
            working_folder = self._get_data("working_folder")
            self._broadcast_status_update("Preparing cut anime...")
            merger_bumps_list_1 = 'multibumps_v2_data_reordered'
            merger_bumps_list_2 = 'multibumps_v3_data_reordered'
            merger_bumps_list_3 = 'multibumps_v9_data_reordered'
            merger_bumps_list_4 = 'multibumps_v8_data_reordered'
            merger_out_1 = 'lineup_v2'
            merger_out_2 = 'lineup_v3'
            merger_out_3 = 'lineup_v9'
            merger_out_4 = 'lineup_v8'
            commercial_injector_out = 'commercial_injector_final'
            cut_folder = working_folder + "/cut"
            commercial_injector_prep = ToonamiTools.AnimeFileOrganizer(cut_folder)
            commercial_injector = ToonamiTools.LineupLogic()
            BIC = ToonamiTools.BlockIDCreator()
            merger = ToonamiTools.ShowScheduler(apply_ns3_logic=True)
            commercial_injector_prep.organize_files()
            commercial_injector.generate_lineup()
            BIC.run()
            self._broadcast_status_update("Creating your lineup...")
            merger.run(merger_bumps_list_1, commercial_injector_out, merger_out_1)
            merger.run(merger_bumps_list_2, commercial_injector_out, merger_out_2)
            merger.run(merger_bumps_list_3, commercial_injector_out, merger_out_3)
            merger.run(merger_bumps_list_4, commercial_injector_out, merger_out_4)
            self._broadcast_status_update("Cut anime preparation complete!")

        thread = threading.Thread(target=prepare_cut_anime_thread)
        thread.start()

    def add_special_bumps(self):
        special_bump_folder = self._get_data("special_bump_folder")
        sepcial_bump_processor = ToonamiTools.FileProcessor(special_bump_folder)
        sepcial_bump_processor.process_files()

    def create_prepare_plex(self):
        def prepare_plex_thread():
            self._broadcast_status_update("Preparing Plex...")
            plex_url_plex_splitter = self._get_data("plex_url")
            plex_token_plex_splitter = self._get_data("plex_token")
            plex_library_name_plex_splitter = self._get_data("selected_toonami_library")
            self._broadcast_status_update("Splitting merged Plex shows...")
            plex_splitter = ToonamiTools.PlexAutoSplitter(plex_url_plex_splitter, plex_token_plex_splitter, plex_library_name_plex_splitter)
            plex_splitter.split_merged_items()
            self._broadcast_status_update("Renaming Plex shows...")
            plex_rename_split = ToonamiTools.PlexLibraryUpdater(plex_url_plex_splitter, plex_token_plex_splitter, plex_library_name_plex_splitter)
            plex_rename_split.update_titles()
            self._broadcast_status_update("Plex preparation complete!")
            self.filter_complete_event.set()
        thread = threading.Thread(target=prepare_plex_thread)
        thread.start()

    def create_toonami_channel(self, toonami_version, channel_number):
        def create_toonami_channel_thread():
            self._broadcast_status_update("Creating Toonami channel...")
            plex_url = self._get_data("plex_url")
            plex_token = self._get_data("plex_token")
            plex_library_name = self._get_data("selected_toonami_library")
            toon_config = config.TOONAMI_CONFIG.get(toonami_version, {})
            table = toon_config["table"]
            dizquetv_url = self._get_data("dizquetv_url")
            ptod = ToonamiTools.PlexToDizqueTVSimplified(plex_url, plex_token, plex_library_name, table, dizquetv_url, channel_number)
            ptod.run()
            self._broadcast_status_update("Toonami channel created!")
            self.filter_complete_event.set()
        thread = threading.Thread(target=create_toonami_channel_thread)
        thread.start()

    def prepare_toonami_channel(self, start_from_last_episode, toonami_version):

        def prepare_toonami_channel_thread():
            self._broadcast_status_update("Preparing Toonami channel...")
            cont_config = config.TOONAMI_CONFIG_CONT.get(toonami_version, {})

            merger_bump_list = cont_config["merger_bump_list"]
            merger_out = cont_config["merger_out"]
            encoder_in = cont_config["encoder_in"]
            uncut = cont_config["uncut"]

            merger = ToonamiTools.ShowScheduler(reuse_episode_blocks=True, continue_from_last_used_episode_block=start_from_last_episode, uncut=uncut)
            merger.run(merger_bump_list, encoder_in, merger_out)
            self._broadcast_status_update("Toonami channel prepared!")
            self.filter_complete_event.set()
        thread = threading.Thread(target=prepare_toonami_channel_thread)
        thread.start()

    def create_toonami_channel_cont(self, toonami_version, channel_number):
        self._broadcast_status_update("Creating new Toonami channel...")
        cont_config = config.TOONAMI_CONFIG_CONT.get(toonami_version, {})
        table = cont_config["merger_out"]
        dizquetv_url = self._get_data("dizquetv_url")
        plex_url = self._get_data("plex_url")
        plex_token = self._get_data("plex_token")
        plex_library_name = self._get_data("selected_toonami_library")

        ptod = ToonamiTools.PlexToDizqueTVSimplified(plex_url, plex_token, plex_library_name, table, dizquetv_url, channel_number)
        ptod.run()
        self._broadcast_status_update("New Toonami channel created!")
        self.filter_complete_event.set()


    def add_flex_creds(self, ssh_host, ssh_user, ssh_pass, dizquetv_container_name, dizquetv_channel_number, dizquetv_flex_duration):
        # Attempt to retrieve data from the database
        if not ssh_host or ssh_host.startswith("eg. "):
            ssh_host = self._get_data("ssh_host")
        if not ssh_user or ssh_user.startswith("eg. "):
            ssh_user = self._get_data("ssh_user")
        if not ssh_pass or ssh_pass.startswith("eg. "):
            ssh_pass = self._get_data("ssh_pass")
        if not dizquetv_container_name or dizquetv_container_name.startswith("eg. "):
            dizquetv_container_name = self._get_data("dizquetv_container_name")
        if not dizquetv_channel_number or dizquetv_channel_number.startswith("eg. "):
            dizquetv_channel_number = self._get_data("dizquetv_channel_number")
        if not dizquetv_flex_duration or dizquetv_flex_duration.startswith("eg. "):
            dizquetv_flex_duration = self._get_data("dizquetv_flex_duration")

        # Save the fetched data to the database
        self._set_data("ssh_host", ssh_host)
        self._set_data("ssh_user", ssh_user)
        self._set_data("ssh_pass", ssh_pass)
        self._set_data("dizquetv_container_name", dizquetv_container_name)
        self._set_data("dizquetv_channel_number", dizquetv_channel_number)
        self._set_data("dizquetv_flex_duration", dizquetv_flex_duration)

    def add_flex(self):
        def add_flex_thread():
            self._broadcast_status_update("Adding Flex...")
            ssh_host = self._get_data("ssh_host")
            ssh_user = self._get_data("ssh_user")
            ssh_pass = self._get_data("ssh_pass")
            dizquetv_container_name = self._get_data("dizquetv_container_name")
            dizquetv_channel_number = self._get_data("dizquetv_channel_number")
            dizquetv_flex_duration = self._get_data("dizquetv_flex_duration")
            Flex = ToonamiTools.DizqueTVManager(ssh_host, ssh_user, ssh_pass, dizquetv_container_name, dizquetv_channel_number, dizquetv_flex_duration)
            Flex.main()
            self._broadcast_status_update("Flex added!")
            self.filter_complete_event.set()

        thread = threading.Thread(target=add_flex_thread)
        thread.start()