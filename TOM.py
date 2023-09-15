from pathlib import Path
import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, IntVar
import ttkthemes as ttkthemes
import sv_ttk
from ComBreak.CommercialBreakerGUI import CommercialBreakerGUI
from ToonamiTools import *
from config import *

class Page1(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        label = ttk.Label(self, text="Login with Plex", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        # Login button
        login_with_plex_button = ttk.Button(self, text="Login with Plex",
                                            command=self.login_to_plex)
        login_with_plex_button.pack(pady=3)

        # Drop down menu for plex servers
        self.plex_server_name = tk.StringVar()
        self.plex_server_name.set("Select a Plex Server")
        self.plex_server_dropdown = ttk.Combobox(self)
        self.plex_server_dropdown.set("Select a Plex Server")
        self.plex_server_dropdown.pack(pady=3)

        # Drop down menu for selecting anime library
        self.plex_anime_library_name = tk.StringVar()
        self.plex_anime_library_name.set("Select your Anime Library")
        self.plex_anime_library_dropdown = ttk.Combobox(self, textvariable=self.plex_anime_library_name)
        self.plex_anime_library_dropdown.set("Select your Anime Library")
        self.plex_anime_library_dropdown.pack(pady=3)

        # Drop down menu for selecting toonami library
        self.plex_library_name = tk.StringVar()
        self.plex_library_name.set("Select your Toonami Library")
        self.plex_library_dropdown = ttk.Combobox(self, textvariable=self.plex_library_name)
        self.plex_library_dropdown.set("Select your Toonami Library")
        self.plex_library_dropdown.pack(pady=3)

        # Ask for DizqueTV URL
        dizquetv_url_label = ttk.Label(self, text="dizqueTV URL:")
        dizquetv_url_label.pack(pady=3)
        self.dizquetv_url_entry = ttk.Entry(self)
        self.dizquetv_url_entry.insert(0, "eg. http://localhost:17685")
        self.dizquetv_url_entry.pack(pady=3)

        # Create a new frame to hold the buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        # Dark mode toggle button
        toggle_button = ttk.Button(button_frame, text="Toggle Dark Mode", command=self.controller.toggle_theme)
        toggle_button.pack(side="left", padx=5, pady=5)

        # Initially, pack the 'Skip' button into the button_frame
        self.skip_button = ttk.Button(button_frame, text="Skip",
                                    command=lambda: controller.show_frame(Page2))
        self.skip_button.pack(side="right", padx=5, pady=5)

        # Create the 'Continue' button but don't pack it yet
        self.continue_button = ttk.Button(button_frame, text="Continue",
                                        command=self.on_continue)
        
    def on_continue(self):
        main_app = self.controller
        main_app.selected_anime_library = self.plex_anime_library_name.get()
        main_app.selected_toonami_library = self.plex_library_name.get()
        main_app.plex_url = self.library_manager.plex_url
        main_app.plex_token = self.library_manager.plex_token
        main_app.dizquetv_url = self.dizquetv_url_entry.get()
        print (main_app.dizquetv_url)
        print (main_app.plex_url)
        print (main_app.plex_token)
        print (main_app.selected_anime_library)
        print (main_app.selected_toonami_library)
        self.controller.show_frame(Page3)

    def login_to_plex(self):
        try:
            # Create PlexServerList instance, fetch token and populate dropdown
            self.server_list = PlexServerList()
            self.server_list.run()

            # Set new menu options
            new_choices = self.server_list.plex_servers
            self.plex_server_dropdown['values'] = new_choices

            # Bind an event for server selection
            self.plex_server_dropdown.bind("<<ComboboxSelected>>", self.on_server_selected)

            # Bind event for library selection
            self.plex_anime_library_dropdown.bind("<<ComboboxSelected>>", self.validate_and_update_buttons)
            self.plex_library_dropdown.bind("<<ComboboxSelected>>", self.validate_and_update_buttons)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while fetching libraries: {e}")


    def on_server_selected(self, event):
        selected_server = self.plex_server_dropdown.get()
        self.fetch_libraries(selected_server)

    def fetch_libraries(self, selected_server):
        try:
            # Create PlexLibraryManager and PlexLibraryFetcher instances
            self.library_manager = PlexLibraryManager(selected_server, self.server_list.plex_token)
            self.library_manager.run()

            self.library_fetcher = PlexLibraryFetcher(self.library_manager.plex_url, self.server_list.plex_token)
            self.library_fetcher.run()

            # Set new menu options for Anime and Toonami libraries
            new_choices = self.library_fetcher.libraries  # Replace with the actual attribute name for libraries

            self.plex_anime_library_dropdown['values'] = new_choices
            self.plex_library_dropdown['values'] = new_choices

            # Bind event for library selection
            self.plex_anime_library_dropdown.bind("<<ComboboxSelected>>", self.validate_and_update_buttons)
            self.plex_library_dropdown.bind("<<ComboboxSelected>>", self.validate_and_update_buttons)

        except Exception as e:  # Replace with more specific exceptions if known
            messagebox.showerror("Error", f"An error occurred while fetching libraries: {e}")

    
    def validate_and_update_buttons(self, *args):
        selected_anime_library = self.plex_anime_library_name.get()
        selected_toonami_library = self.plex_library_name.get()
        
        # Debugging: Print the current selected libraries
        print(f"Selected Anime Library: {selected_anime_library}")
        print(f"Selected Toonami Library: {selected_toonami_library}")

        if selected_anime_library != "Select your Anime Library" and selected_toonami_library != "Select your Toonami Library":
            self.skip_button.pack_forget()
            self.continue_button.pack(side="right", padx=5, pady=5)
        else:
            self.continue_button.pack_forget()
            self.skip_button.pack(side="right", padx=5, pady=5)



class Page2(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        label = ttk.Label(self, text="Enter your details:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

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

        plex_anime_library_name_label = ttk.Label(self, text="Existing Plex Anime Library Name:")
        plex_anime_library_name_label.pack(pady=3)
        self.plex_anime_library_name_entry = ttk.Entry(self)
        self.plex_anime_library_name_entry.insert(0, "eg. Anime")
        self.plex_anime_library_name_entry.pack(pady=3)

        plex_library_name_label = ttk.Label(self, text="Toonami Plex Library Name:")
        plex_library_name_label.pack(pady=3)
        self.plex_library_name_entry = ttk.Entry(self)
        self.plex_library_name_entry.insert(0, "eg. Toonami")
        self.plex_library_name_entry.pack(pady=3)

        dizquetv_url_label = ttk.Label(self, text="dizqueTV URL:")
        dizquetv_url_label.pack(pady=3)
        self.dizquetv_url_entry = ttk.Entry(self)
        self.dizquetv_url_entry.insert(0, "eg. http://localhost:17685")
        self.dizquetv_url_entry.pack(pady=3)

        # Create a new frame to hold the button
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        # Create the 'Continue' button but don't pack it yet
        self.continue_button = ttk.Button(self, text="Continue",
                                    command=self.on_continue)
        #pad it 5 pixels from the right and bottom edges of the button_frame
        self.continue_button.pack(side="right", padx=5, pady=5)
        
    def on_continue(self):
        main_app = self.controller
        main_app.selected_anime_library = self.plex_anime_library_name_entry.get()
        main_app.selected_toonami_library = self.plex_library_name_entry.get()
        main_app.plex_url = self.plex_url_entry.get()
        main_app.plex_token = self.plex_token_entry.get()
        main_app.dizquetv_url = self.dizquetv_url_entry.get()
        self.controller.show_frame(Page3)

class Page3(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        label = ttk.Label(self, text="Select your folders:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        self.anime_folder_entry = ttk.Entry(self)
        self.anime_folder_entry.pack(pady=3)
        anime_button = ttk.Button(self, text="Browse Anime Folder",
                                 command=lambda: self.browse_folder(self.anime_folder_entry))
        anime_button.pack(pady=3)

        self.bump_folder_entry = ttk.Entry(self)
        self.bump_folder_entry.pack(pady=3)
        bump_button = ttk.Button(self, text="Browse Bump Folder",
                                command=lambda: self.browse_folder(self.bump_folder_entry))
        bump_button.pack(pady=3)

        self.special_bump_folder_entry = ttk.Entry(self)
        self.special_bump_folder_entry.pack(pady=3)
        special_bump_button = ttk.Button(self, text="Browse Special Bump Folder",
                                        command=lambda: self.browse_folder(self.special_bump_folder_entry))
        special_bump_button.pack(pady=3)

        self.working_folder_entry = ttk.Entry(self)
        self.working_folder_entry.pack(pady=3)
        working_button = ttk.Button(self, text="Browse Working Folder",
                                   command=lambda: self.browse_folder(self.working_folder_entry))
        working_button.pack(pady=3)

        # Create a new frame to hold the button
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        # Create the 'Continue' button but don't pack it yet
        self.continue_button = ttk.Button(self, text="Continue",
                                    command=self.on_continue)
        #pad it 5 pixels from the right and bottom edges of the button_frame
        self.continue_button.pack(side="right", padx=5, pady=5)
        
    def on_continue(self):
        main_app = self.controller
        main_app.anime_folder = self.anime_folder_entry.get()
        main_app.bump_folder = self.bump_folder_entry.get()
        main_app.special_bump_folder = self.special_bump_folder_entry.get()
        main_app.working_folder = self.working_folder_entry.get()
        self.controller.show_frame(Page4)

        

    def browse_folder(self, entry_widget):
        folder_selected = filedialog.askdirectory()
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, folder_selected)

class Page4(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller

        self.dont_move = False  # Set to False by default


        label = ttk.Label(self, text="Prepare Your Content:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        self.dont_move_anime_var = tk.BooleanVar(value=self.dont_move)
        dont_move_anime_checkbox = ttk.Checkbutton(self, text="Don't move my anime (not recommended)",
                                                   variable=self.dont_move_anime_var)
        dont_move_anime_checkbox.pack(pady=3)

        prepare_button = ttk.Button(self, text="Prepare my shows and bumps to be cut",
                                    command=self.prepare_content)
        prepare_button.pack(pady=3)

        get_plex_timestamps_button = ttk.Button(self, text="Get Plex Timestamps",
                                        command=self.get_plex_timestamps)
        get_plex_timestamps_button.pack(pady=3)
        
        # Create a new frame to hold the button
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(self, text="Continue",
                                    command=lambda: controller.show_frame(Page5))

        self.continue_button.pack(side="right", padx=5, pady=5)

    def prepare_content(self):
        # Update the values based on the current state of the checkboxes
        self.dont_move = self.dont_move_anime_var.get()
        main_app = self.controller
        working_folder = main_app.working_folder
        anime_folder = main_app.anime_folder
        bump_folder = main_app.bump_folder
        toonami_folder = working_folder + "/toonami" 
        nice_bumps = working_folder + "/nice_bumps"
        merger_bumps_list_1 = 'multibumps_v2_data_reordered'
        merger_bumps_list_2 = 'multibumps_v3_data_reordered'
        merger_bumps_list_3 = 'multibumps_v9_data_reordered'
        merger_bumps_list_4 = 'multibumps_v8_data_reordered'
        merger_out_1 = 'lineup_v2_uncut'
        merger_out_2 = 'lineup_v3_uncut'
        merger_out_3 = 'lineup_v9_uncut'
        merger_out_4 = 'lineup_v8_uncut'
        uncut_encoder_out = 'uncut_encoded_data'
        filter_output_folder = working_folder + "/toonami_filtered/"
        fmaker = FolderMaker(working_folder)
        easy_checker = ToonamiChecker(main_app, anime_folder)
        easy_mover = FileMover(toonami_folder, self.dont_move)
        lineup_prep = MediaProcessor(bump_folder, nice_bumps)
        easy_encoder = ToonamiEncoder()
        uncutencoder = UncutEncoder(toonami_folder)
        ml = Multilineup()
        merger = ShowScheduler(uncut=True)
        fmove = FilterAndMove()
        fmaker.run()
        easy_checker.run()
        easy_mover.run()
        lineup_prep.run()
        easy_encoder.encode_and_save()
        ml.reorder_all_tables()
        uncutencoder.run()
        merger.run(merger_bumps_list_1, uncut_encoder_out, merger_out_1)
        merger.run(merger_bumps_list_2, uncut_encoder_out, merger_out_2)
        merger.run(merger_bumps_list_3, uncut_encoder_out, merger_out_3)
        merger.run(merger_bumps_list_4, uncut_encoder_out, merger_out_4)
        fmove.run(filter_output_folder, self.dont_move)
        messagebox.showinfo("Information","Your Anime is ready to be cut!")

    def get_plex_timestamps(self):
        main_app = self.controller
        working_folder = main_app.working_folder
        toonami_filtered_folder = working_folder + "/toonami"
        plex_ts_url = main_app.plex_url
        plex_ts_token = main_app.plex_token
        plex_ts_anime_library_name = main_app.selected_anime_library
        GetTimestamps = GetPlexTimestamps(plex_ts_url, plex_ts_token, plex_ts_anime_library_name, toonami_filtered_folder)
        GetTimestamps.run() # Calling the run method on the instance
        messagebox.showinfo("Information","Get Plex Timestamps has finished!")

class Page5(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.commercial_breaker = CommercialBreakerGUI(self)
        self.controller = controller
        self.commercial_breaker.add_continue_button(command=lambda: controller.show_frame(Page6))

    def tkraise(self):
        main_app = self.controller
        working_folder = main_app.working_folder
        cut_folder = working_folder + "/cut"
        toonami_filtered_folder = working_folder + "/toonami_filtered"

        # Set the input and output directories in the Commercial Breaker GUI
        self.commercial_breaker.set_input_output_dirs(toonami_filtered_folder, cut_folder)

        # Call the original tkraise method to display the frame
        super().tkraise()

class Page6(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        label = ttk.Label(self, text="Choose Your Action:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        what_toonami_version_label = ttk.Label(self, text="What Toonami Version are you making today?")
        what_toonami_version_label.pack(pady=3)

        self.toonami_version = tk.StringVar()
        self.toonami_version.set("OG")
        toonami_version_dropdown = ttk.Combobox(self, textvariable=self.toonami_version)
        toonami_version_dropdown['values'] = ("OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed")
        toonami_version_dropdown.set("OG")
        toonami_version_dropdown.set("OG")
        toonami_version_dropdown.pack(pady=3)

        channel_number_label = ttk.Label(self, text="What channel number do you want to use?")
        channel_number_label.pack(pady=3)
        self.channel_number_entry = ttk.Entry(self)
        self.channel_number_entry.insert(0, "eg. 60")
        self.channel_number_entry.pack(pady=3)

        prepare_cut_anime_button = ttk.Button(self, text="Prepare Cut Anime for Lineup",
                                             command=self.prepare_cut_anime)
        prepare_cut_anime_button.pack(pady=3)

        add_special_bumps_button = ttk.Button(self, text="Add Special Bumps to Sheet",
                                                command=self.add_special_bumps)
        add_special_bumps_button.pack(pady=3)

        create_prepare_plex_button = ttk.Button(self, text="Prepare Plex",
                                               command=self.create_prepare_plex)
        create_prepare_plex_button.pack(pady=3)

        create_toonami_channel_button = ttk.Button(self, text="Create Toonami Channel",
                                                  command=self.create_toonami_channel)
        create_toonami_channel_button.pack(pady=3)

        # Create a new frame to hold the button
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(self, text="Continue",
                                    command=lambda: controller.show_frame(Page7))

        self.continue_button.pack(side="right", padx=5, pady=5)


    def prepare_cut_anime(self):
        main_app = self.controller
        working_folder = main_app.working_folder
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
        commercial_injector_prep = AnimeFileOrganizer(cut_folder)
        commercial_injector = LineupLogic()
        BIC = BlockIDCreator()
        merger = ShowScheduler(apply_ns3_logic=True)
        commercial_injector_prep.organize_files()
        commercial_injector.generate_lineup()
        BIC.run()
        merger.run(merger_bumps_list_1, commercial_injector_out, merger_out_1)
        merger.run(merger_bumps_list_2, commercial_injector_out, merger_out_2)
        merger.run(merger_bumps_list_3, commercial_injector_out, merger_out_3)
        merger.run(merger_bumps_list_4, commercial_injector_out, merger_out_4)
        messagebox.showinfo("Information","Cut Anime is ready for Plex!")

    def add_special_bumps(self):
        main_app = self.controller
        special_bump_folder = main_app.special_bump_folder
        sepcial_bump_processor = FileProcessor(special_bump_folder)
        sepcial_bump_processor.process_files()

    def create_prepare_plex(self):
        main_app = self.controller
        plex_url_plex_splitter = main_app.plex_url
        plex_token_plex_splitter = main_app.plex_token
        plex_library_name_plex_splitter = main_app.selected_toonami_library
        plex_splitter = PlexAutoSplitter(plex_url_plex_splitter, plex_token_plex_splitter, plex_library_name_plex_splitter)
        plex_splitter.split_merged_items()
        plex_rename_split = PlexLibraryUpdater(plex_url_plex_splitter, plex_token_plex_splitter, plex_library_name_plex_splitter)
        plex_rename_split.update_titles()
        messagebox.showinfo("Success", "Prepare Plex Complete!")

    def create_toonami_channel(self):
        main_app = self.controller
        plex_url = main_app.plex_url
        plex_token = main_app.plex_token
        plex_library_name = main_app.selected_toonami_library
        toonami_version = self.toonami_version.get()
        config = TOONAMI_CONFIG.get(toonami_version, {})
        table = config["table"]
        dizquetv_url = main_app.dizquetv_url
        channel_number = self.channel_number_entry.get()
        ptod = PlexToDizqueTVSimplified(plex_url, plex_token, plex_library_name, table, dizquetv_url, channel_number)
        ptod.run()


class Page7(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller


        label = ttk.Label(self, text="Make a new Toonami Channel:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        self.toonami_version = tk.StringVar()
        self.toonami_version.set("OG")

        what_toonami_version_label = ttk.Label(self, text="What Toonami Version are you making today?")
        what_toonami_version_label.pack(pady=3)

        toonami_version_dropdown = ttk.Combobox(self, textvariable=self.toonami_version)
        toonami_version_dropdown['values'] = list(TOONAMI_CONFIG.keys())
        toonami_version_dropdown.pack(pady=3)

        channel_number_label = ttk.Label(self, text="What channel number do you want to use?")
        channel_number_label.pack(pady=3)
        self.channel_number_entry = ttk.Entry(self)
        self.channel_number_entry.insert(0, "eg. 60")
        self.channel_number_entry.pack(pady=3)

        self.start_from_last_episode = tk.BooleanVar(value=True)
        start_from_last_episode_checkbox = ttk.Checkbutton(self, text="Start from last episode", variable=self.start_from_last_episode)
        start_from_last_episode_checkbox.pack(pady=3)

        prepare_toonami_channel_button = ttk.Button(self, text="Prepare Toonami Channel", command=self.prepare_toonami_channel)
        prepare_toonami_channel_button.pack(pady=3)

        create_toonami_channel_button = ttk.Button(self, text="Create Toonami Channel", command=self.create_toonami_channel)
        create_toonami_channel_button.pack(pady=3)

        # Create a new frame to hold the button
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(self, text="Continue",
                                    command=lambda: controller.show_frame(Page8))

        self.continue_button.pack(side="right", padx=5, pady=5)


    def prepare_toonami_channel(self):
        main_app = self.controller

        toonami_version = self.toonami_version.get()
        config = TOONAMI_CONFIG_CONT.get(toonami_version, {})

        merger_bump_list = config["merger_bump_list"]
        merger_out = config["merger_out"]
        encoder_in = config["encoder_in"]
        ns3Logic = config["ns3Logic"]

        merger = ShowScheduler(reuse_episode_blocks=True, continue_from_last_used_episode_block=self.start_from_last_episode.get(), apply_ns3_logic=ns3Logic)
        merger.run(merger_bump_list, encoder_in, merger_out)

    def create_toonami_channel(self):
        main_app = self.controller

        toonami_version = self.toonami_version.get()
        config = TOONAMI_CONFIG_CONT.get(toonami_version, {})
        channel_number = self.channel_number_entry.get()
        table = config["merger_out"]
        dizquetv_url = main_app.dizquetv_url
        plex_url = main_app.plex_url
        plex_token = main_app.plex_token
        plex_library_name = main_app.selected_toonami_library

        ptod = PlexToDizqueTVSimplified(plex_url, plex_token, plex_library_name, table, dizquetv_url, channel_number)
        ptod.run()

class Page8(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller

        label = ttk.Label(self, text="Flex your Toonami Channel:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        ssh_host_label = ttk.Label(self, text="Enter The IP address for your server:")
        ssh_host_label.pack(pady=3)
        self.ssh_host_entry = ttk.Entry(self)
        self.ssh_host_entry.insert(0, "eg. 192.168.255.255")
        self.ssh_host_entry.pack(pady=3)

        ssh_user_label = ttk.Label(self, text="Enter the username for your server:")
        ssh_user_label.pack(pady=3)
        self.ssh_user_entry = ttk.Entry(self)
        self.ssh_user_entry.insert(0, "eg. root")
        self.ssh_user_entry.pack(pady=3)

        ssh_pass_label = ttk.Label(self, text="Enter the password for your server:")
        ssh_pass_label.pack(pady=3)
        self.ssh_pass_entry = ttk.Entry(self)
        self.ssh_pass_entry.insert(0, "eg. password")
        self.ssh_pass_entry.pack(pady=3)

        self.dizquetv_docker_name_label = ttk.Label(self, text="Enter the name of your dizqueTV docker container:")
        self.dizquetv_docker_name_label.pack(pady=3)
        self.dizquetv_docker_name_entry = ttk.Entry(self)
        self.dizquetv_docker_name_entry.insert(0, "eg. dizquetv")
        self.dizquetv_docker_name_entry.pack(pady=3)

        self.dizquetv_channel_number_label = ttk.Label(self, text="Enter the channel number you want to add flex to:")
        self.dizquetv_channel_number_label.pack(pady=3)
        self.dizquetv_channel_number_entry = ttk.Entry(self)
        self.dizquetv_channel_number_entry.insert(0, "eg. 60")
        self.dizquetv_channel_number_entry.pack(pady=3)

        self.dizquetv_flex_duration_label = ttk.Label(self, text="Enter the duration of the flex in Minutes:Sesconds")
        self.dizquetv_flex_duration_label.pack(pady=3)
        self.dizquetv_flex_duration_entry = ttk.Entry(self)
        self.dizquetv_flex_duration_entry.insert(0, "eg. 4:20")
        self.dizquetv_flex_duration_entry.pack(pady=3)

        add_flex_button = ttk.Button(self, text="Add Flex", command=self.add_flex)
        add_flex_button.pack(pady=3)
        

    def add_flex(self):
        ssh_host = self.ssh_host_entry.get()
        ssh_user = self.ssh_user_entry.get()
        ssh_pass = self.ssh_pass_entry.get()
        dizquetv_container_name = self.dizquetv_docker_name_entry.get()
        dizquetv_channel_number = self.dizquetv_channel_number_entry.get()
        dizquetv_flex_duration = self.dizquetv_flex_duration_entry.get()

        Flex = DizqueTVManager(ssh_host, ssh_user, ssh_pass, dizquetv_container_name, dizquetv_channel_number, dizquetv_flex_duration)
        Flex.main()

class MainApplication(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.dark_mode = True
        self.set_theme()

        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.selected_anime_library = None
        self.selected_toonami_library = None
        self.plex_url = None
        self.plex_token = None
        self.dizquetv_url = None
        self.anime_folder = None
        self.bump_folder = None
        self.special_bump_folder = None
        self.working_folder = None

        self.frames = {}
        for F in (Page1, Page2, Page3, Page4, Page5, Page6, Page7, Page8):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(Page1)

    def set_theme(self):
        if self.dark_mode:
            sv_ttk.set_theme("dark")
        else:
            sv_ttk.set_theme("light")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.set_theme()
        # Refresh frames if needed

    def show_frame(self, page_class):
        page_name = page_class.__name__
        frame_titles = {
            "Page1": "Step 1 - Login to Plex - Welcome to the Absolution",
            "Page2": "Step 1 - Enter Details - A Little Detour",
            "Page3": "Step 2 - Select Folders - Deploy the Clydes",
            "Page4": "Step 3 - Prepare Content - Intruder Alert",
            "Page5": "Step 4 - Commercial Breaker - Toonami Will Be Right Back",
            "Page6": "Step 5 - Create your Toonami Channel - All aboard the Absolution",
            "Page7": "Step 6 - Let's Make Another Channel! - Toonami's Back Bitches",
            "Page8": "Step 7 - Flex Your Toonami Channel - Commerecial Break"
        }
        
        frame = self.frames[page_name]
        frame.tkraise()
        self.title(frame_titles[page_name])

if __name__ == "__main__":
    app = MainApplication()
    app.iconbitmap(icon_path)
    app.mainloop()
