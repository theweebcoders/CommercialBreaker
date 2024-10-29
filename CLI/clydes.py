import threading
import queue
import time
import redis
from GUI import LogicController
from CLI.CommercialBreakerCLI import main as CommercialBreakerCLI

class PlexManager:
    def __init__(self, logic):
        self.logic = logic

    # Main method to get Plex credentials
    def get_plex_creds(self):
        print("Would you like to login to Plex via the web interface? If not, you will need to enter your Plex URL and token manually. (y/n)")
        login = input().strip().lower()
        
        # Login to Plex via web interface
        if login == 'y':
            self.logic.login_to_plex()
            self._wait_for_servers()
            self._select_server()
            self._wait_for_libraries()
            anime_library_name = self._choose_library("Anime")
            toonami_library_name = self._choose_library("Toonami")
            dizquetv_url = input("Enter the dizqueTV URL: ")
            self.logic.on_continue_first(anime_library_name, toonami_library_name, dizquetv_url)
        # If user chooses not to login, manually enter Plex credentials
        elif login == 'n':
            self._manual_plex_entry()

    def _wait_for_servers(self):
        while not self.logic.plex_servers:
            print("Waiting for Plex servers to load...")
            time.sleep(1)

    def _select_server(self):
        print("Choose a server:")
        servers = {i + 1: server for i, server in enumerate(self.logic.plex_servers)}
        for idx, server in servers.items():
            print(f"{idx}. {server}")
        server_choice = int(input("Enter the number that is next to the server you would like to use: "))
        server_name = servers.get(server_choice, self.logic.plex_servers[0])
        self.logic.on_server_selected(server_name)

    def _wait_for_libraries(self):
        while not self.logic.plex_libraries:
            print("Waiting for Plex libraries to load...")
            time.sleep(1)

    def _choose_library(self, library_type):
        print(f"Choose a {library_type} library:")
        libraries = {i + 1: library for i, library in enumerate(self.logic.plex_libraries)}
        for idx, library in libraries.items():
            print(f"{idx}. {library}")
        library_choice = int(input(f"Enter the number that is next to your {library_type} library: "))
        return libraries.get(library_choice, self.logic.plex_libraries[0])

    def _manual_plex_entry(self):
        plex_url = input("Enter your Plex URL: ")
        plex_token = input("Enter your Plex token: ")
        anime_library_name = input("Enter the name of your Anime library: ")
        toonami_library_name = input("Enter the name of your Toonami library: ")
        dizquetv_url = input("Enter the dizqueTV URL: ")
        self.logic.on_continue_second(anime_library_name, toonami_library_name, plex_url, plex_token, dizquetv_url)

class FolderManager:
    def __init__(self, logic):
        self.logic = logic

    def get_folders(self):
        print("Please enter the paths to the required folders. For optional folders, press Enter if you do not wish to specify.")
        
        # Get folder paths from user
        anime_folder = input("Enter the path to your Anime folder: ")
        bump_folder = input("Enter the path to your Bump folder: ")
        special_bump_folder = input("Enter the path to your Special Bump folder (optional): ") or None
        working_folder = input("Enter the path to your Working folder: ")

        # Confirm paths with user
        self._confirm_paths(anime_folder, bump_folder, special_bump_folder, working_folder)

        # Save paths and continue
        self.logic.on_continue_third(anime_folder, bump_folder, special_bump_folder, working_folder)
        

    def _confirm_paths(self, anime_folder, bump_folder, special_bump_folder, working_folder):
        print("\nYou have entered the following paths:")
        print(f"Anime Folder: {anime_folder}")
        print(f"Bump Folder: {bump_folder}")
        print(f"Special Bump Folder: {'Not specified' if not special_bump_folder else special_bump_folder}")
        print(f"Working Folder: {working_folder}")
        if input("Are these paths correct? (y/n): ").strip().lower() != 'y':
            self.get_folders()

