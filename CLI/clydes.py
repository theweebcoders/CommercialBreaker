import threading
import queue
import time
from GUI import LogicController
from CLI.CommercialBreakerCLI import main as CommercialBreakerCLI
import config


def status_printer(status_queue):
    while True:
        status = status_queue.get()
        if status is None:  # Stop signal
            break
        if "Idle" not in status:  # Ignore "Idle" status messages
            print(status)

def get_plex_creds(logic):
    print("Would you like to login to Plex via the web interface? If not, you will need to enter your Plex URL and token manually. (y/n)")
    login = input().strip().lower()
    
    if login == "y":
        logic.login_to_plex()
        # Ensuring the server list is loaded
        while not logic.plex_servers:
            print("Waiting for Plex servers to load...")
            time.sleep(1)  # Smoother wait loop with feedback

        print("Choose a server:")
        servers = {i + 1: server for i, server in enumerate(logic.plex_servers)}
        for idx, server in servers.items():
            print(f"{idx}. {server}")
        server_choice = int(input("Enter server number: "))
        server_name = servers.get(server_choice, logic.plex_servers[0])  # Default to the first server if invalid choice
        
        logic.on_server_selected(server_name)

        # Ensuring the library list is loaded
        while not logic.plex_libraries:
            print("Waiting for Plex libraries to load...")
            time.sleep(1)

        anime_library_name = choose_library(logic, "Anime")
        toonami_library_name = choose_library(logic, "Toonami")
        dizquetv_url = input("Enter the dizqueTV URL: ")
        logic.on_continue_first(anime_library_name, toonami_library_name, dizquetv_url)

    elif login == "n":
        plex_url = input("Enter your Plex URL: ")
        plex_token = input("Enter your Plex token: ")
        anime_library_name = input("Enter the name of your Anime library: ")
        toonami_library_name = input("Enter the name of your Toonami library: ")
        dizquetv_url = input("Enter the dizqueTV URL: ")
        logic.on_continue_second(anime_library_name, toonami_library_name, plex_url, plex_token, dizquetv_url)

def choose_library(logic, library_type):
    print(f"Choose a {library_type} library:")
    libraries = {i + 1: library for i, library in enumerate(logic.plex_libraries)}
    for idx, library in libraries.items():
        print(f"{idx}. {library}")
    library_choice = int(input(f"Enter {library_type} library number: "))
    return libraries.get(library_choice, logic.plex_libraries[0])  # Default to the first library if invalid choice


def get_folders(logic):
    # Improved feedback and input handling for folder setup
    print("Please enter the paths to the required folders. For optional folders, press Enter if you do not wish to specify.")

    anime_folder = input("Enter the path to your Anime folder: ")
    bump_folder = input("Enter the path to your Bump folder: ")
    special_bump_folder = input("Enter the path to your Special Bump folder (optional): ")
    working_folder = input("Enter the path to your Working folder: ")

    # Handle optional folder by setting to None if not provided
    special_bump_folder = None if not special_bump_folder.strip() else special_bump_folder

    # Call the logic controller with the collected folder paths
    logic.on_continue_third(anime_folder, bump_folder, special_bump_folder, working_folder)

    # Optionally, verify and confirm the paths with the user
    print("\nYou have entered the following paths:")
    print(f"Anime Folder: {anime_folder}")
    print(f"Bump Folder: {bump_folder}")
    print(f"Special Bump Folder: {'Not specified' if special_bump_folder is None else special_bump_folder}")
    print(f"Working Folder: {working_folder}")
    if input("Are these paths correct? (y/n): ").strip().lower() != 'y':
        print("Let's try entering the folder paths again.")
        get_folders(logic)


def prepare_content(logic):
    print("We need to prepare your shows and bumps to be cut. This will also create the uncut lineup.")
    
    if input("Would you like to prepare your shows and bumps to be cut now? (y/n): ").strip().lower() == 'y':
        logic.prepare_content(display_show_selection)

        # Check periodically until the table exists, giving user feedback on the status
        print("Preparing content. Please wait...")
        while not logic._check_table_exists("lineup_v8_uncut"):
            time.sleep(1)  # Use a shorter sleep to check more frequently
        print("Content preparation complete.")
        time.sleep(2)  # Pause for a moment before continuing

        if input("Fetch Plex Timestamps for intros and outros to speed up cutting? (y/n): ").strip().lower() == 'y':
            logic.get_plex_timestamps()

        if input("Move your filtered shows to the working folder to speed up processing? (y/n): ").strip().lower() == 'y':
            logic.move_filtered()
            while not logic.is_filtered_complete():
                time.sleep(1)  # Sleep to prevent a busy wait
            logic.reset_filter_event()

