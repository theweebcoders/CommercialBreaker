import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sv_ttk
from ComBreak import CommercialBreakerLogic
from API import LogicController
import config
import threading
import os
import json
import psutil  # Added back psutil


class Page1(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.logic = logic
        self.libraries_selected = 0

        # Subscribe to updates via LogicController
        self.logic.subscribe_to_updates(
            "status_updates", self.update_status_label_handler
        )
        self.logic.subscribe_to_updates("plex_servers", self.handle_plex_servers_update)
        self.logic.subscribe_to_updates(
            "plex_libraries", self.handle_plex_libraries_update
        )
        self.logic.subscribe_to_updates(
            "jellyfin_servers", self.handle_jellyfin_servers_update
        )
        self.logic.subscribe_to_updates(
            "jellyfin_libraries", self.handle_jellyfin_libraries_update
        )
        self.logic.subscribe_to_updates(
            "plex_auth_url", self.handle_plex_auth_url_update
        )
        self.logic.subscribe_to_updates(
            "jellyfin_auth_url", self.handle_jellyfin_auth_url_update
        )
        self.logic.subscribe_to_updates(
            "media_server_type", self.handle_media_server_type_update
        )
        self.logic.subscribe_to_updates(
            "new_server_choices", self.handle_new_server_choices_update
        )
        self.logic.subscribe_to_updates(
            "new_library_choices", self.handle_new_library_choices_update
        )

        # Initialize variables
        self.media_server_type = None
        self.plex_servers = []
        self.plex_libraries = []
        self.jellyfin_servers = []
        self.jellyfin_libraries = []

        # Media Server Selection
        label = ttk.Label(self, text="Choose Media Server", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        # Login buttons frame
        login_frame = ttk.Frame(self)
        login_frame.pack(pady=5)

        login_with_plex_button = ttk.Button(
            login_frame, text="Login with Plex", command=self.login_to_plex
        )
        login_with_plex_button.pack(side=tk.LEFT, padx=5)

        login_with_jellyfin_button = ttk.Button(
            login_frame, text="Login with Jellyfin", command=self.login_to_jellyfin
        )
        login_with_jellyfin_button.pack(side=tk.LEFT, padx=5)

        # Jellyfin server URL entry (initially hidden)
        self.jellyfin_url_frame = ttk.Frame(self)
        ttk.Label(self.jellyfin_url_frame, text="Jellyfin Server URL:").pack()
        self.jellyfin_url_entry = ttk.Entry(self.jellyfin_url_frame)
        self.jellyfin_url_entry.insert(0, "e.g., http://localhost:8096")
        self.jellyfin_url_entry.pack(pady=3)

        # Server dropdown (unified for both Plex and Jellyfin)
        self.server_name = tk.StringVar()
        self.server_name.set("Select a Server")
        self.server_dropdown = ttk.Combobox(self)
        self.server_dropdown.bind(
            "<<ComboboxSelected>>",
            lambda event: self.logic.on_server_selected(self.server_dropdown.get()),
        )
        self.server_dropdown.set("Select a Server")
        self.server_dropdown.pack(pady=3)

        self.anime_library_name = tk.StringVar()
        self.anime_library_name.set("Select your Anime Library")
        self.anime_library_dropdown = ttk.Combobox(
            self, textvariable=self.anime_library_name
        )
        self.anime_library_dropdown.bind(
            "<<ComboboxSelected>>", self.add_1_to_libraries_selected
        )
        self.anime_library_dropdown.set("Select your Anime Library")
        self.anime_library_dropdown.pack(pady=3)

        self.library_name = tk.StringVar()
        self.library_name.set("Select your Toonami Library")
        self.library_dropdown = ttk.Combobox(self, textvariable=self.library_name)
        self.library_dropdown["values"] = "Select your Toonami Library"
        self.library_dropdown.bind(
            "<<ComboboxSelected>>", self.add_1_to_libraries_selected
        )
        self.library_dropdown.set("Select your Toonami Library")
        self.library_dropdown.pack(pady=3)

        # Platform Selection Frame
        platform_frame = ttk.Frame(self)
        platform_frame.pack(pady=3)

        platform_label = ttk.Label(platform_frame, text="Select Platform:")
        platform_label.pack(side="left", padx=5)

        self.platform_var = tk.StringVar(value="dizquetv")
        dizquetv_radio = ttk.Radiobutton(
            platform_frame,
            text="DizqueTV",
            variable=self.platform_var,
            value="dizquetv",
            command=self.update_url_placeholder,
        )
        dizquetv_radio.pack(side="left", padx=5)

        tunarr_radio = ttk.Radiobutton(
            platform_frame,
            text="Tunarr",
            variable=self.platform_var,
            value="tunarr",
            command=self.update_url_placeholder,
        )
        tunarr_radio.pack(side="left", padx=5)

        # Platform URL
        self.url_label = ttk.Label(self, text="Platform URL:")
        self.url_label.pack(pady=3)
        self.platform_url_entry = ttk.Entry(self)
        self.platform_url_entry.insert(0, "eg. http://localhost:17685")
        self.platform_url_entry.pack(pady=3)

        self.status_label = tk.Label(
            self,
            text="Status: Idle",
            foreground="darkgray",
            font=("Arial", 16, "bold"),
            relief="flat",
        )
        self.status_label.pack(pady=10, padx=10, fill="x")

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        toggle_button = ttk.Button(
            button_frame, text="Toggle Dark Mode", command=self.controller.toggle_theme
        )
        toggle_button.pack(side="left", padx=5, pady=5)

        self.skip_button = ttk.Button(
            button_frame, text="Skip", command=lambda: controller.show_frame("Page2")
        )
        self.skip_button.pack(side="right", padx=5, pady=5)

        self.continue_button = ttk.Button(
            button_frame, text="Continue", command=self.on_continue_button_click
        )

    def update_status_label_handler(self, status):
        self.status_label.config(text=f"Status: {status}")

    def login_to_plex(self):
        print("You pressed the Plex login button")
        self.media_server_type = "plex"
        self.logic.login_to_plex()

    def login_to_jellyfin(self):
        print("You pressed the Jellyfin login button")
        self.media_server_type = "jellyfin"

        # Show Jellyfin URL entry if hidden
        self.jellyfin_url_frame.pack(pady=3)

        # Get server URL from input field
        server_url = self.jellyfin_url_entry.get()
        if not server_url or server_url.startswith("e.g.,"):
            print("Please enter a valid Jellyfin server URL first.")
            return

        self.logic.login_to_jellyfin(server_url)

    def handle_plex_auth_url_update(self, data):
        print(f"Page1: Received Plex auth URL from LogicController - opening browser")
        self.open_auth_url(data)

    def handle_jellyfin_auth_url_update(self, data):
        print(
            f"Page1: Received Jellyfin auth URL from LogicController - opening browser"
        )
        self.open_auth_url(data)

    def handle_plex_servers_update(self, data):
        print(f"Page1: Received plex_servers update: {data}")
        try:
            server_list = json.loads(data) if isinstance(data, str) else data
            self.plex_servers = server_list
            self.server_dropdown["values"] = server_list
            if (
                server_list
                and len(server_list) > 0
                and self.server_dropdown.get() == "Select a Server"
            ):
                pass
        except json.JSONDecodeError as e:
            print(f"Error decoding plex_servers JSON: {e}")
            self.server_dropdown["values"] = []
        except Exception as e:
            print(f"Error updating plex_servers dropdown: {e}")
            self.server_dropdown["values"] = []

    def handle_jellyfin_servers_update(self, data):
        print(f"Page1: Received jellyfin_servers update: {data}")
        try:
            server_list = json.loads(data) if isinstance(data, str) else data
            self.jellyfin_servers = server_list
            self.server_dropdown["values"] = server_list
            if (
                server_list
                and len(server_list) > 0
                and self.server_dropdown.get() == "Select a Server"
            ):
                pass
        except json.JSONDecodeError as e:
            print(f"Error decoding jellyfin_servers JSON: {e}")
            self.server_dropdown["values"] = []
        except Exception as e:
            print(f"Error updating jellyfin_servers dropdown: {e}")
            self.server_dropdown["values"] = []

    def handle_plex_libraries_update(self, data):
        print(f"Page1: Received plex_libraries update: {data}")
        try:
            library_list = json.loads(data) if isinstance(data, str) else data
            self.plex_libraries = library_list
            self.anime_library_dropdown["values"] = library_list
            self.library_dropdown["values"] = library_list
        except json.JSONDecodeError as e:
            print(f"Error decoding plex_libraries JSON: {e}")
            self.anime_library_dropdown["values"] = []
            self.library_dropdown["values"] = []
        except Exception as e:
            print(f"Error updating plex_libraries dropdown: {e}")
            self.anime_library_dropdown["values"] = []
            self.library_dropdown["values"] = []

    def handle_jellyfin_libraries_update(self, data):
        print(f"Page1: Received jellyfin_libraries update: {data}")
        try:
            library_list = json.loads(data) if isinstance(data, str) else data
            self.jellyfin_libraries = library_list
            self.anime_library_dropdown["values"] = library_list
            self.library_dropdown["values"] = library_list
        except json.JSONDecodeError as e:
            print(f"Error decoding jellyfin_libraries JSON: {e}")
            self.anime_library_dropdown["values"] = []
            self.library_dropdown["values"] = []
        except Exception as e:
            print(f"Error updating jellyfin_libraries dropdown: {e}")
            self.anime_library_dropdown["values"] = []
            self.library_dropdown["values"] = []

    def handle_media_server_type_update(self, server_type):
        """Handle media server type change and update platform compatibility"""
        try:
            print(f"Media server type changed to: {server_type}")
            self.media_server_type = server_type

            # Update platform button states based on server type
            if server_type == "jellyfin":
                # Disable DizqueTV when Jellyfin is selected
                self.dizquetv_button.config(state="disabled")

                # Auto-select Tunarr
                if (
                    hasattr(self, "selected_platform")
                    and self.selected_platform == "dizquetv"
                ):
                    self.on_platform_change("tunarr")

                print("DizqueTV disabled: not compatible with Jellyfin. Using Tunarr.")
            else:
                # Re-enable DizqueTV for Plex
                self.dizquetv_button.config(state="normal")

        except Exception as e:
            print(f"Error handling media server type update: {e}")

    def handle_new_server_choices_update(self, data):
        print(f"Page1: Received new_server_choices update: {data}")

    def handle_new_library_choices_update(self, data):
        print(f"Page1: Received new_library_choices update: {data}")

    def open_auth_url(self, auth_url):
        self.logic.open_auth_url(auth_url)

    def update_status_label(self, status):
        self.status_label.config(text=f"Status: {status}")

    def show_continue_button(self):
        if self.libraries_selected == 2:
            self.skip_button.pack_forget()
            self.continue_button.pack(side="right", padx=5, pady=5)

    def add_1_to_libraries_selected(self, event):
        self.libraries_selected += 1
        self.show_continue_button()

    def update_url_placeholder(self):
        self.platform_url_entry.delete(0, tk.END)
        if self.platform_var.get() == "dizquetv":
            self.platform_url_entry.insert(0, "eg. http://localhost:17685")
        else:
            self.platform_url_entry.insert(0, "eg. http://localhost:8000")

    def on_continue_button_click(self):
        selected_anime_library = self.plex_anime_library_dropdown.get()
        selected_toonami_library = self.plex_library_dropdown.get()
        platform_url = self.platform_url_entry.get()
        platform_type = self.platform_var.get()
        self.logic.on_continue_first(
            selected_anime_library,
            selected_toonami_library,
            platform_url,
            platform_type,
        )
        self.controller.show_frame("Page3")


class Page2(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.logic = logic

        self.logic.subscribe_to_updates(
            "status_updates", self.update_status_label_handler
        )

        label = ttk.Label(self, text="Enter your details:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        # Add status_label initialization
        self.status_label = tk.Label(
            self,
            text="Status: Idle",
            foreground="darkgray",
            font=("Arial", 16, "bold"),
            relief="flat",
        )
        self.status_label.pack(pady=10, padx=10, fill="x")

        plex_url_label = ttk.Label(self, text="Plex URL:")
        plex_url_label.pack(pady=3)
        self.plex_url_entry = ttk.Entry(self)
        self.plex_url_entry.insert(0, "eg. http://localhost:32400")
        self.plex_url_entry.pack(pady=3)

        plex_token_label = ttk.Label(self, text="Plex Token:")
        plex_token_label.pack(pady=3)
        self.plex_token_entry = ttk.Entry(self)
        self.plex_token_entry.insert(0, "eg. xxxxxxxxxxxxxx")
        self.plex_token_entry.pack(pady=3)

        plex_anime_library_name_label = ttk.Label(
            self, text="Existing Plex Anime Library Name:"
        )
        plex_anime_library_name_label.pack(pady=3)
        self.plex_anime_library_name_entry = ttk.Entry(self)
        self.plex_anime_library_name_entry.insert(0, "eg. Anime")
        self.plex_anime_library_name_entry.pack(pady=3)

        plex_library_name_label = ttk.Label(self, text="Toonami Plex Library Name:")
        plex_library_name_label.pack(pady=3)
        self.plex_library_name_entry = ttk.Entry(self)
        self.plex_library_name_entry.insert(0, "eg. Toonami")
        self.plex_library_name_entry.pack(pady=3)

        dizquetv_url_label = ttk.Label(self, text="dizqueTV or tunarr URL:")
        dizquetv_url_label.pack(pady=3)
        self.dizquetv_url_entry = ttk.Entry(self)
        self.dizquetv_url_entry.insert(0, "eg. http://localhost:17685")
        self.dizquetv_url_entry.pack(pady=3)

        platform_type_label = ttk.Label(self, text="Platform Type:")
        platform_type_label.pack(pady=3)
        self.platform_type = tk.StringVar(value="dizquetv")
        dizquetv_radio = ttk.Radiobutton(
            self, text="DizqueTV", variable=self.platform_type, value="dizquetv"
        )
        dizquetv_radio.pack(pady=3)
        tunarr_radio = ttk.Radiobutton(
            self, text="Tunarr", variable=self.platform_type, value="tunarr"
        )
        tunarr_radio.pack(pady=3)

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(
            self, text="Continue", command=self.on_continue_button_click
        )
        self.continue_button.pack(side="right", padx=5, pady=5)

    def update_status_label_handler(self, status):
        self.status_label.config(text=f"Status: {status}")

    def on_continue_button_click(self):
        plex_url = self.plex_url_entry.get()
        plex_token = self.plex_token_entry.get()
        selected_anime_library = self.plex_anime_library_name_entry.get()
        selected_toonami_library = self.plex_library_name_entry.get()
        dizquetv_url = self.dizquetv_url_entry.get()
        platform_type = self.platform_type.get()
        self.logic.on_continue_second(
            plex_url,
            plex_token,
            selected_anime_library,
            selected_toonami_library,
            dizquetv_url,
            platform_type,
        )
        self.controller.show_frame("Page3")


class Page3(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.logic = logic

        self.logic.subscribe_to_updates(
            "status_updates", self.update_status_label_handler
        )

        label = ttk.Label(self, text="Select your folders:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        # Add status_label initialization
        self.status_label = tk.Label(
            self,
            text="Status: Idle",
            foreground="darkgray",
            font=("Arial", 16, "bold"),
            relief="flat",
        )
        self.status_label.pack(pady=10, padx=10, fill="x")

        self.anime_folder_entry = ttk.Entry(self)
        self.anime_folder_entry.pack(pady=3)
        anime_button = ttk.Button(
            self,
            text="Browse Anime Folder",
            command=lambda: self.anime_folder_entry.insert(
                0, filedialog.askdirectory()
            ),
        )
        anime_button.pack(pady=3)

        self.bump_folder_entry = ttk.Entry(self)
        self.bump_folder_entry.pack(pady=3)
        bump_button = ttk.Button(
            self,
            text="Browse Bump Folder",
            command=lambda: self.bump_folder_entry.insert(0, filedialog.askdirectory()),
        )
        bump_button.pack(pady=3)

        self.special_bump_folder_entry = ttk.Entry(self)
        self.special_bump_folder_entry.pack(pady=3)
        special_bump_button = ttk.Button(
            self,
            text="Browse Special Bump Folder",
            command=lambda: self.special_bump_folder_entry.insert(
                0, filedialog.askdirectory()
            ),
        )
        special_bump_button.pack(pady=3)

        self.working_folder_entry = ttk.Entry(self)
        self.working_folder_entry.pack(pady=3)
        working_button = ttk.Button(
            self,
            text="Browse Working Folder",
            command=lambda: self.working_folder_entry.insert(
                0, filedialog.askdirectory()
            ),
        )
        working_button.pack(pady=3)

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(
            self, text="Continue", command=self.on_continue_button_click
        )
        self.continue_button.pack(side="right", padx=5, pady=5)

    def update_status_label_handler(self, status):
        self.status_label.config(text=f"Status: {status}")

    def on_continue_button_click(self):
        anime_folder = self.anime_folder_entry.get()
        bump_folder = self.bump_folder_entry.get()
        special_bump_folder = self.special_bump_folder_entry.get()
        working_folder = self.working_folder_entry.get()
        self.logic.on_continue_third(
            anime_folder, bump_folder, special_bump_folder, working_folder
        )
        self.controller.show_frame("Page4")


class Page4(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.logic = logic
        self.root_window = parent
        self.dont_move = False
        self.filtered_files_action = tk.StringVar(value="move")

        self.logic.subscribe_to_updates("status_updates", self.update_status_label)

        label = ttk.Label(self, text="Prepare Your Content:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        prepare_button = ttk.Button(
            self,
            text="Prepare my shows and bumps to be cut",
            command=self.prepare_my_shows,
        )
        prepare_button.pack(pady=3)

        get_plex_timestamps_button = ttk.Button(
            self, text="Get Plex Timestamps", command=self.logic.get_plex_timestamps
        )
        get_plex_timestamps_button.pack(pady=3)

        filtered_action_frame = ttk.LabelFrame(self, text="Filtered Shows Action")
        filtered_action_frame.pack(fill="x", padx=10, pady=5)

        move_files_radio = ttk.Radiobutton(
            filtered_action_frame,
            text="Move Files (Legacy)",
            variable=self.filtered_files_action,
            value="move",
        )
        move_files_radio.pack(side="left", padx=5, pady=5)

        prepopulate_radio = ttk.Radiobutton(
            filtered_action_frame,
            text="Prepopulate Selection",
            variable=self.filtered_files_action,
            value="prepopulate",
        )
        prepopulate_radio.pack(side="left", padx=5, pady=5)

        process_filtered_button = ttk.Button(
            self, text="Process Filtered Shows", command=self.process_filtered_shows
        )
        process_filtered_button.pack(pady=3)

        self.status_label = tk.Label(
            self,
            text="Status: Idle",
            foreground="darkgray",
            font=("Arial", 16, "bold"),
            relief="flat",
        )
        self.status_label.pack(pady=10, padx=10, fill="x")

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(
            self, text="Continue", command=self.on_continue_button_click
        )

        self.continue_button.pack(side="right", padx=5, pady=5)

    def process_filtered_shows(self):
        prepopulate = self.filtered_files_action.get() == "prepopulate"
        self.logic.move_filtered(prepopulate=prepopulate)

    def on_continue_button_click(self):
        self.logic.on_continue_fourth()
        self.controller.show_frame("Page5")

    def update_status_label(self, status):
        self.status_label.config(text=f"Status: {status}")

    def prepare_my_shows(self):
        self.logic.prepare_content(self.display_show_selection)

    def display_show_selection(self, unique_show_names):
        selected_shows = []

        def on_continue():
            for show, var in zip(sorted_unique_show_names, checkboxes):
                if var.get():
                    selected_shows.append(show)
            selection_window.destroy()

        selection_window = tk.Toplevel(self.root_window)
        selection_window.title("Select Shows")

        frame = tk.Frame(selection_window)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        checkbox_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=checkbox_frame, anchor="nw")

        sorted_unique_show_names = sorted(unique_show_names)

        checkboxes = [tk.IntVar(value=1) for _ in sorted_unique_show_names]
        for show, var in zip(sorted_unique_show_names, checkboxes):
            ttk.Checkbutton(checkbox_frame, text=show, variable=var).pack(anchor="w")

        ttk.Button(selection_window, text="Continue", command=on_continue).pack()

        self.root_window.wait_window(selection_window)

        return selected_shows

    def load_filtered_files_handler(self, data):
        try:
            files = json.loads(data) if isinstance(data, str) else data
            self.load_filtered_files(files)
        except json.JSONDecodeError as e:
            print(f"Error decoding filtered_files JSON: {e}")
            self.load_filtered_files([])
        except Exception as e:
            print(f"Error in load_filtered_files_handler: {e}")
            self.load_filtered_files([])

    def load_filtered_files(self, filtered_files):
        if not filtered_files:
            return

        filtered_count = len(filtered_files)
        print(f"Received {filtered_count} filtered files to display")

        self.input_mode.set("file")
        self.toggle_input_mode()

        filtered_files.sort(key=lambda x: os.path.basename(x).lower())

        print(
            f"Adding {len(filtered_files)} alphabetically sorted files to input handler"
        )
        self.logic.input_handler.add_files(filtered_files)

        self.update_file_list()

        loaded_count = len(self.logic.input_handler.get_consolidated_paths())
        print(f"Displaying {loaded_count} of {filtered_count} filtered files")

        self.TOM_logic._broadcast_status_update(
            f"Loaded {loaded_count} of {filtered_count} filtered files"
        )

        if loaded_count != filtered_count:
            messagebox.showwarning(
                "File Loading Warning",
                f"Only {loaded_count} out of {filtered_count} filtered files were loaded.\n"
                "Some files may not exist or could not be accessed.",
            )


class Page5(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.TOM_logic = logic
        self.logic = CommercialBreakerLogic()
        self.master = self
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.input_mode = tk.StringVar(value="folder")
        self.file_path_map = {}

        self.TOM_logic.subscribe_to_updates("status_updates", self.update_status_label)
        self.TOM_logic.subscribe_to_updates(
            "filtered_files", self.load_filtered_files_handler
        )
        self.TOM_logic.subscribe_to_updates(
            "cutless_state", self.handle_cutless_state_update
        )
        self.TOM_logic.subscribe_to_updates("progress_updates", self.update_progress)

        if LogicController.cutless:
            self.cutless = True
        else:
            self.cutless = False

        self.create_widgets()

    def tkraise(self):
        working_folder = self.TOM_logic._get_data("working_folder")
        cut_folder = working_folder + "/cut"
        toonami_filtered_folder = working_folder + "/toonami_filtered"

        self.set_input_output_dirs(toonami_filtered_folder, cut_folder)

        if (
            hasattr(self.TOM_logic, "filtered_files_for_selection")
            and self.TOM_logic.filtered_files_for_selection
        ):
            filtered_count = len(self.TOM_logic.filtered_files_for_selection)
            print(f"Found {filtered_count} filtered files to display")

            self.input_mode.set("file")
            self.toggle_input_mode()

            files_to_add = self.TOM_logic.filtered_files_for_selection.copy()
            self.TOM_logic.filtered_files_for_selection = []

            files_to_add.sort(key=lambda x: os.path.basename(x).lower())

            if files_to_add:
                print(
                    f"Adding {len(files_to_add)} alphabetically sorted files to input handler"
                )
                self.logic.input_handler.add_files(files_to_add)

                self.update_file_list()

                loaded_count = len(self.logic.input_handler.get_consolidated_paths())
                print(f"Displaying {loaded_count} of {filtered_count} filtered files")

                self.TOM_logic._broadcast_status_update(
                    f"Loaded {loaded_count} of {filtered_count} filtered files"
                )

                if loaded_count != filtered_count:
                    messagebox.showwarning(
                        "File Loading Warning",
                        f"Only {loaded_count} out of {filtered_count} filtered files were loaded.\n"
                        "Some files may not exist or could not be accessed.",
                    )

        super().tkraise()

    def create_widgets(self):
        self.input_mode_frame = ttk.LabelFrame(self.master, text="Input Selection Mode")
        self.input_mode_frame.pack(fill="x", padx=10, pady=5)

        self.folder_radio = ttk.Radiobutton(
            self.input_mode_frame,
            text="Folder Mode (Legacy)",
            variable=self.input_mode,
            value="folder",
            command=self.toggle_input_mode,
        )
        self.folder_radio.pack(side="left", padx=5, pady=5)

        self.file_radio = ttk.Radiobutton(
            self.input_mode_frame,
            text="File Selection Mode",
            variable=self.input_mode,
            value="file",
            command=self.toggle_input_mode,
        )
        self.file_radio.pack(side="left", padx=5, pady=5)

        self.checkbox_frame = tk.Frame(self.master)
        self.checkbox_frame.pack(side="bottom", fill="x")

        self.destructive_mode = tk.BooleanVar()
        self.destructive_mode.trace("w", self.toggle_destructive_mode)
        self.destructive_checkbox = ttk.Checkbutton(
            self.checkbox_frame, text="Destructive Mode", variable=self.destructive_mode
        )
        self.destructive_checkbox.pack(side="left")

        self.fast_mode = tk.BooleanVar()
        self.fast_mode.trace("w", self.toggle_low_power_mode)
        self.fast_checkbox = ttk.Checkbutton(
            self.checkbox_frame, text="Fast Mode", variable=self.fast_mode
        )
        self.fast_checkbox.pack(side="left")

        self.low_power_mode = tk.BooleanVar()
        self.low_power_mode.trace("w", self.toggle_fast_mode)
        self.low_power_checkbox = ttk.Checkbutton(
            self.checkbox_frame, text="Low Power Mode", variable=self.low_power_mode
        )
        self.low_power_checkbox.pack(side="left")

        self.cutless_mode = tk.BooleanVar()
        self.cutless_mode.trace("w", self.toggle_cutless_mode)
        self.cutless_checkbox = ttk.Checkbutton(
            self.checkbox_frame, text="Cutless Mode", variable=self.cutless_mode
        )
        self.update_cutless_checkbox(LogicController.cutless)

        self.directory_frame = ttk.Frame(self.master)
        self.directory_frame.pack(fill="x", padx=10, pady=5)

        self.input_frame = ttk.Frame(self.directory_frame)
        self.input_frame.pack(fill="x", pady=3)
        self.input_label = ttk.Label(
            self.input_frame, text="Input directory:", width=15
        )
        self.input_label.pack(side="left", pady=3, padx=1)
        self.input_entry = ttk.Entry(self.input_frame, textvariable=self.input_path)
        self.input_entry.pack(side="left", fill="x", expand=True, pady=3, padx=1)
        self.input_browse_btn = ttk.Button(
            self.input_frame, text="Browse...", command=self.browse_input_directory
        )
        self.input_browse_btn.pack(side="left", pady=3, padx=1)

        self.file_frame = ttk.Frame(self.master)
        self.file_list_label = ttk.Label(self.file_frame, text="Selected Files:")
        self.file_list_label.pack(anchor="w", padx=10, pady=(5, 0))

        self.file_list_frame = ttk.Frame(self.file_frame)
        self.file_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.file_scrollbar = ttk.Scrollbar(self.file_list_frame)
        self.file_scrollbar.pack(side="right", fill="y")

        self.file_listbox = tk.Listbox(
            self.file_list_frame, height=5, selectmode=tk.EXTENDED
        )
        self.file_listbox.pack(side="left", fill="both", expand=True)

        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set)
        self.file_scrollbar.config(command=self.file_listbox.yview)

        self.file_buttons_frame = ttk.Frame(self.file_frame)
        self.file_buttons_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.add_files_btn = ttk.Button(
            self.file_buttons_frame, text="Add Files", command=self.add_files
        )
        self.add_files_btn.pack(side="left", padx=5)

        self.add_folder_btn = ttk.Button(
            self.file_buttons_frame, text="Add Folder", command=self.add_folder
        )
        self.add_folder_btn.pack(side="left", padx=5)

        self.remove_files_btn = ttk.Button(
            self.file_buttons_frame,
            text="Remove Selected",
            command=self.remove_selected_files,
        )
        self.remove_files_btn.pack(side="left", padx=5)

        self.output_frame = ttk.Frame(self.directory_frame)
        self.output_frame.pack(fill="x", pady=3)
        self.output_label = ttk.Label(
            self.output_frame, text="Output directory:", width=15
        )
        self.output_label.pack(side="left", pady=3, padx=1)
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path)
        self.output_entry.pack(side="left", fill="x", expand=True, pady=3, padx=1)
        self.output_browse_btn = ttk.Button(
            self.output_frame, text="Browse...", command=self.browse_output_directory
        )
        self.output_browse_btn.pack(side="left", pady=3, padx=1)

        progress_frame = ttk.Frame(self.master)
        progress_frame.pack(padx=10, pady=10)

        progress_label = ttk.Label(progress_frame, text="Progress:")
        progress_label.grid(row=0, column=0)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=200,
            mode="determinate",
            variable=self.progress_var,
        )
        self.progress_bar.grid(row=0, column=1)

        self.status_label = ttk.Label(progress_frame, text="Idle")
        self.status_label.grid(row=1, column=1)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10)

        button_configs = [
            ("Detect", self.detect_commercials),
            ("Cut", self.cut_videos),
            ("Delete", self.delete_txt_files),
            ("Exit", self.exit_program),
        ]
        for text, cmd in button_configs:
            button = ttk.Button(button_frame, text=text, command=cmd)
            button.pack(side="left", padx=5, pady=3)

        self.continue_button = ttk.Button(
            self.checkbox_frame,
            text="Continue",
            command=lambda: [
                self.controller.show_frame("Page6"),
                self.on_continue_button_click(),
            ],
        )
        self.continue_button.pack(side="right", padx=5, pady=5)

        self.toggle_input_mode()

    def toggle_input_mode(self):
        if self.input_mode.get() == "folder":
            self.file_frame.pack_forget()
            self.input_frame.pack(fill="x", pady=3)
            self.logic.input_handler.clear_all()
            self.input_label.config(text="Input directory:")
            self.input_browse_btn.config(command=self.browse_input_directory)
        else:
            self.file_frame.pack(
                fill="both", expand=True, padx=10, pady=5, before=self.directory_frame
            )
            self.input_frame.pack_forget()
            self.input_label.config(text="Input path:")
            self.input_browse_btn.config(command=self.add_files)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=[
                (
                    "Video Files",
                    " ".join(
                        f"*{ext}"
                        for ext in self.logic.input_handler.video_file_extensions
                    ),
                )
            ],
        )

        if files:
            self.logic.input_handler.add_files(files)
            self.update_file_list()

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select a folder containing video files")

        if folder:
            self.logic.input_handler.add_folders([folder])
            self.update_file_list()

    def remove_selected_files(self):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return

        all_paths = self.logic.input_handler.get_consolidated_paths()

        selected_filenames = [self.file_listbox.get(idx) for idx in selected_indices]
        selected_paths = [
            self.file_path_map[filename]
            for filename in selected_filenames
            if filename in self.file_path_map
        ]

        files_to_keep = [p for p in all_paths if p not in selected_paths]

        self.logic.input_handler.clear_all()
        self.logic.input_handler.add_files(files_to_keep)

        self.update_file_list()

    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        self.file_path_map.clear()

        paths = self.logic.input_handler.get_consolidated_paths()

        paths.sort(key=lambda x: os.path.basename(x).lower())

        print(f"Updating file list with {len(paths)} alphabetically sorted paths")

        for path in paths:
            filename = os.path.basename(path)
            if filename in self.file_path_map:
                count = 1
                base_name, ext = os.path.splitext(filename)
                while f"{base_name} ({count}){ext}" in self.file_path_map:
                    count += 1
                filename = f"{base_name} ({count}){ext}"

            self.file_path_map[filename] = path
            self.file_listbox.insert(tk.END, filename)

    def on_continue_button_click(self):
        self.TOM_logic.on_continue_fifth()

    def set_input_output_dirs(self, input_dir, output_dir):
        self.input_path.set(input_dir)
        self.output_path.set(output_dir)

    def toggle_fast_mode(self, *args):
        if self.low_power_mode.get():
            self.fast_mode.set(False)

    def toggle_low_power_mode(self, *args):
        if self.fast_mode.get():
            self.low_power_mode.set(False)

    def toggle_cutless_mode(self, *args):
        if self.cutless_mode.get():
            self.destructive_mode.set(False)

    def toggle_destructive_mode(self, *args):
        if self.destructive_mode.get():
            self.cutless_mode.set(False)

    def browse_input_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.input_path.set(directory)
            if self.input_mode.get() == "folder":
                self.logic.input_handler.clear_all()
                self.logic.input_handler.add_folders([directory])

    def browse_output_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_path.set(directory)

    def delete_txt_files(self):
        if not self.output_path.get():
            messagebox.showerror("Error", "Please specify an output directory.")
            return
        self.logic.delete_files(self.output_path.get())
        messagebox.showinfo("Clean up", "Done!")

    def cut_videos(self):
        if self.validate_input_output_dirs():
            threading.Thread(
                target=self._run_and_notify,
                args=(
                    self.logic.cut_videos,
                    self.done_cut_videos,
                    "Cut Video",
                    self.destructive_mode.get(),
                    self.cutless_mode.get(),
                ),
            ).start()

    def detect_commercials(self):
        if self.validate_input_output_dirs():
            threading.Thread(
                target=self._run_and_notify,
                args=(
                    self.logic.detect_commercials,
                    self.done_detect_commercials,
                    "Detect Black Frames",
                    False,
                    False,
                    self.low_power_mode.get(),
                    self.fast_mode.get(),
                    self.reset_progress_bar,
                ),
            ).start()

    def validate_input_output_dirs(self):
        output_dir = self.output_path.get()

        if not output_dir:
            messagebox.showerror("Error", "Please specify an output directory.")
            return False

        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
            except:
                messagebox.showerror("Error", "Could not create output directory.")
                return False

        if not os.access(output_dir, os.W_OK):
            messagebox.showerror("Error", "Output directory is not writable.")
            return False

        if self.input_mode.get() == "file" and not self.logic.input_handler.has_input():
            messagebox.showerror(
                "Error", "No files selected. Please add files or folders."
            )
            return False

        if self.input_mode.get() == "folder":
            input_dir = self.input_path.get()
            if not input_dir:
                messagebox.showerror("Error", "Please specify an input directory.")
                return False
            if not os.path.isdir(input_dir):
                messagebox.showerror("Error", "Input directory does not exist.")
                return False

        return True

    def exit_program(self):
        main_process_pid = os.getpid()
        main_process = psutil.Process(main_process_pid)

        for child_process in main_process.children(recursive=True):
            try:
                child_process.terminate()
            except Exception:
                pass

        os._exit(0)

    def update_progress(self, current_or_data, total=None):
        if isinstance(current_or_data, dict):
            current = current_or_data.get("current", 0)
            total = current_or_data.get("total", 100)
        elif isinstance(current_or_data, (tuple, list)) and len(current_or_data) == 2:
            current, total = current_or_data
        else:
            current = current_or_data
            if total is None:
                total = 100

        if total > 0:
            percentage = (current / total) * 100
            self.progress_var.set(percentage)
        else:
            self.progress_var.set(0)
        self.update_idletasks()

    def reset_progress_bar(self):
        self.progress_var.set(0)
        self.progress_bar.update()

    def update_status(self, text):
        self.status_label.config(text=text)
        self.status_label.update()

    def _run_and_notify(
        self,
        task,
        done_callback,
        task_name,
        destructive_mode=False,
        cutless_mode=False,
        low_power_mode=False,
        fast_mode=False,
        reset_callback=None,
    ):
        self.update_status(f"Started task: {task_name}")
        if task_name == "Detect Black Frames":
            task(
                self.input_path.get(),
                self.output_path.get(),
                self.update_progress,
                self.update_status,
                low_power_mode,
                fast_mode,
                reset_callback,
            )
        elif task_name == "Cut Video":
            self.reset_progress_bar()
            task(
                self.input_path.get(),
                self.output_path.get(),
                self.update_progress,
                self.update_status,
                destructive_mode,
                cutless_mode,
            )
        self.update_status(f"Finished task: {task_name}")
        done_callback(task_name)

    @staticmethod
    def done_cut_videos(task_name):
        messagebox.showinfo(task_name, "Done!")

    @staticmethod
    def done_detect_commercials(task_name):
        messagebox.showinfo(task_name, "Done!")

    def update_status_label(self, status):
        self.status_label.config(text=status)

    def update_cutless_checkbox(self, enabled):
        if enabled:
            if not self.cutless_checkbox.winfo_ismapped():
                self.cutless_checkbox.pack(side="left")
        else:
            if self.cutless_checkbox.winfo_ismapped():
                self.cutless_checkbox.pack_forget()
            self.cutless_mode.set(False)

    def on_cutless_state_change(self, enabled):
        self.update_cutless_checkbox(enabled)

    def handle_cutless_state_update(self, enabled):
        self.on_cutless_state_change(enabled)
        if enabled:
            self.cutless_checkbox.config(state=tk.NORMAL)
        else:
            self.cutless_checkbox.config(state=tk.DISABLED)

    def load_filtered_files_handler(self, data):
        try:
            files = json.loads(data) if isinstance(data, str) else data
            self.load_filtered_files(files)
        except json.JSONDecodeError as e:
            print(f"Error decoding filtered_files JSON: {e}")
            self.load_filtered_files([])
        except Exception as e:
            print(f"Error in load_filtered_files_handler: {e}")
            self.load_filtered_files([])

    def load_filtered_files(self, filtered_files):
        if not filtered_files:
            return

        filtered_count = len(filtered_files)
        print(f"Received {filtered_count} filtered files to display")

        self.input_mode.set("file")
        self.toggle_input_mode()

        filtered_files.sort(key=lambda x: os.path.basename(x).lower())

        print(
            f"Adding {len(filtered_files)} alphabetically sorted files to input handler"
        )
        self.logic.input_handler.add_files(filtered_files)

        self.update_file_list()

        loaded_count = len(self.logic.input_handler.get_consolidated_paths())
        print(f"Displaying {loaded_count} of {filtered_count} filtered files")

        self.TOM_logic._broadcast_status_update(
            f"Loaded {loaded_count} of {filtered_count} filtered files"
        )

        if loaded_count != filtered_count:
            messagebox.showwarning(
                "File Loading Warning",
                f"Only {loaded_count} out of {filtered_count} filtered files were loaded.\n"
                "Some files may not exist or could not be accessed.",
            )


class Page6(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        label = ttk.Label(self, text="Choose Your Action:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)
        self.logic = logic

        self.logic.subscribe_to_updates(
            "status_updates", self.update_status_label_handler
        )

        what_toonami_version_label = ttk.Label(
            self, text="What Toonami Version are you making today?"
        )
        what_toonami_version_label.pack(pady=3)

        self.toonami_version = tk.StringVar()
        self.toonami_version.set("OG")
        toonami_version_dropdown = ttk.Combobox(self, textvariable=self.toonami_version)
        toonami_version_dropdown["values"] = (
            "OG",
            "2",
            "3",
            "Mixed",
            "Uncut OG",
            "Uncut 2",
            "Uncut 3",
            "Uncut Mixed",
        )
        toonami_version_dropdown.pack(pady=3)

        channel_number_label = ttk.Label(
            self, text="What channel number do you want to use?"
        )
        channel_number_label.pack(pady=3)
        self.channel_number_entry = ttk.Entry(self)
        self.channel_number_entry.insert(0, "eg. 60")
        self.channel_number_entry.pack(pady=3)

        flex_duration_label = ttk.Label(
            self,
            text="Enter your Flex duration Minutes:Seconds (How long should a commercial break be)",
        )
        flex_duration_label.pack(pady=3)
        self.flex_duration_entry = ttk.Entry(self)
        self.flex_duration_entry.insert(0, "eg. 4:20")
        self.flex_duration_entry.pack(pady=3)

        prepare_cut_anime_button = ttk.Button(
            self,
            text="Prepare Cut Anime for Lineup",
            command=self.logic.prepare_cut_anime,
        )
        prepare_cut_anime_button.pack(pady=3)

        add_special_bumps_button = ttk.Button(
            self,
            text="Add Special Bumps to Sheet",
            command=self.logic.add_special_bumps,
        )
        add_special_bumps_button.pack(pady=3)

        create_prepare_plex_button = ttk.Button(
            self, text="Prepare Plex", command=self.logic.create_prepare_plex
        )
        create_prepare_plex_button.pack(pady=3)

        self.create_toonami_channel_button_with_flex = ttk.Button(
            self,
            text="Create Toonami Channel with Flex",
            command=self.create_toonami_channel,
        )

        self.create_toonami_channel_button = ttk.Button(
            self, text="Create Toonami Channel", command=self.create_toonami_channel
        )

        self.add_flex_button = ttk.Button(self, text="Add Flex", command=self.add_flex)

        self.dynamic_buttons_frame = ttk.Frame(self)
        self.dynamic_buttons_frame.pack(pady=3)

        self.status_label = tk.Label(
            self,
            text="Status: Idle",
            foreground="darkgray",
            font=("Arial", 16, "bold"),
            relief="flat",
        )
        self.status_label.pack(pady=10, padx=10, fill="x")

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(
            self, text="Continue", command=self.on_continue_button_click
        )
        self.continue_button.pack(side="right", padx=5, pady=5)

    def tkraise(self):
        platform_type = self.logic._get_data("platform_type")

        for widget in self.dynamic_buttons_frame.winfo_children():
            widget.destroy()

        if platform_type == "tunarr":
            self.create_toonami_channel_button_with_flex = ttk.Button(
                self.dynamic_buttons_frame,
                text="Create Toonami Channel with Flex",
                command=self.create_toonami_channel,
            )
            self.create_toonami_channel_button_with_flex.pack(pady=3)
        else:
            self.create_toonami_channel_button = ttk.Button(
                self.dynamic_buttons_frame,
                text="Create Toonami Channel",
                command=self.create_toonami_channel,
            )
            self.create_toonami_channel_button.pack(pady=3)

            self.add_flex_button = ttk.Button(
                self.dynamic_buttons_frame, text="Add Flex", command=self.add_flex
            )
            self.add_flex_button.pack(pady=3)

        super().tkraise()

    def update_status_label_handler(self, status):
        self.status_label.config(text=f"Status: {status}")

    def on_continue_button_click(self):
        self.logic.on_continue_sixth()
        self.controller.show_frame("Page7")

    def update_status_label(self, status):
        self.status_label.config(text=f"Status: {status}")

    def create_toonami_channel(self):
        toonami_version = self.toonami_version.get()
        channel_number = self.channel_number_entry.get()
        flex_duration = self.flex_duration_entry.get()
        self.logic.create_toonami_channel(
            toonami_version, channel_number, flex_duration
        )

    def add_flex(self):
        channel_number = self.channel_number_entry.get()
        flex_duration = self.flex_duration_entry.get()
        self.logic.add_flex(channel_number, flex_duration)


class Page7(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.logic = logic

        self.logic.subscribe_to_updates(
            "status_updates", self.update_status_label_handler
        )

        label = ttk.Label(
            self, text="Make a new Toonami Channel:", font=("Helvetica", 24)
        )
        label.pack(pady=10, padx=10)

        self.toonami_version = tk.StringVar()
        self.toonami_version.set("OG")

        what_toonami_version_label = ttk.Label(
            self, text="What Toonami Version are you making today?"
        )
        what_toonami_version_label.pack(pady=3)

        toonami_version_dropdown = ttk.Combobox(self, textvariable=self.toonami_version)
        toonami_version_dropdown["values"] = list(config.TOONAMI_CONFIG.keys())
        toonami_version_dropdown.pack(pady=3)

        channel_number_label = ttk.Label(
            self, text="What channel number do you want to use?"
        )
        channel_number_label.pack(pady=3)
        self.channel_number_entry = ttk.Entry(self)
        self.channel_number_entry.insert(0, "eg. 60")
        self.channel_number_entry.pack(pady=3)

        flex_duration_label = ttk.Label(
            self,
            text="Enter your Flex duration Minutes:Seconds (How long should a commercial break be)",
        )
        flex_duration_label.pack(pady=3)
        self.flex_duration_entry = ttk.Entry(self)
        self.flex_duration_entry.insert(0, "eg. 3:00")
        self.flex_duration_entry.pack(pady=3)

        self.start_from_last_episode = tk.BooleanVar(value=True)
        start_from_last_episode_checkbox = ttk.Checkbutton(
            self, text="Start from last episode", variable=self.start_from_last_episode
        )
        start_from_last_episode_checkbox.pack(pady=3)

        prepare_toonami_channel_button = ttk.Button(
            self, text="Prepare Toonami Channel", command=self.prepare_toonami_channel
        )
        prepare_toonami_channel_button.pack(pady=3)

        self.dynamic_buttons_frame = ttk.Frame(self)
        self.dynamic_buttons_frame.pack(pady=3)

        self.create_toonami_channel_button_with_flex = ttk.Button(
            self,
            text="Create Toonami Channel with Flex",
            command=self.create_toonami_channel_cont,
        )

        self.create_toonami_channel_button = ttk.Button(
            self,
            text="Create Toonami Channel",
            command=self.create_toonami_channel_cont,
        )

        self.add_flex_button = ttk.Button(self, text="Add Flex", command=self.add_flex)

        self.status_label = tk.Label(
            self,
            text="Status: Idle",
            foreground="darkgray",
            font=("Arial", 16, "bold"),
            relief="flat",
        )
        self.status_label.pack(pady=10, padx=10, fill="x")

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

    def tkraise(self):
        platform_type = self.logic._get_data("platform_type")

        for widget in self.dynamic_buttons_frame.winfo_children():
            widget.destroy()

        if platform_type == "tunarr":
            self.create_toonami_channel_button_with_flex = ttk.Button(
                self.dynamic_buttons_frame,
                text="Create Toonami Channel with Flex",
                command=self.create_toonami_channel_cont,
            )
            self.create_toonami_channel_button_with_flex.pack(pady=3)
        else:
            self.create_toonami_channel_button = ttk.Button(
                self.dynamic_buttons_frame,
                text="Create Toonami Channel",
                command=self.create_toonami_channel_cont,
            )
            self.create_toonami_channel_button.pack(pady=3)

            self.add_flex_button = ttk.Button(
                self.dynamic_buttons_frame, text="Add Flex", command=self.add_flex
            )
            self.add_flex_button.pack(pady=3)

        super().tkraise()

    def update_status_label_handler(self, status):
        self.status_label.config(text=f"Status: {status}")

    def update_status_label(self, status):
        self.status_label.config(text=f"Status: {status}")

    def prepare_toonami_channel(self):
        toonami_version = self.toonami_version.get()
        start_from_last_episode = self.start_from_last_episode.get()
        self.logic.prepare_toonami_channel(start_from_last_episode, toonami_version)

    def create_toonami_channel_cont(self):
        toonami_version = self.toonami_version.get()
        channel_number = self.channel_number_entry.get()
        flex_duration = self.flex_duration_entry.get()
        self.logic.create_toonami_channel(
            toonami_version, channel_number, flex_duration
        )

    def add_flex(self):
        channel_number = self.channel_number_entry.get()
        flex_duration = self.flex_duration_entry.get()
        self.logic.add_flex(channel_number, flex_duration)


class MainApplication(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.dark_mode = True
        self.set_theme()

        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.logic = LogicController()

        for F in (Page1, Page2, Page3, Page4, Page5, Page6, Page7):
            page_name = F.__name__
            frame = F(parent=container, controller=self, logic=self.logic)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("Page1")

    def set_theme(self):
        if self.dark_mode:
            sv_ttk.set_theme("dark")
        else:
            sv_ttk.set_theme("light")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.set_theme()

    def show_frame(self, page_name):
        frame_titles = {
            "Page1": "Step 1 - Login to Plex - Welcome to the Absolution",
            "Page2": "Step 1 - Enter Details - A Little Detour",
            "Page3": "Step 2 - Select Folders - Deploy the Clydes",
            "Page4": "Step 3 - Prepare Content - Intruder Alert",
            "Page5": "Step 4 - Commercial Breaker - Toonami Will Be Right Back",
            "Page6": "Step 5 - Create your Toonami Channel - All aboard the Absolution",
            "Page7": "Step 6 - Let's Make Another Channel! - Toonami's Back Bitches",
        }

        frame = self.frames[page_name]
        frame.tkraise()
        self.title(frame_titles[page_name])


def main():
    app = MainApplication()
    try:
        app.iconbitmap(config.icon_path)
    except Exception as ex:
        print(f"Error showing icon: {ex!r}")
    app.mainloop()


if __name__ == "__main__":
    main()