class ContentPreparer:
    def __init__(self, logic):
        self.logic = logic

    def prepare_content(self):
        if not self.logic._check_table_exists("lineup_v8_uncut"):
            if input("Would you like to prepare your shows and bumps to be cut now? (y/n): ").strip().lower() == 'y':
                self.logic.prepare_content(self._display_show_selection)
                self._wait_for_content()
                self._handle_additional_options()
        else:
            print ("You have already run 'prepare your shows and bumps to be cut'. Skipping this step.")

    def _display_show_selection(self, unique_show_names):
        sorted_show_names = sorted(unique_show_names)  # Sorting the set directly
        print("Select shows to exclude by entering the corresponding numbers separated by commas.")
        
        for index, show_name in enumerate(sorted_show_names):
            print(f"{index + 1}. {show_name}")
        
        excluded_indexes = input("Numbers of shows to exclude: ").strip()
        excluded_shows = set()  # Using a set to avoid duplicates
        
        try:
            excluded_indexes = map(int, excluded_indexes.split(','))
            for index in excluded_indexes:
                if 1 <= index <= len(sorted_show_names):  # Validate index range
                    excluded_shows.add(sorted_show_names[index - 1])
        except ValueError:
            print("Invalid input. No shows have been excluded.")

        return [show for show in sorted_show_names if show not in excluded_shows]

    def _wait_for_content(self):
        print("Preparing content. Please wait...")
        while not self.logic._check_table_exists("lineup_v8_uncut"):
            time.sleep(1)
        print("Content preparation complete.")
        time.sleep(2)

    def _handle_additional_options(self):
        if input("Move your filtered shows to the working folder to speed up processing? (y/n): ").strip().lower() == 'y':
            self.logic.move_filtered()
            while not self.logic.is_filtered_complete():
                time.sleep(1)  # Sleep to prevent a busy wait
            self.logic.reset_filter_event()

