import ToonamiTools
from .utils.FlagManager import FlagManager
from .utils.DatabaseManager import get_db_manager
import config
import threading
import time
import json
import re
from queue import Queue
import sys
import webbrowser
import traceback
from typing import Optional
from .utils.MessageBroker import get_message_broker
from .utils.ErrorManager import get_error_manager, ErrorLevel

class LogicController():
    docker = FlagManager.docker
    cutless_in_args = FlagManager.cutless_in_args
    cutless = FlagManager.cutless

    def __init__(self):
        self.db_manager = get_db_manager()
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

        self.error_manager = get_error_manager()
        self._setup_error_handling()
        self._current_operation_thread = None
        self._operation_queue = Queue()
        self._error_rate_limiter = {}  # For rate limiting repeated errors

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

    def _setup_error_handling(self):
        """Initialize error message handling"""
        self._error_queue = self.message_broker.subscribe(['error_messages'])
        # Start a thread to monitor the error queue
        error_thread = threading.Thread(target=self._error_handler_loop, daemon=True)
        error_thread.start()

    def _error_handler_loop(self):
        """Continuously monitor the error queue and handle messages"""
        while True:
            try:
                channel, error_data = self._error_queue.get()
                self._handle_error_message(error_data)
                self._error_queue.task_done()
            except Exception as e:
                print(f"Error in error handler loop: {e}")
                time.sleep(1)  # Avoid busy-looping on persistent errors
    
    def _handle_error_message(self, error_data: dict):
        """
        Handle incoming error messages and broadcast them to UIs.
        This ensures all UIs receive error messages in a consistent format.
        
        For critical errors, attempts to gracefully stop the current operation.
        """
        # Check if this is a clear action
        if error_data.get('action') == 'clear':
            return
            
        # Ensure required fields exist
        if not all(key in error_data for key in ['source', 'operation', 'message', 'level']):
            print(f"Error: Missing required fields in error data: {error_data}")
            return
            
        # Rate limiting for repeated errors
        error_key = f"{error_data['source']}:{error_data['operation']}:{error_data['message']}"
        current_time = time.time()
        if error_key in self._error_rate_limiter:
            last_time = self._error_rate_limiter[error_key]
            if current_time - last_time < 5:  # 5 second rate limit
                return
        self._error_rate_limiter[error_key] = current_time
        
        # Handle critical errors
        if error_data['level'] == 'CRITICAL':
            self._handle_critical_error(error_data)
        
    
    def _format_error_message(self, error_data: dict) -> str:
        """Format error message with all available context"""
        message_parts = [
            f"[{error_data['level']}] {error_data['source']}: {error_data['message']}"
        ]
        
        if error_data.get('details'):
            message_parts.append(f"Details: {error_data['details']}")
        if error_data.get('suggestion'):
            message_parts.append(f"Suggestion: {error_data['suggestion']}")
        
        return "\n".join(message_parts)
    
    def _handle_critical_error(self, error_data: dict):
        """
        Handle critical errors by attempting to gracefully stop the current operation.
        """
        self._broadcast_status_update("Critical error detected!")
        
        # Stop current operation thread if it exists
        if self._current_operation_thread and self._current_operation_thread.is_alive():
            try:
                # Signal the thread to stop
                self._broadcast_status_update("Stopping current operation...")
                # Note: We can't directly kill the thread, but we can signal it to stop
                # The thread should check for this signal periodically
                self._should_stop = True
                
                # Wait for thread to finish (with timeout)
                self._current_operation_thread.join(timeout=5)
                
                if self._current_operation_thread.is_alive():
                    self._broadcast_status_update("Warning: Operation did not stop gracefully")
            except Exception as e:
                self._broadcast_status_update(f"Error stopping operation: {str(e)}")
        
        # Clear operation queue
        while not self._operation_queue.empty():
            try:
                self._operation_queue.get_nowait()
            except Empty:
                break
        
        # Reset UI state
        self._reset_ui_state()
    
    def _reset_ui_state(self):
        """Reset UI state after a critical error"""
        self._should_stop = False
        self._current_operation_thread = None
    
    def _run_operation(self, operation_func, *args, **kwargs):
        """
        Run an operation in a thread with proper error handling and state management.
        
        Args:
            operation_func: The function to run
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        """
        def operation_wrapper():
            try:
                self._should_stop = False
                operation_func(*args, **kwargs)
            except Exception as e:
                # Log the error and send it through the error system
                self.error_manager.send_critical(
                    source="FrontEndLogic",
                    operation=operation_func.__name__,
                    message=f"Operation failed: {str(e)}",
                    details=traceback.format_exc()
                )
            finally:
                self._current_operation_thread = None
        
        # Store reference to current operation thread
        self._current_operation_thread = threading.Thread(target=operation_wrapper)
        self._current_operation_thread.start()

    def subscribe_to_error_messages(self, callback: callable) -> None:
        """Subscribe to error messages. Callback receives (error_data)"""
        queue = self.message_broker.subscribe(['error_messages'])
        # Start a thread to monitor the error queue
        def error_handler():
            while True:
                try:
                    channel, error_data = queue.get()
                    callback(error_data)
                    queue.task_done()
                except Exception as e:
                    print(f"Error in error handler: {e}")
                    time.sleep(1)  # Avoid busy-looping on persistent errors
        
        error_thread = threading.Thread(target=error_handler, daemon=True)
        error_thread.start()

    def clear_error_messages(self) -> None:
        """
        Clear all error messages from all UIs.
        Broadcasts a clear action to the error messaging system.
        """
        try:
            clear_message = {
                'action': 'clear',
                'timestamp': time.time()
            }
            
            # Send clear message through message broker
            self.message_broker.publish('error_messages', clear_message)
            
            # Also clear local rate limiter if it exists
            if hasattr(self, '_error_rate_limiter'):
                self._error_rate_limiter.clear()
                
        except Exception as e:
            print(f"Error clearing error messages: {e}")

    def get_error_history(self, 
                         level_filter: Optional[str] = None,
                         source_filter: Optional[str] = None,
                         limit: Optional[int] = None) -> list:
        """
        Get error history with optional filtering.
        
        Args:
            level_filter: Filter by error level (CRITICAL, ERROR, WARNING, INFO)
            source_filter: Filter by source component
            limit: Maximum number of errors to return (most recent first)
            
        Returns:
            List of error messages matching the filters
        """
        try:
            return self.error_manager.get_error_history(
                level_filter=level_filter,
                source_filter=source_filter,
                limit=limit
            )
        except Exception as e:
            print(f"Error retrieving error history: {e}")
            return []
    
    def get_recent_errors(self, count: int = 10) -> list:
        """Get the most recent N errors"""
        try:
            return self.error_manager.get_recent_errors(count)
        except Exception as e:
            print(f"Error retrieving recent errors: {e}")
            return []
    
    def get_errors_by_level(self, level: str) -> list:
        """Get all errors of a specific level"""
        try:
            return self.error_manager.get_errors_by_level(level)
        except Exception as e:
            print(f"Error retrieving errors by level: {e}")
            return []
    
    def get_critical_errors(self) -> list:
        """Get all critical errors"""
        try:
            return self.error_manager.get_critical_errors()
        except Exception as e:
            print(f"Error retrieving critical errors: {e}")
            return []
    
    def clear_error_history(self) -> None:
        """Clear the entire error history"""
        try:
            self.error_manager.clear_error_history()
            self._broadcast_status_update("Error history cleared")
        except Exception as e:
            print(f"Error clearing error history: {e}")
            self._broadcast_status_update(f"Failed to clear error history: {str(e)}")
    
    def get_error_summary(self) -> dict:
        """Get a summary of errors by level"""
        try:
            return self.error_manager.get_error_summary()
        except Exception as e:
            print(f"Error retrieving error summary: {e}")
            return {
                'CRITICAL': 0,
                'ERROR': 0,
                'WARNING': 0,
                'INFO': 0
            }

    def _setup_database(self):
        self.db_manager.create_table(
            "app_data",
            "key TEXT PRIMARY KEY, value TEXT"
        )

    def _set_data(self, key, value):
        self.db_manager.insert_or_replace("app_data", {"key": key, "value": value})

    def _get_data(self, key):
        result = self.db_manager.fetchone(
            "SELECT value FROM app_data WHERE key = ?", 
            (key,)
        )
        return result["value"] if result else None

    def _check_table_exists(self, table_name):
        return self.db_manager.table_exists(table_name)

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
        # Validate required fields before processing
        missing_fields = []
        
        if selected_anime_library.startswith("eg. ") or not selected_anime_library or selected_anime_library == "Select your Anime Library":
            existing_anime_library = self._get_data("selected_anime_library")
            if not existing_anime_library or existing_anime_library == "Select your Anime Library":
                missing_fields.append("Anime Library")
            selected_anime_library = existing_anime_library

        if selected_toonami_library.startswith("eg. ") or not selected_toonami_library or selected_toonami_library == "Select your Toonami Library":
            existing_toonami_library = self._get_data("selected_toonami_library")
            if not existing_toonami_library or existing_toonami_library == "Select your Toonami Library":
                missing_fields.append("Toonami Library")
            selected_toonami_library = existing_toonami_library

        if platform_url.startswith("eg. ") or not platform_url:
            existing_platform_url = self._get_data("platform_url")
            if not existing_platform_url or existing_platform_url.startswith("eg. "):
                missing_fields.append("Platform URL")
            platform_url = existing_platform_url
        
        # Send error if required fields are missing
        if missing_fields:
            self.error_manager.send_error_level(
                source="FrontEndLogic",
                operation="on_continue_first",
                message="Required fields are missing",
                details=f"Please fill in: {', '.join(missing_fields)}",
                suggestion="Complete all required fields before continuing to the next step"
            )
            return False
        
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
        return True

    def on_continue_second(self, plex_url, plex_token, selected_anime_library, selected_toonami_library, platform_url, platform_type='dizquetv'):
        # Validate required fields before processing
        missing_fields = []
        
        # Check each widget value, if it starts with "eg. ", fetch the value from the database
        if selected_anime_library.startswith("eg. ") or not selected_anime_library:
            existing_anime_library = self._get_data("selected_anime_library")
            if not existing_anime_library or existing_anime_library.startswith("eg. "):
                missing_fields.append("Anime Library")
            selected_anime_library = existing_anime_library
            
        if selected_toonami_library.startswith("eg. ") or not selected_toonami_library:
            existing_toonami_library = self._get_data("selected_toonami_library")
            if not existing_toonami_library or existing_toonami_library.startswith("eg. "):
                missing_fields.append("Toonami Library")
            selected_toonami_library = existing_toonami_library
            
        if plex_url.startswith("eg. ") or not plex_url:
            existing_plex_url = self._get_data("plex_url")
            if not existing_plex_url or existing_plex_url.startswith("eg. "):
                missing_fields.append("Plex URL")
            plex_url = existing_plex_url
            
        if plex_token.startswith("eg. ") or not plex_token:
            existing_plex_token = self._get_data("plex_token")
            if not existing_plex_token or existing_plex_token.startswith("eg. "):
                missing_fields.append("Plex Token")
            plex_token = existing_plex_token
            
        if platform_url.startswith("eg. ") or not platform_url:
            existing_platform_url = self._get_data("platform_url")
            if not existing_platform_url or existing_platform_url.startswith("eg. "):
                missing_fields.append("Platform URL")
            platform_url = existing_platform_url

        # Send error if required fields are missing
        if missing_fields:
            self.error_manager.send_error_level(
                source="FrontEndLogic",
                operation="on_continue_second",
                message="Required fields are missing",
                details=f"Please fill in: {', '.join(missing_fields)}",
                suggestion="Complete all required fields before continuing to the next step"
            )
            return False

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
        # Validate required fields before processing (special_bump_folder is optional)
        missing_fields = []
        
        # Check each widget value, if it's blank, fetch the value from the database
        if not anime_folder:
            existing_anime_folder = self._get_data("anime_folder")
            if not existing_anime_folder:
                missing_fields.append("Anime Folder")
            anime_folder = existing_anime_folder

        if not bump_folder:
            existing_bump_folder = self._get_data("bump_folder")
            if not existing_bump_folder:
                missing_fields.append("Bump Folder")
            bump_folder = existing_bump_folder

        if not special_bump_folder:
            special_bump_folder = self._get_data("special_bump_folder")
            # Special bump folder is optional, so no validation needed

        if not working_folder:
            existing_working_folder = self._get_data("working_folder")
            if not existing_working_folder:
                missing_fields.append("Working Folder")
            working_folder = existing_working_folder

        # Send error if required fields are missing
        if missing_fields:
            self.error_manager.send_error_level(
                source="FrontEndLogic",
                operation="on_continue_third",
                message="Required fields are missing",
                details=f"Please fill in: {', '.join(missing_fields)}",
                suggestion="Complete all required folder selections before continuing (Special Bump Folder is optional)"
            )
            return False

        # Save the fetched data to the database
        self._set_data("anime_folder", anime_folder)
        self._set_data("bump_folder", bump_folder)
        self._set_data("special_bump_folder", special_bump_folder)
        self._set_data("working_folder", working_folder)

        # Optional: Print values for verification
        print(anime_folder, bump_folder, special_bump_folder, working_folder)
        self._broadcast_status_update("Idle")
        return True

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
        # Validate required fields before processing
        missing_fields = []
        
        # Validate toonami_version
        if not toonami_version or toonami_version in ["Please select version", "Select a Toonami Version"]:
            missing_fields.append("Toonami Version")
        
        # Validate channel_number
        if not channel_number or channel_number.startswith("eg. ") or channel_number.strip() == "":
            missing_fields.append("Channel Number")
        else:
            try:
                int(channel_number)
            except ValueError:
                missing_fields.append("Channel Number (must be numeric)")
        
        # Validate flex_duration
        if not flex_duration or flex_duration.startswith("eg. ") or flex_duration.strip() == "":
            missing_fields.append("Flex Duration")
        else:
            # Check format MM:SS
            if not re.match(r'^\d+:\d{2}$', flex_duration):
                missing_fields.append("Flex Duration (must be in MM:SS format, e.g., 04:20)")
        
        # Send error if required fields are missing
        if missing_fields:
            self.error_manager.send_error_level(
                source="FrontEndLogic",
                operation="create_toonami_channel",
                message="Required fields are missing or invalid",
                details=f"Please fill in: {', '.join(missing_fields)}",
                suggestion="Complete all required fields with valid values before creating the channel"
            )
            return False
        
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
        # Validate required fields before processing
        missing_fields = []
        
        # Validate toonami_version
        if not toonami_version or toonami_version in ["Please select version", "Select a Toonami Version"]:
            missing_fields.append("Toonami Version")
        
        # Validate channel_number
        if not channel_number or channel_number.startswith("eg. ") or channel_number.strip() == "":
            missing_fields.append("Channel Number")
        else:
            try:
                int(channel_number)
            except ValueError:
                missing_fields.append("Channel Number (must be numeric)")
        
        # Validate flex_duration
        if not flex_duration or flex_duration.startswith("eg. ") or flex_duration.strip() == "":
            missing_fields.append("Flex Duration")
        else:
            # Check format MM:SS
            if not re.match(r'^\d+:\d{2}$', flex_duration):
                missing_fields.append("Flex Duration (must be in MM:SS format, e.g., 04:20)")
        
        # Send error if required fields are missing
        if missing_fields:
            self.error_manager.send_error_level(
                source="FrontEndLogic",
                operation="create_toonami_channel_cont",
                message="Required fields are missing or invalid",
                details=f"Please fill in: {', '.join(missing_fields)}",
                suggestion="Complete all required fields with valid values before creating the channel"
            )
            return False
            
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
        # Validate required fields before processing
        missing_fields = []
        
        # Validate channel_number
        if not channel_number or channel_number.startswith("eg. ") or channel_number.strip() == "":
            missing_fields.append("Channel Number")
        else:
            try:
                int(channel_number)
            except ValueError:
                missing_fields.append("Channel Number (must be numeric)")
        
        # Validate duration (flex duration)
        if not duration or duration.startswith("eg. ") or duration.strip() == "":
            missing_fields.append("Flex Duration")
        else:
            # Check format MM:SS
            if not re.match(r'^\d+:\d{2}$', duration):
                missing_fields.append("Flex Duration (must be in MM:SS format, e.g., 04:20)")
        
        # Send error if required fields are missing
        if missing_fields:
            self.error_manager.send_error_level(
                source="FrontEndLogic",
                operation="add_flex",
                message="Required fields are missing or invalid",
                details=f"Please fill in: {', '.join(missing_fields)}",
                suggestion="Complete all required fields with valid values before adding flex content"
            )
            return False
            
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