import sqlite3
import ToonamiTools
from .components.FlagManager import FlagManager
import config
import threading
import time
import json
from queue import Queue
import sys
import webbrowser
import traceback
from .components.MessageBroker import get_message_broker

class LogicController():
    docker = FlagManager.docker
    cutless_in_args = FlagManager.cutless_in_args
    cutless = FlagManager.cutless

    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self._setup_database()
        self.docker = FlagManager.docker
        self.cutless = FlagManager.cutless
        
        # Check platform compatibility if needed - let FlagManager handle this
        if self.cutless:
            platform_type = self._get_data("platform_type")
            platform_url = self._get_data("platform_url")
            # Let FlagManager handle the compatibility check
            FlagManager.evaluate_platform_compatibility(platform_type, platform_url)

        # Get the message broker singleton
        self.message_broker = get_message_broker()
        
        # UI callback management
        self._ui_callbacks = {
            'status_updates': [],
            'progress_updates': [],
            'plex_servers': [],
            'plex_libraries': [],
            'filtered_files': [],
            'plex_auth_url': [],
            'cutless_state': [],
            'new_server_choices': [],
            'new_library_choices': []
        }
        
        self._start_message_handler_thread()
        
        self.plex_servers = []
        self.plex_libraries = []
        self.filter_complete_event = threading.Event()
        self.filtered_files_for_selection = []  # List to store filtered files for prepopulation

        # Register callback for cutless state changes
        FlagManager.register_cutless_callback(self._on_cutless_change)

    def subscribe_to_status_updates(self, callback: callable):
        """Subscribe to status updates. Callback receives (status_message)"""
        self.subscribe_to_updates('status_updates', callback)

    def subscribe_to_progress_updates(self, callback: callable):
        """Subscribe to progress updates. Callback receives (progress_data)"""
        self.subscribe_to_updates('progress_updates', callback)

    def subscribe_to_plex_servers(self, callback: callable):
        """Subscribe to Plex server updates. Callback receives (server_list_json)"""
        self.subscribe_to_updates('plex_servers', callback)

    def subscribe_to_plex_libraries(self, callback: callable):
        """Subscribe to Plex library updates. Callback receives (library_list_json)"""
        self.subscribe_to_updates('plex_libraries', callback)

    def subscribe_to_filtered_files(self, callback: callable):
        """Subscribe to filtered files updates. Callback receives (filtered_files_json)"""
        self.subscribe_to_updates('filtered_files', callback)

    def subscribe_to_plex_auth_url(self, callback: callable):
        """Subscribe to Plex auth URL. Callback receives (auth_url)"""
        self.subscribe_to_updates('plex_auth_url', callback)

    def subscribe_to_cutless_state(self, callback: callable):
        """Subscribe to cutless state changes. Callback receives ('true' or 'false')"""
        self.subscribe_to_updates('cutless_state', callback)

    def subscribe_to_server_choices(self, callback: callable):
        """Subscribe to new server choices. Callback receives (signal)"""
        self.subscribe_to_updates('new_server_choices', callback)

    def subscribe_to_library_choices(self, callback: callable):
        """Subscribe to new library choices. Callback receives (signal)"""
        self.subscribe_to_updates('new_library_choices', callback)

    def subscribe_to_updates(self, channel: str, callback: callable):
        """Simple subscription method for UIs"""
        if channel not in self._ui_callbacks:
            self._ui_callbacks[channel] = [] # Initialize if new channel (should be pre-defined though)
            print(f"Warning: Subscribing to a new, previously unknown channel: {channel}")
        if callback not in self._ui_callbacks[channel]: # Avoid duplicate subscriptions
            self._ui_callbacks[channel].append(callback)
    
    def unsubscribe_from_updates(self, channel: str, callback: callable):
        """Simple unsubscription method"""
        if channel in self._ui_callbacks and callback in self._ui_callbacks[channel]:
            self._ui_callbacks[channel].remove(callback)
            # Optionally, clean up empty channel list if desired, though not strictly necessary
            # if not self._ui_callbacks[channel]:
            #     del self._ui_callbacks[channel]
    
    def _start_message_handler_thread(self):
        """Internal method to start the thread that routes broker messages to UI callbacks"""
        handler_thread = threading.Thread(target=self._message_handler_loop, daemon=True)
        handler_thread.start()

    def _message_handler_loop(self):
        """Continuously fetches messages from the broker and routes them to UI callbacks."""
        # Subscribe to all channels that LogicController manages for UI callbacks
        known_channels = list(self._ui_callbacks.keys())
        queue = self.message_broker.subscribe(known_channels)
        
        while True:
            try:
                channel, data = queue.get() # Blocks until a message is available
                
                # Iterate over a copy of the callbacks list for thread safety
                callbacks_to_run = list(self._ui_callbacks.get(channel, []))
                
                for callback in callbacks_to_run:
                    try:
                        # Ensure UI updates are scheduled on the main thread if necessary
                        # For Remi/Tkinter, this might involve using their respective mechanisms
                        # For now, direct call. UIs must handle thread safety if needed.
                        callback(data)
                    except Exception as e:
                        print(f"Error in UI callback for channel {channel} with data '{data}': {e}")
                queue.task_done()
            except Exception as e:
                print(f"Error in message handler loop: {e}")
                # Avoid busy-looping on persistent errors
                time.sleep(1)

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

    def _publish_status_update(self, channel, message):
        """
        Publish a message to the specified channel using the message broker.
        
        Args:
            channel: Channel name
            message: Message to publish
        """
        self.message_broker.publish(channel, message)

    def _broadcast_status_update(self, message):
        """
        Publish a status update to the 'status_updates' channel.
        
        Args:
            message: Status message
        """
        # Publish to the broker
        self.message_broker.publish('status_updates', message)

    def publish_plex_servers(self):
        """Publish server list via message broker"""
        plex_servers_json = json.dumps(self.plex_servers)
        self._publish_status_update('plex_servers', plex_servers_json)

    def publish_plex_libraries(self):
        """Publish libraries list via message broker"""
        plex_libraries_json = json.dumps(self.plex_libraries)
        self._publish_status_update('plex_libraries', plex_libraries_json)

    def publish_filtered_files(self, filtered_files):
        """Publish filtered files to channel"""
        filtered_files_json = json.dumps(filtered_files)
        self._publish_status_update('filtered_files', filtered_files_json)

    def get_token(self):
        """Get Plex token from database"""
        plex_token = self._get_data("plex_token")
        return plex_token

    def publish_plex_auth_url(self, auth_url):
        """Publish Plex authentication URL to channel"""
        self.message_broker.publish('plex_auth_url', auth_url)
        print("Please open the following URL in your browser to authenticate with Plex: \n" + auth_url)

    def publish_cutless_state(self, enabled):
        """Publish cutless state to 'cutless_state' channel as a boolean"""
        self._publish_status_update('cutless_state', enabled)

    def _on_cutless_change(self, enabled):
        """
        Callback for FlagManager cutless state changes. Broadcasts the new state.
        """
        LogicController.cutless = enabled  # Keep class variable in sync
        self.cutless = enabled             # Keep instance variable in sync
        
        # Publish to the message broker
        self.publish_cutless_state(enabled)
        
        # Broadcast status update
        self._broadcast_status_update(f"Cutless mode {'enabled' if enabled else 'disabled'}")

    def is_filtered_complete(self):
        return self.filter_complete_event.is_set()

    def reset_filter_event(self):
        self.filter_complete_event.clear()

    def set_filter_event(self):
        self.filter_complete_event.set()

    def check_dizquetv_compatibility(self):
        platform_url = self._get_data("platform_url")
        platform_type = self._get_data("platform_type")
        
        # Delegate to FlagManager's evaluation
        return FlagManager.evaluate_platform_compatibility(platform_type, platform_url)

    def login_to_plex(self):
        def login_thread():
            try:
                print("Logging in to Plex...")
                # Create PlexServerList instance, fetch token and populate dropdown
                self._broadcast_status_update("Logging in to Plex...")
                self.server_list = ToonamiTools.PlexServerList()
                
                # Set up the callback to handle auth URL
                self.server_list.set_auth_url_callback(self.publish_plex_auth_url)
                
                self.server_list.run()
                self._broadcast_status_update("Plex login successful. Fetching servers...")
                # Update the list of servers
                self.plex_servers, plex_token = self.server_list.plex_servers, self.server_list.plex_token
                self._set_data("plex_token", plex_token)
                self._broadcast_status_update("Plex servers fetched!")

                # Announce that new server choices are available
                self.message_broker.publish("new_server_choices", "new_server_choices")
                self.publish_plex_servers()

            except Exception as e:
                error_msg = f"ERROR: Plex login failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in login_to_plex: {e}")
                
                traceback.print_exc()

        thread = threading.Thread(target=login_thread)
        thread.start()

    def open_auth_url(self, auth_url):
        """Open the Plex authentication URL in the browser."""
        print(f"Opening auth URL in browser: {auth_url}")
        webbrowser.open(auth_url)

    def on_server_selected(self, selected_server):
        self.fetch_libraries(selected_server)

    def fetch_libraries(self, selected_server):
        """Unified fetch libraries method that uses the message broker"""
        def fetch_libraries_thread():
            try:
                # Create PlexLibraryManager and PlexLibraryFetcher instances
                self._broadcast_status_update(f"Fetching libraries for {selected_server}...")
                
                # Get token either from get_token or from server_list
                plex_token = self.get_token()
                if plex_token is None and hasattr(self, 'server_list'):
                    plex_token = self.server_list.plex_token
                
                if plex_token is None:
                    raise Exception("Could not fetch Plex Token")
                    
                # Create library manager
                self.library_manager = ToonamiTools.PlexLibraryManager(selected_server, plex_token)
                plex_url = self.library_manager.run()
                self._set_data("plex_url", plex_url)
                
                if plex_url is None:
                    raise Exception("Could not fetch Plex URL")
                
                # Use either direct URL or one from library manager
                url_to_use = plex_url
                if hasattr(self.library_manager, 'plex_url'):
                    url_to_use = self.library_manager.plex_url
                
                # Create library fetcher
                self.library_fetcher = ToonamiTools.PlexLibraryFetcher(url_to_use, plex_token)
                self.library_fetcher.run()

                # Update the list of libraries
                self.plex_libraries = self.library_fetcher.libraries
                self._broadcast_status_update("Libraries fetched successfully!")

                # Announce that new library choices are available
                self.message_broker.publish("new_library_choices", "new_library_choices")
                self.publish_plex_libraries()

            except Exception as e:
                error_msg = f"ERROR: Library fetching failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in fetch_libraries: {e}")
                
                traceback.print_exc()

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
        
        # Re-evaluate cutless mode using FlagManager
        FlagManager.evaluate_platform_compatibility(platform_type, platform_url)
        
        # Sync our instance and class variable with FlagManager
        self.cutless = FlagManager.cutless
        LogicController.cutless = FlagManager.cutless

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
        
        # Re-evaluate cutless mode using FlagManager
        FlagManager.evaluate_platform_compatibility(platform_type, platform_url)
        
        # Sync our instance and class variable with FlagManager
        self.cutless = FlagManager.cutless
        LogicController.cutless = FlagManager.cutless

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
            try:
                # Update the values based on the current state of the checkboxes
                self._broadcast_status_update("Preparing bumps...")
                working_folder = self._get_data("working_folder")
                anime_folder = self._get_data("anime_folder")
                bump_folder = self._get_data("bump_folder")
                # merger_bumps_list_1 = 'multibumps_v2_data_reordered'
                # merger_bumps_list_2 = 'multibumps_v3_data_reordered'
                # merger_bumps_list_3 = 'multibumps_v9_data_reordered'
                # merger_bumps_list_4 = 'multibumps_v8_data_reordered'
                # merger_out_1 = 'lineup_v2_uncut'
                # merger_out_2 = 'lineup_v3_uncut'
                # merger_out_3 = 'lineup_v9_uncut'
                # merger_out_4 = 'lineup_v8_uncut'
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
                
            except Exception as e:
                error_msg = f"ERROR: Content preparation failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in prepare_content: {e}")
                traceback.print_exc()
                
        thread = threading.Thread(target=prepare_content_thread)
        thread.start()

    def move_filtered(self, prepopulate=False):
        """
        Moves filtered episodes to the toonami_filtered folder or prepares them for selection.
        
        Args:
            prepopulate (bool, optional): If True, don't move files but collect paths for selection
                                          If False (default), move files as before
        """
        def move_filtered_thread():
            try:
                import ToonamiTools
                fmove = ToonamiTools.FilterAndMove()
                
                if prepopulate:
                    self._broadcast_status_update("Preparing filtered shows for selection...")
                    # Call run with prepopulate=True to get filtered paths without moving
                    filtered_files = fmove.run(prepopulate=True)
                    
                    # Publish filtered files via broker
                    self.publish_filtered_files(filtered_files)
                    print(f"Published {len(filtered_files)} filtered files")
                    
                    self._broadcast_status_update(f"Found {len(filtered_files)} files for selection")
                else:
                    self._broadcast_status_update("Moving filtered shows...")
                    working_folder = self._get_data("working_folder")
                    filter_output_folder = working_folder + "/toonami_filtered/"
                    # Call run with prepopulate=False to move files (original behavior)
                    fmove.run(filter_output_folder, prepopulate=False)
                    self._broadcast_status_update("Filtered shows moved!")
                
                self.filter_complete_event.set()
                
            except Exception as e:
                error_msg = f"ERROR: Filter and move operation failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in move_filtered: {e}")
                traceback.print_exc()
                self.filter_complete_event.set()  # Still set event so callers don't hang
            
        thread = threading.Thread(target=move_filtered_thread)
        thread.start()

    def get_plex_timestamps(self):
        def get_plex_timestamps_thread():
            try:
                self._broadcast_status_update("Getting Timestamps from Plex...")
                working_folder = self._get_data("working_folder")
                toonami_filtered_folder = working_folder + "/toonami"
                plex_ts_url = self._get_data("plex_url")
                plex_ts_token = self._get_data("plex_token")
                plex_ts_anime_library_name = self._get_data("selected_anime_library")
                GetTimestamps = ToonamiTools.GetPlexTimestamps(plex_ts_url, plex_ts_token, plex_ts_anime_library_name, toonami_filtered_folder)
                GetTimestamps.run()  # Calling the run method on the instance
                self._broadcast_status_update("Plex timestamps fetched!")
                
            except Exception as e:
                error_msg = f"ERROR: Getting Plex timestamps failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in get_plex_timestamps: {e}")
                
                traceback.print_exc()

        thread = threading.Thread(target=get_plex_timestamps_thread)
        thread.start()

    def prepare_cut_anime(self):
        def prepare_cut_anime_thread():
            try:
                working_folder = self._get_data("working_folder")
                cutless_mode_used = self._get_data("cutless_mode_used")
                cutless_enabled = cutless_mode_used == 'True'
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
                if not cutless_enabled:
                    commercial_injector_prep.organize_files()
                else:
                    self._broadcast_status_update("Cutless Mode: Skipping cut file preparation")
                commercial_injector.generate_lineup()
                BIC.run()
                self._broadcast_status_update("Creating your lineup...")
                merger.run(merger_bumps_list_1, commercial_injector_out, merger_out_1)
                merger.run(merger_bumps_list_2, commercial_injector_out, merger_out_2)
                merger.run(merger_bumps_list_3, commercial_injector_out, merger_out_3)
                merger.run(merger_bumps_list_4, commercial_injector_out, merger_out_4)
                if cutless_enabled:
                    self._broadcast_status_update("Cutless Mode: Finalizing lineup tables...")
                    finalizer = ToonamiTools.CutlessFinalizer()
                    finalizer.run()
                    self._broadcast_status_update("Cutless lineup finalization complete!")

                self._broadcast_status_update("Cut anime preparation complete!")
                
            except Exception as e:
                error_msg = f"ERROR: Cut anime preparation failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in prepare_cut_anime: {e}")
                traceback.print_exc()

        thread = threading.Thread(target=prepare_cut_anime_thread)
        thread.start()

    def add_special_bumps(self):
        special_bump_folder = self._get_data("special_bump_folder")
        special_bump_processor = ToonamiTools.FileProcessor(special_bump_folder)
        special_bump_processor.process_files()

    def create_prepare_plex(self):
        def prepare_plex_thread():
            try:
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
                
            except Exception as e:
                error_msg = f"ERROR: Plex preparation failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in prepare_plex: {e}")
                
                traceback.print_exc()
                self.filter_complete_event.set()  # Still set event so callers don't hang
                
        thread = threading.Thread(target=prepare_plex_thread)
        thread.start()

    def create_toonami_channel(self, toonami_version, channel_number, flex_duration):
        """
        Create a Toonami channel using the stored platform settings
        """
        def create_toonami_channel_thread():
            try:
                self._broadcast_status_update("Creating Toonami channel...")
                plex_url = self._get_data("plex_url")
                plex_token = self._get_data("plex_token")
                anime_library = self._get_data("selected_anime_library")
                toonami_library = self._get_data("selected_toonami_library")
                platform_url = self._get_data("platform_url")
                platform_type = self._get_data("platform_type")
                cutless_mode_used = self._get_data("cutless_mode_used")
                cutless_enabled = cutless_mode_used == 'True'
                toon_config = config.TOONAMI_CONFIG.get(toonami_version, {})
                table = toon_config["table"]
                
                # If cutless mode is enabled, use the cutless table instead
                if (cutless_enabled):
                    table = f"{table}_cutless"
                    self._broadcast_status_update(f"Cutless Mode: Using {table} table")

                if platform_type == 'dizquetv':
                    ptod = ToonamiTools.PlexToDizqueTVSimplified(
                        plex_url=plex_url, 
                        plex_token=plex_token, 
                        anime_library=anime_library,
                        toonami_library=toonami_library, 
                        table=table, 
                        dizquetv_url=platform_url, 
                        channel_number=int(channel_number),
                        cutless_mode=cutless_enabled
                    )
                    ptod.run()
                else:  # tunarr
                    ptot = ToonamiTools.PlexToTunarr(
                        plex_url, plex_token, toonami_library, table,
                        platform_url, int(channel_number), flex_duration
                    )
                    ptot.run()

                self._broadcast_status_update("Toonami channel created!")
                self.filter_complete_event.set()
                
            except Exception as e:
                error_msg = f"ERROR: Toonami channel creation failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in create_toonami_channel: {e}")
                traceback.print_exc()
                self.filter_complete_event.set()  # Still set event so callers don't hang

        thread = threading.Thread(target=create_toonami_channel_thread)
        thread.start()

    def prepare_toonami_channel(self, start_from_last_episode, toonami_version):

        def prepare_toonami_channel_thread():
            try:
                self._broadcast_status_update("Preparing Toonami channel...")
                cont_config = config.TOONAMI_CONFIG_CONT.get(toonami_version, {})
                cutless_mode_used = self._get_data("cutless_mode_used")
                cutless_enabled = cutless_mode_used == 'True'
                merger_bump_list = cont_config["merger_bump_list"]
                merger_out = cont_config["merger_out"]
                encoder_in = cont_config["encoder_in"]
                uncut = cont_config["uncut"]

                merger = ToonamiTools.ShowScheduler(reuse_episode_blocks=True, continue_from_last_used_episode_block=start_from_last_episode, uncut=uncut)
                merger.run(merger_bump_list, encoder_in, merger_out)
                if cutless_enabled:
                    finalizer = ToonamiTools.CutlessFinalizer()
                    finalizer.run()
                self._broadcast_status_update("Toonami channel prepared!")
                self.filter_complete_event.set()
                
            except Exception as e:
                error_msg = f"ERROR: Toonami channel preparation failed: {str(e)}"
                self._broadcast_status_update(error_msg)
                print(f"Thread error in prepare_toonami_channel: {e}")
                traceback.print_exc()
                self.filter_complete_event.set()  # Still set event so callers don't hang
                
        thread = threading.Thread(target=prepare_toonami_channel_thread)
        thread.start()

    def create_toonami_channel_cont(self, toonami_version, channel_number, flex_duration):
        """
        Create a Toonami continuation channel using the stored platform settings
        """
        self._broadcast_status_update("Creating new Toonami channel...")
        cont_config = config.TOONAMI_CONFIG_CONT.get(toonami_version, {})
        table = cont_config["merger_out"]
        plex_url = self._get_data("plex_url")
        plex_token = self._get_data("plex_token")
        anime_library = self._get_data("selected_anime_library")
        toonami_library = self._get_data("selected_toonami_library")
        platform_url = self._get_data("platform_url")
        platform_type = self._get_data("platform_type")
        cutless_mode_used = self._get_data("cutless_mode_used")
        cutless_enabled = cutless_mode_used == 'True'
        
        # If cutless mode is enabled, use the cutless table instead
        if cutless_enabled:
            table = f"{table}_cutless"
            self._broadcast_status_update(f"Cutless Mode: Using {table} table")
        
        if platform_type == 'dizquetv':
            ptod = ToonamiTools.PlexToDizqueTVSimplified(
                plex_url=plex_url, 
                plex_token=plex_token, 
                anime_library=anime_library,
                toonami_library=toonami_library, 
                table=table, 
                dizquetv_url=platform_url, 
                channel_number=int(channel_number),
                cutless_mode=cutless_enabled
            )
            ptod.run()
        else:  # tunarr
            ptot = ToonamiTools.PlexToTunarr(
                plex_url, plex_token, toonami_library, table,
                platform_url, int(channel_number), flex_duration
            )
            ptot.run()
            
        self._broadcast_status_update("New Toonami channel created!")
        self.filter_complete_event.set()

    def add_flex(self, channel_number, duration):
        self.platform_url = self._get_data("platform_url")
        self.network = config.network
        self.channel_number = int(channel_number)
        self.duration = duration
        flex_injector = ToonamiTools.FlexInjector.DizqueTVManager(
                platform_url=self.platform_url,
                channel_number=self.channel_number,
                duration=self.duration,
                network=self.network,
            )
        flex_injector.main()
        self.filter_complete_event.set()
        self._broadcast_status_update("Flex content added!")