class ToonamiManager:
    def __init__(self, logic):
        self.logic = logic
        self.dizquetv_url = self.logic._get_data("dizquetv_url")
        self.toonami_library = self.logic._get_data("selected_toonami_library")
        self.toonami_versions = ["OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]
        self.continue_from_last = False
       
    def create_toonami_channels(self):
        if not self.logic._check_table_exists("lineup_v8"):
            if self._confirm("We need to prepare your cut Anime for the Toonami channel. Would you like to continue? (y/n)"):
                self.logic.prepare_cut_anime()
                self._wait_for("lineup_v8", "Preparing cut anime...")
                self.add_special_bumps()
                self.prepare_plex()
                self.create_toonami_channel()
                if self._confirm("Would you like to create a second Toonami channel? (y/n)"):
                    self.create_second_toonami_channel()
        else:
            if self._confirm("Is this your first time creating a Toonami channel? (y/n)"):
                self.add_special_bumps()
                self.prepare_plex()
                self.create_toonami_channel()
                if self._confirm("Would you like to create a second Toonami channel? (y/n)"):
                    self.create_second_toonami_channel()
            else:
                if self._confirm("Would you like to create a second Toonami channel? (y/n)"):
                    self.create_second_toonami_channel()
                
    
    def add_special_bumps(self):
        if self._confirm("Would you like to add special bumps to the lineup? (y/n)"):
            self.logic.add_special_bumps()
            self._wait_for("lineup_v8_bonus", "Adding special bumps...")
    
    def prepare_plex(self):
        if self._confirm("We need to prepare Plex for the Toonami channel. Would you like to continue? (y/n)"):
            self.logic.create_prepare_plex()
            while not self.logic.is_filtered_complete():
                time.sleep(1)
            self.logic.reset_filter_event()
            
    def create_toonami_channel(self):

        print("It's time to create the Toonami channel!")
        print("Choose a Toonami version:")
        for i, version in enumerate(self.toonami_versions):
            print(f"{i+1}. {version}")
        
        version_choice = self._safe_input_choice("Enter the number of your choice: ", len(self.toonami_versions))
        version = self.toonami_versions[version_choice - 1]
        channel_number = input("What channel number would you like to use? ")
        print("The settings for the Toonami channel are as follows:")
        print(f"Toonami version: {version}")
        print(f"Channel number: {channel_number}")
        print(f"DizqueTV URL: {self.dizquetv_url}")
        print(f"Toonami library: {self.toonami_library}")

        if self._confirm("Would you like to continue with these settings? (y/n)"):
            if self._confirm("We are now ready to create the Toonami channel. Please make sure dizqueTV and Plex are running. This may take a few minutes. Continue? (y/n)"):
                self.logic.create_toonami_channel(version, channel_number)
                while not self.logic.is_filtered_complete():
                    time.sleep(1)
                self.logic.reset_filter_event()
                self.logic._set_data("toonami_channel_created", True)


    def create_second_toonami_channel(self):
        print("It's time to create the second Toonami channel!")
        print("Choose a Toonami version:")
        for i, version in enumerate(self.toonami_versions):
            print(f"{i+1}. {version}")
        
        version_choice = self._safe_input_choice("Enter the number of your choice: ", len(self.toonami_versions))
        version = self.toonami_versions[version_choice - 1]
        
        channel_number = input("What channel number would you like to use? ")
        continue_from_last = True if self._confirm("Would you like to continue from the last episode of the first Toonami channel? (y/n): ") else False

        # Confirm settings before proceeding
        print("\nConfirm the settings for the second Toonami channel:")
        print(f"Toonami version: {version}")
        print(f"Channel number: {channel_number}")
        print(f"Continue from last episode: {continue_from_last}")

        if not self._confirm("Would you like to continue with these settings? (y/n): "):
            return self.create_second_toonami_channel()

        # Preparing the second Toonami channel
        if self._confirm("We need to prepare your second Toonami channel. Would you like to continue? (y/n): "):
            self.logic.prepare_toonami_channel(continue_from_last, version)
            while not self.logic.is_filtered_complete():
                time.sleep(1)  # Sleep to prevent a busy wait
            self.logic.reset_filter_event()

        # Finalize creation
        if self._confirm("Would you like to create the second Toonami channel now? (y/n): "):
            self.logic.create_toonami_channel_cont(version, channel_number)
            while not self.logic.is_filtered_complete():
                time.sleep(1)  # Sleep to prevent a busy wait
            print("Second Toonami channel created successfully!")
            self.logic.reset_filter_event()


    def _safe_input_choice(self, prompt, num_choices):
        while True:
            try:
                choice = int(input(prompt))
                if 1 <= choice <= num_choices:
                    return choice
                print("Invalid choice. Please enter a valid number.")
            except ValueError:
                print("Please enter a number.")


    def _confirm(self, prompt):
        return input(prompt).strip().lower() == 'y'

    def _wait_for(self, table_name, message):
        print(message)
        while not self.logic._check_table_exists(table_name):
            time.sleep(1)
        

class FlexManager:
    def __init__(self, logic):
        self.logic = logic
        self.existing_data = {
            "ssh_host": self.logic._get_data("ssh_host"),
            "ssh_username": self.logic._get_data("ssh_user"),
            "ssh_password": self.logic._get_data("ssh_pass"),
            "dizquetv_container": self.logic._get_data("dizquetv_container_name")
        }

    def check_if_flex_creds_exist(self):
        if all(self.existing_data.values()):
            if input("Would you like to use your existing flex credentials? (y/n): ").strip().lower() == 'y':
                channel_number = input("What channel number would you like to add the flex to? ")
                duration = input("What is the duration of the flex in minutes:seconds? ")
                self.logic.add_flex_creds(self.existing_data["ssh_host"], self.existing_data["ssh_username"], self.existing_data["ssh_password"], self.existing_data["dizquetv_container"], channel_number, duration)
                return True
        return False


    def add_flex_creds(self):
        print("It's time to add a flex to the Toonami channel!")
        # Collect server and channel details
        ssh_host = input("What is the IP address of the server hosting the dizqueTV server? ")
        ssh_username = input("What is the SSH username? ")
        ssh_password = input("What is the SSH password? ")
        dizquetv_container = input("What is the name of the dizqueTV docker container? ")
        channel_number = input("What channel number would you like to add the flex to? ")
        duration = input("What is the duration of the flex in minutes:seconds? ")
        self.logic.add_flex_creds(ssh_host, ssh_username, ssh_password, dizquetv_container, channel_number, duration)
        time.sleep(2)

    def wait_for_flex(self):
        while not self.logic.is_filtered_complete():
            time.sleep(1)  # Sleep to prevent a busy waiy
        self.logic.reset_filter_event()

    def add_flex(self):
        if not self.check_if_flex_creds_exist():
            self.add_flex_creds()
        if input("Proceed with adding the flex to the Toonami channel? (y/n): ").strip().lower() == 'y':
            self.logic.add_flex()
            self.wait_for_flex()
            print("Flex added successfully!")
           

class ClydesApp:
    def __init__(self):
        self.logic = LogicController()
        self.plex_manager = PlexManager(self.logic)
        self.folder_manager = FolderManager(self.logic)
        self.content_preparer = ContentPreparer(self.logic)
        self.toonami_manager = ToonamiManager(self.logic)
        self.flex_manager = FlexManager(self.logic)
        self.status_queue = queue.Queue()
        # Start Redis listener for status updates
        self.redis_queue = queue.Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.redis_listener_thread = threading.Thread(target=self.process_redis_messages, daemon=True)
        self.redis_listener_thread.start()
        self.printer_thread = threading.Thread(target=self.status_printer)


    def status_printer(self):
        while True:
            status = self.status_queue.get()
            if status is None:  # Stop signal
                break
            if "Idle" not in status:  # Ignore "Idle" status messages
                print(status)

    def load_existing_configurations(self):
        # Gather existing data
        existing_data = {
            "plex_url": self.logic._get_data("plex_url"),
            "plex_token": self.logic._get_data("plex_token"),
            "anime_library": self.logic._get_data("selected_anime_library"),
            "toonami_library": self.logic._get_data("selected_toonami_library"),
            "dizquetv_url": self.logic._get_data("dizquetv_url"),
            "anime_folder": self.logic._get_data("anime_folder"),
            "bump_folder": self.logic._get_data("bump_folder"),
            "working_folder": self.logic._get_data("working_folder"),        
        }

        if all(existing_data.values()):
            if input("Would you like to use your existing folders and Plex Credentials? (y/n): ").strip().lower() == 'y':
                print("Using existing configurations.")
                return True
        else:
            return False
                
    def listen_for_redis_updates(self, redis_queue):
        redis_client = self.logic.redis_client
        pubsub = redis_client.pubsub()
        pubsub.subscribe('status_updates', 'new_server_choices', 'new_library_choices', 'plex_servers', 'plex_libraries', 'plex_auth_url')

        for message in pubsub.listen():
            if message['type'] == 'message':
                redis_queue.put(message)

    def start_redis_listener_thread(self, redis_queue):
        threading.Thread(target=self.listen_for_redis_updates, args=(redis_queue,), daemon=True).start()

    def process_redis_messages(self):
        while True:
            message = self.redis_queue.get()
            if message['channel'].decode('utf-8') == 'status_updates':
                self.status_queue.put(f"Status: {message['data'].decode('utf-8')}")
           
    def run(self):
        self.printer_thread.start()
        if not self.load_existing_configurations():
            self.plex_manager.get_plex_creds()
            self.folder_manager.get_folders()
        self.content_preparer.prepare_content()
        CommercialBreakerCLI()
        self.toonami_manager.create_toonami_channels()
        self.flex_manager.add_flex()
        print("Clydes has finished running.")


def main():
    app = ClydesApp()
    app.run()

if __name__ == "__main__":
    main()