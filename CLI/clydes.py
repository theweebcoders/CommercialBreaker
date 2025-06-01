import threading
import queue
import time
from API import LogicController
from CLI.CommercialBreakerCLI import main as CommercialBreakerCLI
from queue import Queue, Empty
import json


class MediaServerManager:
    def __init__(self, logic, app):
        self.logic = logic
        self.app = app  # We'll use app.safe_input() instead of plain input()
        self.media_server_type = None  # 'plex' or 'jellyfin'

    # Main method to get media server credentials
    def get_media_server_creds(self):
        print("Choose your media server:")
        print("1. Plex")
        print("2. Jellyfin")
        server_choice = self.app.safe_input("Enter the number of your choice: ").strip()

        if server_choice == "1":
            self.media_server_type = "plex"
            self._get_plex_creds()
        elif server_choice == "2":
            self.media_server_type = "jellyfin"
            self._get_jellyfin_creds()
        else:
            print("Invalid choice. Please try again.")
            return self.get_media_server_creds()

    def _get_plex_creds(self):
        print(
            "Would you like to login to Plex via the web interface? If not, you will need to enter your Plex URL and token manually. (y/n)"
        )
        login = self.app.safe_input().strip().lower()

        # Login to Plex via web interface
        if login == "y":
            self.logic.login_to_plex()
            self._wait_for_servers("plex")
            self._select_server("plex")
            self._wait_for_libraries("plex")
            anime_library_name = self._choose_library("Anime", "plex")
            toonami_library_name = self._choose_library("Toonami", "plex")

            platform_type, platform_url = self._choose_platform()
            self.logic.on_continue_first(
                anime_library_name, toonami_library_name, platform_url, platform_type
            )

        # If user chooses not to login, manually enter Plex credentials
        elif login == "n":
            self._manual_plex_entry()

    def _get_jellyfin_creds(self):
        print("Enter your Jellyfin server URL (e.g., http://localhost:8096):")
        jellyfin_url = self.app.safe_input().strip()

        if not jellyfin_url:
            print("Server URL is required for Jellyfin.")
            return self._get_jellyfin_creds()

        print("Logging into Jellyfin via Quick Connect...")
        self.logic.login_to_jellyfin(jellyfin_url)
        self._wait_for_servers("jellyfin")
        self._select_server("jellyfin")
        self._wait_for_libraries("jellyfin")
        anime_library_name = self._choose_library("Anime", "jellyfin")
        toonami_library_name = self._choose_library("Toonami", "jellyfin")

        platform_type, platform_url = self._choose_platform()
        self.logic.on_continue_first(
            anime_library_name, toonami_library_name, platform_url, platform_type
        )

    def _choose_platform(self):
        print("Choose the service you want to use:")

        if self.media_server_type == "jellyfin":
            print("Note: DizqueTV is not compatible with Jellyfin. Using Tunarr.")
            platform_type = "tunarr"
            default_url = "http://localhost:8000"
        else:
            print("1. DizqueTV")
            print("2. Tunarr")
            service_choice = self.app.safe_input(
                "Enter the number of your choice: "
            ).strip()

            if service_choice == "1":
                platform_type = "dizquetv"
                default_url = "http://localhost:17685"
            else:
                platform_type = "tunarr"
                default_url = "http://localhost:8000"

        platform_url = (
            self.app.safe_input(f"Enter the platform URL (default: {default_url}): ")
            or default_url
        )

        return platform_type, platform_url

    def _wait_for_servers(self, server_type):
        if server_type == "plex":
            while not self.logic.plex_servers:
                print("Waiting for Plex servers to load...")
                time.sleep(1)
        else:  # jellyfin
            while not self.logic.jellyfin_servers:
                print("Waiting for Jellyfin servers to load...")
                time.sleep(1)

    def _select_server(self, server_type):
        print("Choose a server:")

        if server_type == "plex":
            servers = {
                i + 1: server for i, server in enumerate(self.logic.plex_servers)
            }
        else:  # jellyfin
            servers = {
                i + 1: server for i, server in enumerate(self.logic.jellyfin_servers)
            }

        for idx, server in servers.items():
            print(f"{idx}. {server}")
        server_choice = int(
            self.app.safe_input("Enter the number of the server you'd like to use: ")
        )

        if server_type == "plex":
            server_name = servers.get(server_choice, self.logic.plex_servers[0])
        else:  # jellyfin
            server_name = servers.get(server_choice, self.logic.jellyfin_servers[0])

        self.logic.on_server_selected(server_name)

    def _wait_for_libraries(self, server_type):
        if server_type == "plex":
            while not self.logic.plex_libraries:
                print("Waiting for Plex libraries to load...")
                time.sleep(1)
        else:  # jellyfin
            while not self.logic.jellyfin_libraries:
                print("Waiting for Jellyfin libraries to load...")
                time.sleep(1)

    def _choose_library(self, library_type, server_type):
        print(f"Choose a {library_type} library:")

        if server_type == "plex":
            libraries = {
                i + 1: library for i, library in enumerate(self.logic.plex_libraries)
            }
        else:  # jellyfin
            libraries = {
                i + 1: library
                for i, library in enumerate(self.logic.jellyfin_libraries)
            }

        for idx, library in libraries.items():
            print(f"{idx}. {library}")
        library_choice = int(
            self.app.safe_input(
                f"Enter the number next to your {library_type} library: "
            )
        )

        if server_type == "plex":
            return libraries.get(library_choice, self.logic.plex_libraries[0])
        else:  # jellyfin
            return libraries.get(library_choice, self.logic.jellyfin_libraries[0])

    def _manual_plex_entry(self):
        plex_url = self.app.safe_input("Enter your Plex URL: ")
        plex_token = self.app.safe_input("Enter your Plex token: ")
        anime_library_name = self.app.safe_input(
            "Enter the name of your Anime library: "
        )
        toonami_library_name = self.app.safe_input(
            "Enter the name of your Toonami library: "
        )

        platform_type, platform_url = self._choose_platform()

        self.logic.on_continue_second(
            anime_library_name,
            toonami_library_name,
            plex_url,
            plex_token,
            platform_url,
            platform_type,
        )


