import os
import psutil
import threading
import tkinter as tk
from ComBreak.CommercialBreakerLogic import CommercialBreakerLogic
from tkinter import filedialog, messagebox, ttk


class CommercialBreakerGUI:
    """A class that represents the GUI of the Commercial Breaker program."""

    def __init__(self, master):
        self.logic = CommercialBreakerLogic()
        self.master = master
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.input_mode = tk.StringVar(value="folder")  # Default to folder mode for backward compatibility
        self.selected_files = []  # List to store selected file paths
        self.file_path_map = {}  # Dict to map displayed filenames to full paths
        self.create_widgets()

    def create_widgets(self):
        """Create the widgets for the GUI."""
        # Create a new frame for input mode selection
        self.input_mode_frame = ttk.LabelFrame(self.master, text="Input Selection Mode")
        self.input_mode_frame.pack(fill="x", padx=10, pady=5)
        
        # Radio buttons for input mode selection
        self.folder_radio = ttk.Radiobutton(
            self.input_mode_frame, 
            text="Folder Mode (Legacy)", 
            variable=self.input_mode, 
            value="folder",
            command=self.toggle_input_mode
        )
        self.folder_radio.pack(side="left", padx=5, pady=5)
        
        self.file_radio = ttk.Radiobutton(
            self.input_mode_frame, 
            text="File Selection Mode", 
            variable=self.input_mode, 
            value="file",
            command=self.toggle_input_mode
        )
        self.file_radio.pack(side="left", padx=5, pady=5)

        # Create a new frame to hold the checkboxes
        self.checkbox_frame = tk.Frame(self.master)
        self.checkbox_frame.pack(side="bottom", fill="x")

        # Destructive Mode checkbox
        self.destructive_mode = tk.BooleanVar()
        self.destructive_checkbox = ttk.Checkbutton(self.checkbox_frame, text='Destructive Mode', variable=self.destructive_mode)
        self.destructive_checkbox.pack(side="left")  # 'left' will align the checkbox to the left

        # Fast Mode checkbox
        self.fast_mode = tk.BooleanVar()
        self.fast_mode.trace("w", self.toggle_low_power_mode)  # Add a callback when the value changes
        self.fast_checkbox = ttk.Checkbutton(self.checkbox_frame, text='Fast Mode', variable=self.fast_mode)
        self.fast_checkbox.pack(side="left")  # 'left' will align the checkbox to the left

        # Low Power Mode checkbox
        self.low_power_mode = tk.BooleanVar()
        self.low_power_mode.trace("w", self.toggle_fast_mode)  # Add a callback when the value changes
        self.low_power_checkbox = ttk.Checkbutton(self.checkbox_frame, text='Low Power Mode', variable=self.low_power_mode)
        self.low_power_checkbox.pack(side="left")  # 'left' will align the checkbox to the left

        # Input/output directory selection frames
        self.directory_frame = ttk.Frame(self.master)
        self.directory_frame.pack(fill="x", padx=10, pady=5)
        
        # Input directory selection
        self.input_frame = ttk.Frame(self.directory_frame)
        self.input_frame.pack(fill="x", pady=3)
        self.input_label = ttk.Label(self.input_frame, text="Input directory:", width=15)
        self.input_label.pack(side="left", pady=3, padx=1)
        self.input_entry = ttk.Entry(self.input_frame, textvariable=self.input_path)
        self.input_entry.pack(side="left", fill="x", expand=True, pady=3, padx=1)
        self.input_browse_btn = ttk.Button(self.input_frame, text="Browse...", command=self.browse_input_directory)
        self.input_browse_btn.pack(side="left", pady=3, padx=1)
        
        # File selection frame (initially hidden)
        self.file_frame = ttk.Frame(self.master)
        self.file_list_label = ttk.Label(self.file_frame, text="Selected Files:")
        self.file_list_label.pack(anchor="w", padx=10, pady=(5,0))
        
        # Create a frame for the file listbox and its scrollbar
        self.file_list_frame = ttk.Frame(self.file_frame)
        self.file_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create scrollbar
        self.file_scrollbar = ttk.Scrollbar(self.file_list_frame)
        self.file_scrollbar.pack(side="right", fill="y")
        
        # Create listbox for selected files
        self.file_listbox = tk.Listbox(self.file_list_frame, height=5, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbar
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set)
        self.file_scrollbar.config(command=self.file_listbox.yview)
        
        # Buttons for file management
        self.file_buttons_frame = ttk.Frame(self.file_frame)
        self.file_buttons_frame.pack(fill="x", padx=10, pady=(0,5))
        
        self.add_files_btn = ttk.Button(self.file_buttons_frame, text="Add Files", command=self.add_files)
        self.add_files_btn.pack(side="left", padx=5)
        
        self.add_folder_btn = ttk.Button(self.file_buttons_frame, text="Add Folder", command=self.add_folder)
        self.add_folder_btn.pack(side="left", padx=5)
        
        self.remove_files_btn = ttk.Button(self.file_buttons_frame, text="Remove Selected", command=self.remove_selected_files)
        self.remove_files_btn.pack(side="left", padx=5)
        
        # Output directory selection
        self.output_frame = ttk.Frame(self.directory_frame)
        self.output_frame.pack(fill="x", pady=3)
        self.output_label = ttk.Label(self.output_frame, text="Output directory:", width=15)
        self.output_label.pack(side="left", pady=3, padx=1)
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path)
        self.output_entry.pack(side="left", fill="x", expand=True, pady=3, padx=1)
        self.output_browse_btn = ttk.Button(self.output_frame, text="Browse...", command=self.browse_output_directory)
        self.output_browse_btn.pack(side="left", pady=3, padx=1)

        # Progress section
        progress_frame = ttk.Frame(self.master)
        progress_frame.pack(padx=10, pady=10)

        progress_label = ttk.Label(progress_frame, text="Progress:")
        progress_label.grid(row=0, column=0)

        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=200, mode="determinate", variable=self.progress_var)
        self.progress_bar.grid(row=0, column=1)

        self.status_label = ttk.Label(progress_frame, text="Idle")
        self.status_label.grid(row=1, column=1)  # place it beneath the progress bar

        # Create action buttons
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
        
        # Initially hide the file selection frame
        self.toggle_input_mode()

    def toggle_input_mode(self):
        """Toggle between folder mode and file selection mode."""
        if self.input_mode.get() == "folder":
            self.file_frame.pack_forget()
            self.input_frame.pack(fill="x", pady=3)  # Show the input directory field
            # Clear the input handler's file list
            self.logic.input_handler.clear_all()
            # Show standard folder mode
            self.input_label.config(text="Input directory:")
            self.input_browse_btn.config(command=self.browse_input_directory)
        else:  # file mode
            self.file_frame.pack(fill="both", expand=True, padx=10, pady=5, before=self.directory_frame)
            self.input_frame.pack_forget()  # Hide the input directory field since we're selecting files directly
            self.input_label.config(text="Input path:")
            self.input_browse_btn.config(command=self.add_files)

    def add_files(self):
        """Add individual files to the file list."""
        files = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=[("Video Files", " ".join(f"*{ext}" for ext in self.logic.input_handler.video_file_extensions))]
        )
        
        if files:
            # Add new files without clearing existing ones
            self.logic.input_handler.add_files(files)
            self.update_file_list()

    def add_folder(self):
        """Add all video files from a folder to the file list."""
        folder = filedialog.askdirectory(title="Select a folder containing video files")
        
        if folder:
            # Add files from folder without clearing existing ones
            self.logic.input_handler.add_folders([folder])
            self.update_file_list()

    def remove_selected_files(self):
        """Remove selected files from the file list."""
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return
            
        # Get all currently consolidated paths
        all_paths = self.logic.input_handler.get_consolidated_paths()
        
        # Get the filename-to-path mapping for selected items
        selected_filenames = [self.file_listbox.get(idx) for idx in selected_indices]
        selected_paths = [self.file_path_map[filename] for filename in selected_filenames if filename in self.file_path_map]
        
        # Re-add the files and folders that weren't selected
        files_to_keep = [p for p in all_paths if p not in selected_paths]
        
        # Clear current files and add back only the ones to keep
        self.logic.input_handler.clear_all()
        self.logic.input_handler.add_files(files_to_keep)
        
        # Update the displayed list
        self.update_file_list()

    def update_file_list(self):
        """Update the file list display with consolidated paths from the input handler."""
        # Clear the current list
        self.file_listbox.delete(0, tk.END)
        self.file_path_map.clear()
        
        # Get all consolidated paths
        paths = self.logic.input_handler.get_consolidated_paths()
        
        # Add each path to the listbox and update the path map
        for path in paths:
            filename = os.path.basename(path)
            # Handle duplicate filenames by adding a counter
            if filename in self.file_path_map:
                count = 1
                base_name, ext = os.path.splitext(filename)
                while f"{base_name} ({count}){ext}" in self.file_path_map:
                    count += 1
                filename = f"{base_name} ({count}){ext}"
            
            self.file_path_map[filename] = path
            self.file_listbox.insert(tk.END, filename)

    def add_continue_button(self, command):
        continue_button = ttk.Button(self.master, text="Continue", command=command)
        continue_button.place(relx=1.0, rely=1.0, anchor="se")

    def set_input_output_dirs(self, input_dir, output_dir):
        self.input_path.set(input_dir)
        self.output_path.set(output_dir)

    def toggle_fast_mode(self, *args):
        if self.low_power_mode.get():  # If Low Power Mode is checked
            self.fast_mode.set(False)  # Uncheck Fast Mode

    def toggle_low_power_mode(self, *args):
        if self.fast_mode.get():  # If Fast Mode is checked
            self.low_power_mode.set(False)  # Uncheck Low Power Mode

    def browse_input_directory(self):
        """Open a dialog to select the input directory."""
        directory = filedialog.askdirectory()
        if directory:
            self.input_path.set(directory)
            # In folder mode, update the input handler with the folder
            if self.input_mode.get() == "folder":
                self.logic.input_handler.clear_all()
                self.logic.input_handler.add_folders([directory])

    def browse_output_directory(self):
        """Open a dialog to select the output directory."""
        directory = filedialog.askdirectory()
        if directory:
            self.output_path.set(directory)

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
            
        # For file mode, check if files have been selected
        if self.input_mode.get() == "file" and not self.logic.input_handler.has_input():
            messagebox.showerror("Error", "No files selected. Please add files or folders.")
            return False
            
        # For folder mode, check if input directory exists
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
        """Exit the program."""
        main_process_pid = os.getpid()  # Get the PID of the main process
        main_process = psutil.Process(main_process_pid)

        # Iterate through child processes and terminate them
        for child_process in main_process.children(recursive=True):
            try:
                child_process.terminate()
            except Exception:
                pass  # Handle exceptions as needed

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
