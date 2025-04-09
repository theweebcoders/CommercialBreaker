import sqlite3
import redis
import ToonamiTools
import config
import threading
import time
import json
from queue import Queue
import sys

class LogicController():
    # Initialize the use_redis class variable before the init method
    use_redis = '--use_redis' in sys.argv or '--webui' in sys.argv or '--clydes' in sys.argv
    docker = '--docker' in sys.argv


    def __init__(self):
        self.db_path = f'{config.network}.db'
        self._setup_database()
        self.use_redis = self.__class__.use_redis  # Use class variable
        self.docker = self.__class__.docker
        if self.use_redis:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        else:
            # Else
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

    if use_redis:
        # If Redis is used, include the following
        def _publish_status_update(self, channel, message):
            self.redis_client.publish(channel, message)

        def _broadcast_status_update(self, message):
            """Publish status update to Redis channel."""
            self.redis_client.publish('status_updates', message)

        def publish_plex_servers(self):
            plex_servers_json = json.dumps(self.plex_servers)
            self._publish_status_update('plex_servers', plex_servers_json)

        def publish_plex_libaries(self):
            plex_libraries_json = json.dumps(self.plex_libraries)
            self._publish_status_update('plex_libraries', plex_libraries_json)

        def get_token(self):
            plex_token = self._get_data("plex_token")
            return plex_token
    else:
        # Else
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
                print("Logging in to Plex...")
                # Create PlexServerList instance, fetch token and populate dropdown
                self._broadcast_status_update("Logging in to Plex...")
                self.server_list = ToonamiTools.PlexServerList()
                self.server_list.run()
                self._broadcast_status_update("Plex login successful. Fetching servers...")
                # Update the list of servers
                self.plex_servers, plex_token = self.server_list.plex_servers, self.server_list.plex_token
                self._set_data("plex_token", plex_token)
                self._broadcast_status_update("Plex servers fetched!")

                # Announce that new server choices are available
                if self.use_redis:
                    self._publish_status_update("new_server_choices", "new_server_choices")
                    self.publish_plex_servers()
                else:
                    for subscriber in self._new_server_choice_subscribers:
                        subscriber(self.plex_servers)
                        print(self.plex_servers)

            except Exception as e:
                print(f"An error occurred while logging in to Plex: {e}")

        thread = threading.Thread(target=login_thread)
        thread.start()

    def on_server_selected(self, selected_server):
        self.fetch_libraries(selected_server)

 # There are Two versions of fetch_libraries depending on if it is with or without redis
    if use_redis:
        # If using Redis, include the following
        def fetch_libraries(self, selected_server):
            def fetch_libraries_thread():
                try:
                    # Create PlexLibraryManager and PlexLibraryFetcher instances
                    self._broadcast_status_update(f"Fetching libraries for {selected_server}...")
                    plex_token = self.get_token()
                    if plex_token is None:
                        raise Exception("Could not fetch Plex Token")
                    else:
                        self.library_manager = ToonamiTools.PlexLibraryManager(selected_server, plex_token)
                        plex_url = self.library_manager.run()
                        self._set_data("plex_url", plex_url)
                        if plex_url is None:
                            raise Exception("Could not fetch Plex URL")
                        else:
                            self.library_fetcher = ToonamiTools.PlexLibraryFetcher(plex_url, plex_token)
                            self.library_fetcher.run()

                            # Update the list of libraries
                            self.plex_libraries = self.library_fetcher.libraries
                            self._broadcast_status_update("Libraries fetched successfully!")

                            # Announce that new library choices are available
                            self._publish_status_update("new_library_choices", "new_library_choices")
                            self.publish_plex_libaries()

                except Exception as e:  # Replace with more specific exceptions if known
                    print(f"An error occurred while fetching libraries: {e}")

            thread = threading.Thread(target=fetch_libraries_thread)
            thread.start()
    else:
        # Else use the following
        def fetch_libraries(self, selected_server):
            def fetch_libraries_thread():
                try:
                    # Create PlexLibraryManager and PlexLibraryFetcher instances
                    self._broadcast_status_update(f"Fetching libraries for {selected_server}...")
                    self.library_manager = ToonamiTools.PlexLibraryManager(selected_server, self.server_list.plex_token)
                    plex_url = self.library_manager.run()
                    self._set_data("plex_url", plex_url)  # Add this line
                    
                    self.library_fetcher = ToonamiTools.PlexLibraryFetcher(self.library_manager.plex_url, self.server_list.plex_token)
                    self.library_fetcher.run()

                    # Update the list of libraries
                    self.plex_libraries = self.library_fetcher.libraries
                    self._broadcast_status_update("Libraries fetched successfully!")

                    # Announce that new library choices are available
                    for subscriber in self._new_library_choice_subscribers:
                        subscriber()

                except Exception as e:  # Replace with more specific exceptions if known
                    print(f"An error occurred while fetching libraries: {e}")

            thread = threading.Thread(target=fetch_libraries_thread)
            thread.start()

    def on_continue_first(self, selected_anime_library, selected_toonami_library, platform_url, platform_type='dizquetv'):
        """
        Updated to handle a single platform URL and its type
        """
        if selected_anime_library.startswith("eg. ") or not selected_anime_library:
            selected_anime_library = self._get_data("selected_anime_library")

        if selected_toonami_library.startswith("eg. ") or not selected_toonami_library:
            selected_toonami_library = self._get_data("selected_toonami_library")

        if platform_url.startswith("eg. ") or not platform_url:
            platform_url = self._get_data("platform_url")
        
        # Save the fetched data to the database
        self._set_data("selected_anime_library", selected_anime_library)
        self._set_data("selected_toonami_library", selected_toonami_library)
        self._set_data("platform_url", platform_url)
        self._set_data("platform_type", platform_type)

        print("Saved values:")
        print(f"Anime Library: {selected_anime_library}")
        print(f"Toonami Library: {selected_toonami_library}")
        print(f"Plex URL: {self._get_data('plex_url')}")
        print(f"Platform URL: {platform_url} ({platform_type})")
        
        self._broadcast_status_update("Idle")

    def on_continue_second(self, selected_anime_library, selected_toonami_library, plex_url, plex_token, platform_url, platform_type='dizquetv'):
        # Check each widget value, if it starts with "eg. ", fetch the value from the database
        if selected_anime_library.startswith("eg. ") or not selected_anime_library:
            selected_anime_library = self._get_data("selected_anime_library")
        if selected_toonami_library.startswith("eg. ") or not selected_toonami_library:
            selected_toonami_library = self._get_data("selected_toonami_library")
        if plex_url.startswith("eg. ") or not plex_url:
            plex_url = self._get_data("plex_url")
        if plex_token.startswith("eg. ") or not plex_token:
            plex_token = self._get_data("plex_token")
        if platform_url.startswith("eg. ") or not platform_url:
            platform_url = self._get_data("platform_url")

        # Save the fetched data to the database
        self._set_data("selected_anime_library", selected_anime_library)
        self._set_data("selected_toonami_library", selected_toonami_library)
        self._set_data("plex_url", plex_url)
        self._set_data("plex_token", plex_token)
        self._set_data("platform_url", platform_url)
        self._set_data("platform_type", platform_type)

        # Optional: Print values for verification
        print(selected_anime_library, selected_toonami_library, plex_url, plex_token, platform_url, platform_type)
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
        """
        Create a Toonami channel using the stored platform settings
        """
        def create_toonami_channel_thread():
            self._broadcast_status_update("Creating Toonami channel...")
            plex_url = self._get_data("plex_url")
            plex_token = self._get_data("plex_token")
            plex_library_name = self._get_data("selected_toonami_library")
            platform_url = self._get_data("platform_url")
            platform_type = self._get_data("platform_type")
            toon_config = config.TOONAMI_CONFIG.get(toonami_version, {})
            table = toon_config["table"]

            if platform_type == 'dizquetv':
                ptod = ToonamiTools.PlexToDizqueTVSimplified(
                    plex_url, plex_token, plex_library_name, table, 
                    platform_url, channel_number
                )
                ptod.run()
            else:  # tunarr
                ptot = ToonamiTools.PlexToTunarr(
                    plex_url, plex_token, plex_library_name, table,
                    platform_url, int(channel_number)
                )
                ptot.run()

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
        plex_url = self._get_data("plex_url")
        plex_token = self._get_data("plex_token")
        plex_library_name = self._get_data("selected_toonami_library")
        platform_url = self._get_data("platform_url")
        platform_type = self._get_data("platform_type")
        if platform_type == 'dizquetv':
            ptod = ToonamiTools.PlexToDizqueTVSimplified(
                plex_url, plex_token, plex_library_name, table,
                platform_url, channel_number
            )
            ptod.run()
        else:  # tunarr
            ptot = ToonamiTools.PlexToTunarr(
                plex_url, plex_token, plex_library_name, table,
                platform_url, int(channel_number)
            )
            ptot.run()
        self._broadcast_status_update("New Toonami channel created!")
        self.filter_complete_event.set()

    def add_flex(self, channel_number, duration):
        self.platform_url = self._get_data("platform_url")
        self.network = config.network
        self.channel_number = channel_number
        self.duration = duration
        flex_injector = ToonamiTools.FlexInjector.DizqueTVManager(
                platform_url=self.platform_url,
                channel_number=self.channel_number,
                duration=self.duration,
                network=self.network,
            )
        flex_injector.main()
        self._broadcast_status_update("Flex content added!")