class FolderManager:
    def __init__(self, logic, app):
        self.logic = logic
        self.app = app

    def get_folders(self):
        print(
            "Please enter the paths to the required folders. For optional folders, press Enter if you do not wish to specify."
        )

        anime_folder = self.app.safe_input("Enter the path to your Anime folder: ")
        bump_folder = self.app.safe_input("Enter the path to your Bump folder: ")
        special_bump_folder = (
            self.app.safe_input(
                "Enter the path to your Special Bump folder (optional): "
            )
            or None
        )
        working_folder = self.app.safe_input("Enter the path to your Working folder: ")
        self._confirm_paths(
            anime_folder, bump_folder, special_bump_folder, working_folder
        )

        self.logic.on_continue_third(
            anime_folder, bump_folder, special_bump_folder, working_folder
        )

    def _confirm_paths(
        self, anime_folder, bump_folder, special_bump_folder, working_folder
    ):
        print("\nYou have entered the following paths:")
        print(f"Anime Folder: {anime_folder}")
        print(f"Bump Folder: {bump_folder}")
        print(
            f"Special Bump Folder: {'Not specified' if not special_bump_folder else special_bump_folder}"
        )
        print(f"Working Folder: {working_folder}")
        if (
            self.app.safe_input("Are these paths correct? (y/n): ").strip().lower()
            != "y"
        ):
            self.get_folders()


class ContentPreparer:
    def __init__(self, logic, app):
        self.logic = logic
        self.app = app

    def prepare_content(self):
        if not self.logic._check_table_exists("lineup_v8_uncut"):
            if (
                self.app.safe_input(
                    "Would you like to prepare your shows and bumps to be cut now? (y/n): "
                )
                .strip()
                .lower()
                == "y"
            ):
                self.logic.prepare_content(self._display_show_selection)
                self._wait_for_content()
                self._handle_additional_options()
        else:
            print(
                "You have already run 'prepare your shows and bumps to be cut'. Skipping this step."
            )

    def _display_show_selection(self, unique_show_names):
        sorted_show_names = sorted(unique_show_names)
        print(
            "Select shows to exclude by entering the corresponding numbers separated by commas."
        )

        for index, show_name in enumerate(sorted_show_names):
            print(f"{index + 1}. {show_name}")

        excluded_indexes = self.app.safe_input("Numbers of shows to exclude: ").strip()
        excluded_shows = set()

        try:
            excluded_indexes = map(int, excluded_indexes.split(","))
            for index in excluded_indexes:
                if 1 <= index <= len(sorted_show_names):
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
        if (
            self.app.safe_input(
                "Move your filtered shows to the working folder to speed up processing? (y/n): "
            )
            .strip()
            .lower()
            == "y"
        ):
            self.logic.move_filtered()
            while not self.logic.is_filtered_complete():
                time.sleep(1)
            self.logic.reset_filter_event()