def display_show_selection(unique_show_names):
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


def create_toonami_channel(logic):
    dizquetv_url = logic._get_data("dizquetv_url")
    toonami_library = logic._get_data("selected_toonami_library")
    print("It's time to create the Toonami channel!")
    toonami_versions = ["OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]

    print("Choose a Toonami version:")
    for i, version in enumerate(toonami_versions):
        print(f"{i+1}. {version}")
    
    version_choice = safe_input_choice("Enter the number of your choice: ", len(toonami_versions))
    version = toonami_versions[version_choice - 1]
    
    channel_number = input("What channel number would you like to use? ")

    if not logic._check_table_exists("lineup_v8"):
        if confirm("We need to prepare your cut Anime for the Toonami channel. Would you like to continue? (y/n)"):            
                logic.prepare_cut_anime()
                wait_for(logic, "lineup_v8", "Preparing cut anime...")

    if confirm("Would you like to add special bumps to the lineup? (y/n)"):
        logic.add_special_bumps()
        wait_for(logic, "lineup_v8_bonus", "Adding special bumps...")

    if confirm("We need to prepare Plex for the Toonami channel. Would you like to continue? (y/n)"):
        logic.prepare_plex()
        while not logic.is_filtered_complete():
            time.sleep(1)  # Sleep to prevent a busy wait
        logic.reset_filter_event()

    print("The settings for the Toonami channel are as follows:")
    print(f"Toonami version: {version}")
    print(f"Channel number: {channel_number}")
    print(f"DizqueTV URL: {dizquetv_url}")
    print(f"Toonami library: {toonami_library}")

    if confirm("Would you like to continue with these settings? (y/n)"):
        if confirm("We are now ready to create the Toonami channel. Please make sure dizqueTV and Plex are running. This may take a few minutes. Continue? (y/n)"):
            logic.create_toonami_channel(version, channel_number)
            while not logic.is_filtered_complete():
                time.sleep(1)  # Sleep to prevent a busy wait
            logic.reset_filter_event()
            logic._set_data("toonami_channel_created", True)

def safe_input_choice(prompt, num_choices):
    while True:
        try:
            choice = int(input(prompt))
            if 1 <= choice <= num_choices:
                return choice
            print("Invalid choice. Please enter a valid number.")
        except ValueError:
            print("Please enter a number.")

def confirm(prompt):
    return input(prompt).strip().lower() == 'y'

def wait_for(logic, table_name, message):
    print(message)
    while not logic._check_table_exists(table_name):
        time.sleep(1)

def create_second_toonami_channel(logic):
    print("It's time to create the second Toonami channel!")
    continue_from_last = False

    # List Toonami versions and prompt user to choose one
    toonami_versions = ["OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]
    print("Choose a Toonami version:")
    for i, version in enumerate(toonami_versions):
        print(f"{i+1}. {version}")
    
    version_choice = safe_input_choice("Enter the number of your choice: ", len(toonami_versions))
    version = toonami_versions[version_choice - 1]
    
    channel_number = input("What channel number would you like to use? ")
    continue_from_last = True if confirm("Would you like to continue from the last episode of the first Toonami channel? (y/n): ") else False

    # Confirm settings before proceeding
    print("\nConfirm the settings for the second Toonami channel:")
    print(f"Toonami version: {version}")
    print(f"Channel number: {channel_number}")
    print(f"Continue from last episode: {continue_from_last}")

    if not confirm("Would you like to continue with these settings? (y/n): "):
        return create_second_toonami_channel(logic)

    # Preparing the second Toonami channel
    if confirm("We need to prepare your second Toonami channel. Would you like to continue? (y/n): "):
        logic.prepare_toonami_channel(continue_from_last, version)
        while not logic.is_filtered_complete():
            time.sleep(1)  # Sleep to prevent a busy wait
        logic.reset_filter_event()

    # Finalize creation
    if confirm("Would you like to create the second Toonami channel now? (y/n): "):
        logic.create_toonami_channel_cont(version, channel_number)
        while not logic.is_filtered_complete():
            time.sleep(1)  # Sleep to prevent a busy wait
        print("Second Toonami channel created successfully!")
        logic.reset_filter_event()

def safe_input_choice(prompt, num_choices):
    while True:
        try:
            choice = int(input(prompt))
            if 1 <= choice <= num_choices:
                return choice
            print("Invalid choice. Please enter a valid number.")
        except ValueError:
            print("Please enter a number.")

def confirm(prompt):
    return input(prompt).strip().lower() == 'y'

def add_flex(logic):
    print("It's time to add a flex to the Toonami channel!")
    # Collect server and channel details
    ssh_host = input("What is the IP address of the server hosting the dizqueTV server? ")
    ssh_username = input("What is the SSH username? ")
    ssh_password = input("What is the SSH password? ")
    dizquetv_container = input("What is the name of the dizqueTV docker container? ")
    channel_number = input("What channel number would you like to add the flex to? ")
    duration = input("What is the duration of the flex in minutes:seconds? ")
    logic.add_flex_creds(ssh_host, ssh_username, ssh_password, dizquetv_container, channel_number, duration)
    time.sleep(2)
    if input("Proceed with adding the flex to the Toonami channel? (y/n): ").strip().lower() == 'y':
        while not logic.is_filtered_complete():
            time.sleep(1)  # Sleep to prevent a busy wait
        print("Flex added successfully!")
        logic.reset_filter_event()

def load_existing_configurations(logic):
    # Gather existing data
    existing_data = {
        "plex_url": logic._get_data("plex_url"),
        "plex_token": logic._get_data("plex_token"),
        "anime_library": logic._get_data("selected_anime_library"),
        "toonami_library": logic._get_data("selected_toonami_library"),
        "dizquetv_url": logic._get_data("dizquetv_url"),
        "anime_folder": logic._get_data("anime_folder"),
        "bump_folder": logic._get_data("bump_folder"),
        "working_folder": logic._get_data("working_folder"),        
    }

    if all(existing_data.values()):
        if user_input("Would you like to use your existing folders and Plex Credentials? (y/n): "):
            print("Using existing configurations.")
        else:
            get_plex_creds(logic)
            get_folders(logic)
    else:
        get_plex_creds(logic)
        get_folders(logic)

def prepare_show_and_bumps_if_necessary(logic):
    if logic._check_table_exists("lineup_v8_uncut"):
        print("You have already run 'prepare your shows and bumps to be cut'. Skipping this step.")
    else:
        prepare_content(logic)

def run_commercial_breaker():
    if user_input("Would you like to run Commercial Breaker? This process can take a long time to complete. (y/n): "):
        CommercialBreakerCLI()

def manage_toonami_channels(logic):
    if logic._get_data("toonami_channel_created"):
        if user_input("You have already created the Toonami channel. Would you like to create a second Toonami channel? (y/n): "):
            create_second_toonami_channel(logic)
        else:
            print("No further action taken on Toonami channels.")
    else:
        create_toonami_channel(logic)

def add_flex_if_desired(logic):
    if user_input("Would you like to add a flex to the Toonami channel? (y/n): "):
        add_flex(logic)

def user_input(prompt):
    return input(prompt).strip().lower() == 'y'

def clydes():
    status_queue = queue.Queue()
    logic = LogicController()
    logic.subscribe_to_status_updates(lambda msg: status_queue.put(f"Status: {msg}"))
    printer_thread = threading.Thread(target=status_printer, args=(status_queue,))
    printer_thread.start()

    # Loading existing configurations
    load_existing_configurations(logic)

    # Process for preparing content
    prepare_show_and_bumps_if_necessary(logic)

    # Running Commercial Breaker
    run_commercial_breaker()

    # Managing Toonami channels
    manage_toonami_channels(logic)

    # Adding flex to the Toonami channel
    add_flex_if_desired(logic)

    print("Clydes has finished running.")
    printer_thread.join()  # Ensure that the printer thread has completed before exiting