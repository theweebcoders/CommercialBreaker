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
        self.create_widgets()

    def create_widgets(self):
        """Create the widgets for the GUI."""
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