class ToonamiManager:
    def __init__(self, logic, app):
        self.logic = logic
        self.app = app
        self.platform_url = self.logic._get_data("platform_url")
        self.platform_type = None  # Don't fetch yet!
        self.toonami_library = self.logic._get_data("selected_toonami_library")
        self.toonami_versions = [
            "OG",
            "2",
            "3",
            "Mixed",
            "Uncut OG",
            "Uncut 2",
            "Uncut 3",
            "Uncut Mixed",
        ]
        self.channels_with_flex = set()

    def create_toonami_channels(self):
        # Now that we're here, fetch the latest value:
        self.platform_type = self.logic._get_data("platform_type")
        if not self.logic._check_table_exists("lineup_v8"):
            if self._confirm(
                "We need to prepare your cut Anime for the Toonami channel. Would you like to continue? (y/n)"
            ):
                self.logic.prepare_cut_anime()
                self._wait_for("lineup_v8", "Preparing cut anime...")
                self.add_special_bumps()
                self.prepare_plex()
                self.create_toonami_channel()
                if self._confirm(
                    "Would you like to create a second Toonami channel? (y/n)"
                ):
                    self.create_second_toonami_channel()
                elif self.platform_type == "dizquetv":
                    self.offer_flex_for_existing_channel()
        else:
            if self._confirm(
                "Is this your first time creating a Toonami channel? (y/n)"
            ):
                self.add_special_bumps()
                self.prepare_plex()
                self.create_toonami_channel()
                if self._confirm(
                    "Would you like to create a second Toonami channel? (y/n)"
                ):
                    self.create_second_toonami_channel()
                elif self.platform_type == "dizquetv":
                    self.offer_flex_for_existing_channel()
            else:
                if self._confirm(
                    "Would you like to create a second Toonami channel? (y/n)"
                ):
                    self.create_second_toonami_channel()
                elif self.platform_type == "dizquetv":
                    self.offer_flex_for_existing_channel()

    def add_special_bumps(self):
        if self._confirm("Would you like to add special bumps to the lineup? (y/n)"):
            self.logic.add_special_bumps()
            self._wait_for("lineup_v8_bonus", "Adding special bumps...")

    def prepare_plex(self):
        if self._confirm(
            "We need to prepare Plex for the Toonami channel. Would you like to continue? (y/n)"
        ):
            self.logic.create_prepare_plex()
            while not self.logic.is_filtered_complete():
                time.sleep(1)
            self.logic.reset_filter_event()

    def create_toonami_channel(self):
        print("It's time to create the Toonami channel!")
        print("Choose a Toonami version:")
        for i, version in enumerate(self.toonami_versions):
            print(f"{i+1}. {version}")

        version_choice = self._safe_input_choice(
            "Enter the number of your choice: ", len(self.toonami_versions)
        )
        version = self.toonami_versions[version_choice - 1]
        channel_number = self.app.safe_input(
            "What channel number would you like to use? "
        )

        flex_duration = self.app.safe_input(
            "Enter your Flex duration (Minutes:Seconds) for commercial breaks: "
        ).strip()

        # Summarize
        print("\nThe settings for the Toonami channel are:")
        print(f"Toonami version: {version}")
        print(f"Channel number: {channel_number}")
        print(f"Platform URL: {self.platform_url}")
        print(f"Toonami library: {self.toonami_library}")
        print(f"Flex duration: {flex_duration or '[Not Provided]'}")

        if self._confirm("Would you like to continue with these settings? (y/n)"):
            if self._confirm(
                "We are now ready to create the Toonami channel. This may take a few minutes. Continue? (y/n)"
            ):
                self.logic.create_toonami_channel(
                    version, channel_number, flex_duration
                )
                # **Block** the main thread until creation is done
                self._wait_for_filter_event("Creating the Toonami channel...")

                self.logic._set_data("toonami_channel_created", True)

                # If using DizqueTV, confirm whether to apply FLEX to *this* newly created channel
                if self.platform_type == "dizquetv":
                    if self._confirm(
                        "Would you like to add FLEX to this new channel now? (y/n)"
                    ):
                        self.logic.add_flex(channel_number, flex_duration)
                        self._wait_for_filter_event("Adding FLEX to the new channel...")
                        time.sleep(2)
                        self.channels_with_flex.add(channel_number)

    def create_second_toonami_channel(self):
        print("It's time to create the second Toonami channel!")
        print("Choose a Toonami version:")
        for i, version in enumerate(self.toonami_versions):
            print(f"{i+1}. {version}")

        version_choice = self._safe_input_choice(
            "Enter the number of your choice: ", len(self.toonami_versions)
        )
        version = self.toonami_versions[version_choice - 1]

        channel_number = self.app.safe_input(
            "What channel number would you like to use? "
        )
        continue_from_last = self._confirm(
            "Would you like to continue from the last episode of the first Toonami channel? (y/n): "
        )

        print("\nConfirm the settings for the second Toonami channel:")
        print(f"Toonami version: {version}")
        print(f"Channel number: {channel_number}")
        print(f"Continue from last episode: {continue_from_last}")

        if not self._confirm("Would you like to continue with these settings? (y/n): "):
            return self.create_second_toonami_channel()

        if self._confirm(
            "We need to prepare your second Toonami channel. Would you like to continue? (y/n): "
        ):
            self.logic.prepare_toonami_channel(continue_from_last, version)
            self._wait_for_filter_event("Preparing the second Toonami channel...")

        flex_duration = self.app.safe_input(
            "Enter your Flex duration (Minutes:Seconds) for commercial breaks: "
        ).strip()

        if self._confirm(
            "Would you like to create the second Toonami channel now? (y/n): "
        ):
            self.logic.create_toonami_channel_cont(
                version, channel_number, flex_duration
            )
            self._wait_for_filter_event("Creating the second Toonami channel...")
            print("Second Toonami channel created successfully!")

            if self.platform_type == "dizquetv":
                if self._confirm(
                    "Would you like to add FLEX to this new channel now? (y/n)"
                ):
                    self.logic.add_flex(channel_number, flex_duration)
                    self._wait_for_filter_event("Adding FLEX to the second channel...")
                    self.channels_with_flex.add(channel_number)
        elif self.platform_type == "dizquetv":
            self.offer_flex_for_existing_channel()

    def offer_flex_for_existing_channel(self):
        if self._confirm("Would you like to add FLEX to an existing channel? (y/n)"):
            existing_channel = self.app.safe_input(
                "Enter the channel number you want to add FLEX to: "
            )

            if existing_channel in self.channels_with_flex:
                print(
                    f"FLEX was already added to channel {existing_channel} in this session."
                )
                if not self._confirm(
                    "Do you want to add more FLEX to this channel anyway? (y/n)"
                ):
                    return

            flex_duration = self.app.safe_input(
                "Enter your FLEX duration (Minutes:Seconds): "
            )
            self.logic.add_flex(existing_channel, flex_duration)
            self._wait_for_filter_event("Adding FLEX to existing channel...")
            self.channels_with_flex.add(existing_channel)

    # -----------
    # Helper methods
    # -----------

    def _confirm(self, prompt):
        answer = self.app.safe_input(prompt + " ").strip().lower()
        return answer == "y"

    def _safe_input_choice(self, prompt, num_choices):
        while True:
            answer = self.app.safe_input(prompt)
            try:
                choice = int(answer)
                if 1 <= choice <= num_choices:
                    return choice
                print("Invalid choice. Please enter a valid number.")
            except ValueError:
                print("Please enter a number.")

    def _wait_for(self, table_name, message):
        print(message)
        while not self.logic._check_table_exists(table_name):
            time.sleep(1)

    def _wait_for_filter_event(self, message):
        print(message)
        wait_counter = 0
        while not self.logic.is_filtered_complete():
            time.sleep(1)
        # Once done, reset
        self.logic.reset_filter_event()


