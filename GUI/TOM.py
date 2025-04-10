import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sv_ttk
from ComBreak import CommercialBreakerLogic
from GUI import LogicController
import config
import threading
import os
import psutil
import redis
import json
from queue import Queue


class Page1(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.logic = logic
        self.libraries_selected = 0

# do something to pick one
        # Start the Redis listener thread
        # -------------------------------
        if LogicController.use_redis:
            self.redis_queue = Queue()
            self.controller.start_redis_listener_thread(self.redis_queue)
            self.after(100, self.process_redis_messages)
            # -------------------------------
        # Pubsub stuff
        # ----------------
        else:
            self.logic.subscribe_to_new_server_choices(self.update_dropdown)
            self.logic.subscribe_to_new_library_choices(self.update_anime_dropdown)
            self.logic.subscribe_to_new_library_choices(self.update_toonami_dropdown)
            self.logic.subscribe_to_status_updates(self.update_status_label)
            # ----------------

        label = ttk.Label(self, text="Login with Plex", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        login_with_plex_button = ttk.Button(self, text="Login with Plex",
                                            command=self.logic.login_to_plex)
        login_with_plex_button.pack(pady=3)

        self.plex_server_name = tk.StringVar()
        self.plex_server_name.set("Select a Plex Server")
        self.plex_server_dropdown = ttk.Combobox(self)
        self.plex_server_dropdown.bind("<<ComboboxSelected>>", lambda event: self.logic.on_server_selected(self.plex_server_dropdown.get()))
        self.plex_server_dropdown.set("Select a Plex Server")
        self.plex_server_dropdown.pack(pady=3)

        self.plex_anime_library_name = tk.StringVar()
        self.plex_anime_library_name.set("Select your Anime Library")
        self.plex_anime_library_dropdown = ttk.Combobox(self, textvariable=self.plex_anime_library_name)
        self.plex_anime_library_dropdown.bind("<<ComboboxSelected>>", self.add_1_to_libraries_selected)
        self.plex_anime_library_dropdown.set("Select your Anime Library")
        self.plex_anime_library_dropdown.pack(pady=3)

        self.plex_library_name = tk.StringVar()
        self.plex_library_name.set("Select your Toonami Library")
        self.plex_library_dropdown = ttk.Combobox(self, textvariable=self.plex_library_name)
        self.plex_library_dropdown['values'] = ("Select your Toonami Library")
        self.plex_library_dropdown.bind("<<ComboboxSelected>>", self.add_1_to_libraries_selected)
        self.plex_library_dropdown.set("Select your Toonami Library")
        self.plex_library_dropdown.pack(pady=3)

        # Platform Selection Frame
        platform_frame = ttk.Frame(self)
        platform_frame.pack(pady=3)
        
        platform_label = ttk.Label(platform_frame, text="Select Platform:")
        platform_label.pack(side="left", padx=5)
        
        self.platform_var = tk.StringVar(value="dizquetv")
        dizquetv_radio = ttk.Radiobutton(platform_frame, text="DizqueTV", 
                                        variable=self.platform_var, value="dizquetv",
                                        command=self.update_url_placeholder)
        dizquetv_radio.pack(side="left", padx=5)
        
        tunarr_radio = ttk.Radiobutton(platform_frame, text="Tunarr", 
                                      variable=self.platform_var, value="tunarr",
                                      command=self.update_url_placeholder)
        tunarr_radio.pack(side="left", padx=5)

        # Platform URL
        self.url_label = ttk.Label(self, text="Platform URL:")
        self.url_label.pack(pady=3)
        self.platform_url_entry = ttk.Entry(self)
        self.platform_url_entry.insert(0, "eg. http://localhost:17685")
        self.platform_url_entry.pack(pady=3)

        self.status_label = tk.Label(self, text="Status: Idle",
                                     foreground='darkgray',
                                     font=('Arial', 16, 'bold'),
                                     relief='flat')
        self.status_label.pack(pady=10, padx=10, fill='x')

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        toggle_button = ttk.Button(button_frame, text="Toggle Dark Mode", command=self.controller.toggle_theme)
        toggle_button.pack(side="left", padx=5, pady=5)

        self.skip_button = ttk.Button(button_frame, text="Skip",
                                        command=lambda: controller.show_frame("Page2"))
        self.skip_button.pack(side="right", padx=5, pady=5)

        self.continue_button = ttk.Button(button_frame, text="Continue",
                                        command=self.on_continue_button_click)
 
 # do something to pick one       
    # Process messages from the Redis queue
    # -------------------------------------
    if LogicController.use_redis:
        def process_redis_messages(self):
            while not self.redis_queue.empty():
                message = self.redis_queue.get()
                if message['channel'].decode('utf-8') == 'status_updates':
                    self.update_status_label(message['data'].decode('utf-8'))
                elif message['channel'].decode('utf-8') == 'new_server_choices':
                    self.update_dropdown()
                elif message['channel'].decode('utf-8') == 'new_library_choices':
                    self.update_library_dropdowns()
            
            self.after(100, self.process_redis_messages)

        def update_dropdown(self, *args, **kwargs):
            try:
                message = self.redis_queue.get_nowait()
                if message['channel'].decode('utf-8') == 'plex_servers':
                    server_list = json.loads(message['data'].decode('utf-8'))
                    self.plex_server_dropdown['values'] = server_list
                else:
                    self.redis_queue.put(message)
            except self.redis_queue.empty():
                self.after(100, self.update_dropdown)
            

        def update_library_dropdowns(self, *args, **kwargs):
            try:
                message = self.redis_queue.get_nowait()
                if message['channel'].decode('utf-8') == 'plex_libraries':
                    library_list = json.loads(message['data'].decode('utf-8'))
                    self.plex_anime_library_dropdown['values'] = library_list
                    self.plex_library_dropdown['values'] = library_list
                else:
                    self.redis_queue.put(message)
            except self.redis_queue.empty():
                self.after(100, self.update_library_dropdowns)

# ---------------------------------------------------------------------


# pubsub stuff
# ----------------
    else:
        def update_dropdown(self, *args, **kwargs):
            """Callback to update the dropdown when new server choices are announced."""
            self.plex_server_dropdown['values'] = self.logic.plex_servers

        def update_anime_dropdown(self, *args, **kwargs):
            """Callback to update the dropdown when new library choices are announced."""
            self.plex_anime_library_dropdown['values'] = self.logic.plex_libraries

        def update_toonami_dropdown(self, *args, **kwargs):
            """Callback to update the dropdown when new library choices are announced."""
            self.plex_library_dropdown['values'] = self.logic.plex_libraries
# ---------------------------------


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
        """Update the URL placeholder based on selected platform"""
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
        self.logic.on_continue_first(selected_anime_library, selected_toonami_library, 
                                   platform_url, platform_type)
        self.controller.show_frame("Page3")

class Page2(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        label = ttk.Label(self, text="Enter your details:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        self.logic = logic

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

        dizquetv_url_label = ttk.Label(self, text="dizqueTV or tunarr URL:")
        dizquetv_url_label.pack(pady=3)
        self.dizquetv_url_entry = ttk.Entry(self)
        self.dizquetv_url_entry.insert(0, "eg. http://localhost:17685")
        self.dizquetv_url_entry.pack(pady=3)

        platform_type_label = ttk.Label(self, text= "Platform Type:")
        platform_type_label.pack(pady=3)
        self.platform_type = tk.StringVar(value="dizquetv")
        dizquetv_radio = ttk.Radiobutton(self, text="DizqueTV", variable=self.platform_type, value="dizquetv")
        dizquetv_radio.pack(pady=3)
        tunarr_radio = ttk.Radiobutton(self, text="Tunarr", variable=self.platform_type, value="tunarr")
        tunarr_radio.pack(pady=3)

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(self, text="Continue",
                                    command=self.on_continue_button_click)
        self.continue_button.pack(side="right", padx=5, pady=5)

    def on_continue_button_click(self):
        plex_url = self.plex_url_entry.get()
        plex_token = self.plex_token_entry.get()
        selected_anime_library = self.plex_anime_library_name_entry.get()
        selected_toonami_library = self.plex_library_name_entry.get()
        dizquetv_url = self.dizquetv_url_entry.get()
        platform_type = self.platform_type.get()
        self.logic.on_continue_second(plex_url, plex_token, selected_anime_library, selected_toonami_library, dizquetv_url, platform_type)
        self.controller.show_frame("Page3")


class Page3(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        label = ttk.Label(self, text="Select your folders:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)
        self.logic = logic

        self.anime_folder_entry = ttk.Entry(self)
        self.anime_folder_entry.pack(pady=3)
        anime_button = ttk.Button(self, text="Browse Anime Folder",
                                 command=lambda: self.anime_folder_entry.insert(0, filedialog.askdirectory()))
        anime_button.pack(pady=3)

        self.bump_folder_entry = ttk.Entry(self)
        self.bump_folder_entry.pack(pady=3)
        bump_button = ttk.Button(self, text="Browse Bump Folder",
                                command=lambda: self.bump_folder_entry.insert(0, filedialog.askdirectory()))
        bump_button.pack(pady=3)

        self.special_bump_folder_entry = ttk.Entry(self)
        self.special_bump_folder_entry.pack(pady=3)
        special_bump_button = ttk.Button(self, text="Browse Special Bump Folder",
                                        command=lambda: self.special_bump_folder_entry.insert(0, filedialog.askdirectory()))
        special_bump_button.pack(pady=3)

        self.working_folder_entry = ttk.Entry(self)
        self.working_folder_entry.pack(pady=3)
        working_button = ttk.Button(self, text="Browse Working Folder",
                                   command=lambda: self.working_folder_entry.insert(0, filedialog.askdirectory()))
        working_button.pack(pady=3)

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(self, text="Continue",
                                    command=self.on_continue_button_click)
        self.continue_button.pack(side="right", padx=5, pady=5)

    def on_continue_button_click(self):
        anime_folder = self.anime_folder_entry.get()
        bump_folder = self.bump_folder_entry.get()
        special_bump_folder = self.special_bump_folder_entry.get()
        working_folder = self.working_folder_entry.get()
        self.logic.on_continue_third(anime_folder, bump_folder, special_bump_folder, working_folder)
        self.controller.show_frame("Page4")

class Page4(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.logic = logic
        self.root_window = parent
        self.dont_move = False

    # do something to pick one
        if LogicController.use_redis:
            # Start the Redis listener thread
            # -------------------------------
            self.redis_queue = Queue()
            self.controller.start_redis_listener_thread(self.redis_queue)
            self.after(100, self.process_redis_messages)
            # -------------------------------
           
        else:
            self.logic.subscribe_to_status_updates(self.update_status_label)
            # ----------------



        label = ttk.Label(self, text="Prepare Your Content:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        prepare_button = ttk.Button(self, text="Prepare my shows and bumps to be cut",
                                    command=self.prepare_my_shows)
        prepare_button.pack(pady=3)

        get_plex_timestamps_button = ttk.Button(self, text="Get Plex Timestamps",
                                        command=self.logic.get_plex_timestamps)
        get_plex_timestamps_button.pack(pady=3)

        move_filtered_button = ttk.Button(self, text="Move Filtered Shows",
                                        command=self.logic.move_filtered)
        move_filtered_button.pack(pady=3)

        self.status_label = tk.Label(self, text="Status: Idle",
                                     foreground='darkgray',
                                     font=('Arial', 16, 'bold'),
                                     relief='flat')
        self.status_label.pack(pady=10, padx=10, fill='x')

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(self, text="Continue",
                                    command=self.on_continue_button_click)

        self.continue_button.pack(side="right", padx=5, pady=5)

    if LogicController.use_redis:
         # -------------------------------------
            def process_redis_messages(self):
                while not self.redis_queue.empty():
                    message = self.redis_queue.get()
                    if message['channel'].decode('utf-8') == 'status_updates':
                        self.update_status_label(message['data'].decode('utf-8'))
                
                self.after(100, self.process_redis_messages)
        # -------------------------------------
            # Pubsub stuff
            # ----------------

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
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        checkbox_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=checkbox_frame, anchor="nw")

        sorted_unique_show_names = sorted(unique_show_names)

        checkboxes = [tk.IntVar(value=1) for _ in sorted_unique_show_names]
        for show, var in zip(sorted_unique_show_names, checkboxes):
            ttk.Checkbutton(checkbox_frame, text=show, variable=var).pack(anchor="w")

        ttk.Button(selection_window, text="Continue", command=on_continue).pack()

        self.root_window.wait_window(selection_window)

        return selected_shows

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
        self.create_widgets()

    def tkraise(self):
        working_folder = self.TOM_logic._get_data("working_folder")
        cut_folder = working_folder + "/cut"
        toonami_filtered_folder = working_folder + "/toonami_filtered"

        self.set_input_output_dirs(toonami_filtered_folder, cut_folder)

        super().tkraise()


    def create_widgets(self):
        """Create the widgets for the GUI."""
        self.checkbox_frame = tk.Frame(self.master)
        self.checkbox_frame.pack(side="bottom", fill="x")

        self.destructive_mode = tk.BooleanVar()
        self.destructive_checkbox = ttk.Checkbutton(self.checkbox_frame, text='Destructive Mode', variable=self.destructive_mode)
        self.destructive_checkbox.pack(side="left")  # 'left' will align the checkbox to the left

        self.fast_mode = tk.BooleanVar()
        self.fast_mode.trace("w", self.toggle_low_power_mode) # Add a callback when the value changes
        self.fast_checkbox = ttk.Checkbutton(self.checkbox_frame, text='Fast Mode', variable=self.fast_mode)
        self.fast_checkbox.pack(side="left")  # 'left' will align the checkbox to the left

        self.low_power_mode = tk.BooleanVar()
        self.low_power_mode.trace("w", self.toggle_fast_mode) # Add a callback when the value changes
        self.low_power_checkbox = ttk.Checkbutton(self.checkbox_frame, text='Low Power Mode', variable=self.low_power_mode)
        self.low_power_checkbox.pack(side="left")  # 'left' will align the checkbox to the left

        widget_configs = [
            ("Input directory:", self.input_path, self.browse_input_directory),
            ("Output directory:", self.output_path, self.browse_output_directory),
        ]
        for text, var, cmd in widget_configs:
            frame = ttk.Frame(self.master)
            label = ttk.Label(frame, text=text)
            entry = ttk.Entry(frame, textvariable=var)
            button = ttk.Button(frame, text="Browse...", command=cmd)
            label.pack(side="left", pady=3, padx=1)
            entry.pack(side="left", pady=3, padx=1)
            button.pack(side="left", pady=3, padx=1)
            frame.pack()

        progress_frame = ttk.Frame(self.master)
        progress_frame.pack(padx=100, pady=50)  # adding padding around the frame

        progress_label = ttk.Label(progress_frame, text="Progress:")
        progress_label.grid(row=0, column=0)

        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=200, mode="determinate", variable=self.progress_var)
        self.progress_bar.grid(row=0, column=1)

        self.status_label = ttk.Label(progress_frame, text="Idle")
        self.status_label.grid(row=1, column=1)  # place it beneath the progress bar

        button_configs = [
            ("Detect", self.detect_commercials),
            ("Cut", self.cut_videos),
            ("Delete", self.delete_txt_files),
            ("Exit", self.exit_program),
        ]
        for text, cmd in button_configs:
            button = ttk.Button(self.master, text=text, command=cmd)
            button.pack(pady=3)

        """Add a 'Continue' button to the frame next to the checkboxes."""
        self.continue_button = ttk.Button(self.checkbox_frame, text="Continue", command=lambda: [self.controller.show_frame("Page6"), self.on_continue_button_click()])
        self.continue_button.pack(side="right", padx=5, pady=5)

    def on_continue_button_click(self):
        self.TOM_logic.on_continue_fifth()

    def set_input_output_dirs(self, input_dir, output_dir):
        self.input_path.set(input_dir)
        self.output_path.set(output_dir)

    def toggle_fast_mode(self, *args):
        if self.low_power_mode.get(): # If Low Power Mode is checked
            self.fast_mode.set(False) # Uncheck Fast Mode

    def toggle_low_power_mode(self, *args):
        if self.fast_mode.get(): # If Fast Mode is checked
            self.low_power_mode.set(False) # Uncheck Low Power Mode

    def browse_input_directory(self):
        """Open a dialog to select the input directory."""
        self.input_path.set(filedialog.askdirectory())

    def browse_output_directory(self):
        """Open a dialog to select the output directory."""
        self.output_path.set(filedialog.askdirectory())

    def delete_txt_files(self):
        """Delete the .txt files in the output directory."""
        if not self.output_path.get():
            messagebox.showerror("Error", "Please specify an output directory.")
            return
        self.logic.delete_files(self.output_path.get())
        messagebox.showinfo("Clean up", "Done!")

    def cut_videos(self):
        """Split the videos at the commercial breaks."""
        if self.validate_input_output_dirs():
            threading.Thread(target=self._run_and_notify, args=(self.logic.cut_videos, self.done_cut_videos, "Cut Video", self.destructive_mode.get())).start()

    def detect_commercials(self):
        """Detect the commercials in the videos."""
        if self.validate_input_output_dirs():
            threading.Thread(target=self._run_and_notify, args=(self.logic.detect_commercials, self.done_detect_commercials, "Detect Black Frames", False, self.low_power_mode.get(), self.fast_mode.get(), self.reset_progress_bar)).start()

    def validate_input_output_dirs(self):
        """Validate the input and output directories."""
        input_dir = self.input_path.get()
        output_dir = self.output_path.get()
        if not (input_dir and output_dir):
            messagebox.showerror("Error", "Please specify an input and output directory.")
            return False
        if not os.path.isdir(input_dir):
            messagebox.showerror("Error", "Input directory does not exist.")
            return False
        if not os.access(output_dir, os.W_OK):
            messagebox.showerror("Error", "Output directory is not writable.")
            return False
        return True

    def exit_program(self):
        """Exit the program."""
        main_process_pid = os.getpid() # Get the PID of the main process
        main_process = psutil.Process(main_process_pid)

        # Iterate through child processes and terminate them
        for child_process in main_process.children(recursive=True):
            try:
                child_process.terminate()
            except:
                pass # Handle exceptions as needed

        os._exit(0)

    def update_progress(self, current, total):
        """Update the progress bar."""
        self.progress_var.set(current / total * 100)
        self.progress_bar.update()

    def reset_progress_bar(self):
        """Reset the progress bar to zero."""
        self.progress_var.set(0)
        self.progress_bar.update()


    def update_status(self, text):
        """Update the status label."""
        self.status_label.config(text=text)
        self.status_label.update()

    def _run_and_notify(self, task, done_callback, task_name, destructive_mode=False, low_power_mode=False, fast_mode=False, reset_callback=None):
        self.update_status(f"Started task: {task_name}")
        if task_name == "Detect Black Frames":
            task(self.input_path.get(), self.output_path.get(), self.update_progress, self.update_status, low_power_mode, fast_mode, reset_callback)
        elif task_name == "Cut Video":
            self.reset_progress_bar()
            task(self.input_path.get(), self.output_path.get(), self.update_progress, self.update_status, destructive_mode)
        self.update_status(f"Finished task: {task_name}")
        done_callback(task_name)

    @staticmethod
    def done_cut_videos(task_name):
        """Notify that the videos have been split."""
        messagebox.showinfo(task_name, "Done!")

    @staticmethod
    def done_detect_commercials(task_name):
        """Notify that the commercials have been detected."""
        messagebox.showinfo(task_name, "Done!")


class Page6(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        label = ttk.Label(self, text="Choose Your Action:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)
        self.logic = logic

    # do something to pick one
        if LogicController.use_redis:
            # Start the Redis listener thread
            # -------------------------------
            self.redis_queue = Queue()
            self.controller.start_redis_listener_thread(self.redis_queue)
            self.after(100, self.process_redis_messages)
            # -------------------------------
        else:
            self.logic.subscribe_to_status_updates(self.update_status_label)
            # ----------------

        what_toonami_version_label = ttk.Label(self, text="What Toonami Version are you making today?")
        what_toonami_version_label.pack(pady=3)

        self.toonami_version = tk.StringVar()
        self.toonami_version.set("OG")
        toonami_version_dropdown = ttk.Combobox(self, textvariable=self.toonami_version)
        toonami_version_dropdown['values'] = ("OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed")
        toonami_version_dropdown.pack(pady=3)

        channel_number_label = ttk.Label(self, text="What channel number do you want to use?")
        channel_number_label.pack(pady=3)
        self.channel_number_entry = ttk.Entry(self)
        self.channel_number_entry.insert(0, "eg. 60")
        self.channel_number_entry.pack(pady=3)

        flex_duration_label = ttk.Label(self, text="Enter your Flex duration Minutes:Seconds (How long should a commercial break be)")
        flex_duration_label.pack(pady=3)
        self.flex_duration_entry = ttk.Entry(self)
        self.flex_duration_entry.insert(0, "eg. 4:20")
        self.flex_duration_entry.pack(pady=3)

        prepare_cut_anime_button = ttk.Button(self, text="Prepare Cut Anime for Lineup",
                                             command=self.logic.prepare_cut_anime)
        prepare_cut_anime_button.pack(pady=3)

        add_special_bumps_button = ttk.Button(self, text="Add Special Bumps to Sheet",
                                                command=self.logic.add_special_bumps)
        add_special_bumps_button.pack(pady=3)

        create_prepare_plex_button = ttk.Button(self, text="Prepare Plex",
                                               command=self.logic.create_prepare_plex)
        create_prepare_plex_button.pack(pady=3)

        create_toonami_channel_button = ttk.Button(self, text="Create Toonami Channel",
                                                  command=self.create_toonami_channel)
        create_toonami_channel_button.pack(pady=3)

        add_flex_button = ttk.Button(self, text="Add Flex",
                                     command=self.add_flex)
        add_flex_button.pack(pady=3)

        self.status_label = tk.Label(self, text="Status: Idle",
                                     foreground='darkgray',
                                     font=('Arial', 16, 'bold'),
                                     relief='flat')
        self.status_label.pack(pady=10, padx=10, fill='x')

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        self.continue_button = ttk.Button(self, text="Continue",
                                    command=self.on_continue_button_click)
        self.continue_button.pack(side="right", padx=5, pady=5)

    if LogicController.use_redis:
         # -------------------------------------
            def process_redis_messages(self):
                while not self.redis_queue.empty():
                    message = self.redis_queue.get()
                    if message['channel'].decode('utf-8') == 'status_updates':
                        self.update_status_label(message['data'].decode('utf-8'))
                
                self.after(100, self.process_redis_messages)
        # -------------------------------------

    def on_continue_button_click(self):
        self.logic.on_continue_sixth()
        self.controller.show_frame("Page7")

    def update_status_label(self, status):
        self.status_label.config(text=f"Status: {status}")

    def create_toonami_channel(self):
        toonami_version = self.toonami_version.get()
        channel_number = self.channel_number_entry.get()
        self.logic.create_toonami_channel(toonami_version, channel_number)

    def add_flex(self):
        channel_number = self.channel_number_entry.get()
        flex_duration = self.flex_duration_entry.get()
        self.logic.add_flex(channel_number, flex_duration)

class Page7(ttk.Frame):
    def __init__(self, parent, controller, logic):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.logic = logic

    # do something to pick one
        if LogicController.use_redis:
            # Start the Redis listener thread
            # -------------------------------
            self.redis_queue = Queue()
            self.controller.start_redis_listener_thread(self.redis_queue)
            self.after(100, self.process_redis_messages)
            # -------------------------------
        else:
            self.logic.subscribe_to_status_updates(self.update_status_label)
            # ----------------

        label = ttk.Label(self, text="Make a new Toonami Channel:", font=("Helvetica", 24))
        label.pack(pady=10, padx=10)

        self.toonami_version = tk.StringVar()
        self.toonami_version.set("OG")

        what_toonami_version_label = ttk.Label(self, text="What Toonami Version are you making today?")
        what_toonami_version_label.pack(pady=3)

        toonami_version_dropdown = ttk.Combobox(self, textvariable=self.toonami_version)
        toonami_version_dropdown['values'] = list(config.TOONAMI_CONFIG.keys())
        toonami_version_dropdown.pack(pady=3)

        channel_number_label = ttk.Label(self, text="What channel number do you want to use?")
        channel_number_label.pack(pady=3)
        self.channel_number_entry = ttk.Entry(self)
        self.channel_number_entry.insert(0, "eg. 60")
        self.channel_number_entry.pack(pady=3)

        flex_duration_label = ttk.Label(self, text="Enter your Flex duration Minutes:Seconds (How long should a commercial break be)")
        flex_duration_label.pack(pady=3)
        self.flex_duration_entry = ttk.Entry(self)
        self.flex_duration_entry.insert(0, "eg. 3:00")
        self.flex_duration_entry.pack(pady=3)

        self.start_from_last_episode = tk.BooleanVar(value=True)
        start_from_last_episode_checkbox = ttk.Checkbutton(self, text="Start from last episode", variable=self.start_from_last_episode)
        start_from_last_episode_checkbox.pack(pady=3)

        prepare_toonami_channel_button = ttk.Button(self, text="Prepare Toonami Channel", command=self.prepare_toonami_channel)
        prepare_toonami_channel_button.pack(pady=3)

        create_toonami_channel_button = ttk.Button(self, text="Create Toonami Channel", command=self.create_toonami_channel_cont)
        create_toonami_channel_button.pack(pady=3)

        self.status_label = tk.Label(self, text="Status: Idle",
                                     foreground='darkgray',
                                     font=('Arial', 16, 'bold'),
                                     relief='flat')
        self.status_label.pack(pady=10, padx=10, fill='x')

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="se", fill="x")

        add_flex_button = ttk.Button(self, text="Add Flex",
                                     command=self.add_flex)
        add_flex_button.pack(pady=3)

    if LogicController.use_redis:
        # -------------------------------------
            def process_redis_messages(self):
                while not self.redis_queue.empty():
                    message = self.redis_queue.get()
                    if message['channel'].decode('utf-8') == 'status_updates':
                        self.update_status_label(message['data'].decode('utf-8'))
                
                self.after(100, self.process_redis_messages)
        # -------------------------------------

    def update_status_label(self, status):
        self.status_label.config(text=f"Status: {status}")

    def prepare_toonami_channel(self):
        toonami_version = self.toonami_version.get()
        start_from_last_episode = self.start_from_last_episode.get()
        self.logic.prepare_toonami_channel(start_from_last_episode, toonami_version)

    def create_toonami_channel_cont(self):
        toonami_version = self.toonami_version.get()
        channel_number = self.channel_number_entry.get()
        self.logic.create_toonami_channel(toonami_version, channel_number)

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
# don't use this if not needed
# Listen for Redis updates
# ------------------------
    if LogicController.use_redis:
        def listen_for_redis_updates(self, redis_queue):
            redis_client = self.logic.redis_client
            pubsub = redis_client.pubsub()
            pubsub.subscribe('status_updates', 'new_server_choices', 'new_library_choices', 'plex_servers', 'plex_libraries')

            for message in pubsub.listen():
                if message['type'] == 'message':
                    redis_queue.put(message)

        def start_redis_listener_thread(self, redis_queue):
            threading.Thread(target=self.listen_for_redis_updates, args=(redis_queue,), daemon=True).start()
        # ------------------------

    def set_theme(self):
        if self.dark_mode:
            sv_ttk.set_theme("dark")
        else:
            sv_ttk.set_theme("light")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.set_theme()
        # Refresh frames if needed

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
        print(f'Error showing icon: {ex!r}')
    app.mainloop()


if __name__ == "__main__":
    main()