class ClydesApp:
    def __init__(self):
        self.input_lock = threading.Lock()
        self.logic = LogicController()
        self.status_queue = Queue()
        self.media_server_manager = MediaServerManager(self.logic, self)
        self.folder_manager = FolderManager(self.logic, self)
        self.content_preparer = ContentPreparer(self.logic, self)
        self.toonami_manager = ToonamiManager(self.logic, self)
        self.config = {}

        # Subscribe to updates via LogicController
        self.logic.subscribe_to_updates("status_updates", self.handle_status_updates)
        self.logic.subscribe_to_updates(
            "cutless_state", self.handle_cutless_state_update
        )

        # Start the status printer thread
        self.status_thread = threading.Thread(target=self.status_printer, daemon=True)
        self.status_thread.start()

    def safe_input(self, prompt=""):
        """
        Enforces that only one place in the entire app can read user input at a time.
        Blocks any concurrency on input.
        """
        with self.input_lock:
            return input(prompt)

    def status_printer(self):
        while True:
            status = self.status_queue.get()
            if status is None:  # Stop signal
                break
            if "Idle" not in status:  # Ignore "Idle" status messages
                print(status)

    def load_existing_configurations(self):
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
            answer = self.safe_input(
                "Would you like to use your existing folders and Plex Credentials? (y/n): "
            )
            if answer.strip().lower() == "y":
                print("Using existing configurations.")
                return True
        return False

    # Define handler methods
    def handle_status_updates(self, data):
        self.status_queue.put(f"Status: {data}")

    def handle_cutless_state_update(self, data):
        is_enabled = data.lower() == "true" if isinstance(data, str) else bool(data)
        print(
            f"ClydesApp: Received cutless_state update from LogicController: {is_enabled}"
        )

    def run(self):
        if not self.load_existing_configurations():
            self.media_server_manager.get_media_server_creds()
            self.folder_manager.get_folders()
        self.content_preparer.prepare_content()
        CommercialBreakerCLI(cutless_enabled=self.logic.cutless)
        self.toonami_manager.create_toonami_channels()
        print("Clydes has finished running.")


def main():
    app = ClydesApp()
    app.run()


if __name__ == "__main__":
    main()
