import threading
import time
import os
from GUI import LogicController
from ComBreak import CommercialBreakerLogic
import config
import curses
from pathlib import Path


class CommercialBreakerCLI:
    """A class that represents the CLI of the Commercial Breaker program."""
    def __init__(self):
        self.logic = CommercialBreakerLogic()
        self.fe_logic = LogicController()
        self.working_folder = self.fe_logic._get_data("working_folder")
        
        # Convert the working folder into a Path object and construct subpaths
        self.working_folder = Path(self.working_folder)
        self.input_path = self.working_folder / "toonami_filtered"
        self.output_path = self.working_folder / "cut"
        
        self.destructive_mode = False
        self.mode = "normal"
        self.low_power_mode = False
        self.fast_mode = False
        self.progress_var = 0
        self.status_label = "Ready"
        self.stdscr = None
        self.task_complete = threading.Event()

    def update_status(self, text):
        """Update the status label if it has changed and stdscr is initialized."""
        if self.stdscr is not None and self.status_label != text:
            self.status_label = text
            self.stdscr.move(0, 0)
            self.stdscr.clrtoeol()
            self.stdscr.addstr(f"Status: {self.status_label}")
            self.stdscr.refresh()


    def status_printer(self):
        """Continuously print the status label."""
        while True:
            self.update_status(self.status_label)
            time.sleep(1)  # Update every second

    def __del__(self):
        """Safely reset the terminal before exiting."""
        try:
            if self.stdscr is not None:
                curses.nocbreak()
                self.stdscr.keypad(False)
                curses.echo()
                curses.endwin()
        except curses.error:
            pass  # Handle the exception if curses is already terminated


    def create_status_bar(self):
        """Create a permanent status bar using curses."""
        self.stdscr.move(2, 0)  # Move to the third line of the terminal to avoid the top edge
        self.stdscr.clrtoeol()  # Clear anything previously on this line
        self.stdscr.addstr("Progress: 0%")  # Initialize the status bar with 0% progress
        self.stdscr.refresh()  # Refresh the screen to show the update

    def update_status_bar(self):
        """Update the progress in the status bar using curses."""
        progress_str = f"Progress: {self.progress_var:.2f}%"
        width = curses.COLS - 1  # Get the width of the window
        padded_progress_str = progress_str.ljust(width)  # Pad the string to the full width of the window
        self.stdscr.move(2, 0)  # Move the cursor two lines below the top of the terminal
        self.stdscr.clrtoeol()  # Clear the line
        self.stdscr.addstr(padded_progress_str)  # Print the padded progress
        self.stdscr.refresh()  # Refresh the screen to show the update

    def update_progress(self, current, total):
        """Update the progress bar."""
        if total > 0:
            self.progress_var = (current / total * 100)
        else:
            self.progress_var = 0  # Set progress to 0 if total is 0 to avoid division by zero
        self.update_status_bar()

    def reset_progress_bar(self):
        """Reset the progress bar to zero."""
        self.update_progress(0, 1)

    def show_status_bar(self):
        """Show the status and progress bar."""
        self.stdscr.move(0, 0)  # Position for the status bar
        self.stdscr.clrtoeol()  # Clear the line
        self.stdscr.addstr("Status: Ready")
        self.stdscr.move(2, 0)  # Position for the progress bar
        self.stdscr.clrtoeol()
        self.stdscr.addstr("Progress: 0%")
        self.stdscr.refresh()

    def start_curses(self):
        """Start the curses window and set up the status bar."""
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.create_status_bar()

    def stop_curses(self):
        """Reset the terminal before exiting."""
        if self.stdscr is not None:
            curses.nocbreak()
            self.stdscr.keypad(False)
            curses.echo()
            curses.endwin()
            self.stdscr = None  # Reset the stdscr attribute

    def _run_and_notify(self, task, done_callback, task_name, destructive_mode=False, low_power_mode=False, fast_mode=False, reset_callback=None):
        self.task_complete.clear()  # Clear the event at the start of a new task
        try:
            self.update_status(f"Started task: {task_name}")
            if task_name == "Detect Black Frames":
                self.start_curses()
                self.show_status_bar()
                self.reset_progress_bar()
                task(self.input_path, self.output_path, self.update_progress, self.update_status, low_power_mode, fast_mode, reset_callback)
                self.stop_curses()
            elif task_name == "Cut Video":
                self.start_curses()
                self.show_status_bar()
                self.reset_progress_bar()
                task(self.input_path, self.output_path, self.update_progress, self.update_status, destructive_mode)
                self.stop_curses()
            self.update_status(f"Finished task: {task_name}")
            done_callback(task_name)
        finally:
            self.stop_curses()
            done_callback(task_name)
            self.task_complete.set()  # Set the event when the task is done

            
    def confirm(self, prompt):
        """ Simplifies confirmation prompts """
        response = input(prompt).strip().lower()
        return response == 'y'

    def choose_mode(self):
        """ Allows the user to select a processing mode with validation """
        modes = {'f': 'fast', 'l': 'low power', 'n': 'normal'}
        while True:
            mode_input = input("Choose a mode - Fast (f), Low Power (l), or Normal (n): ").strip().lower()
            if mode_input in modes:
                return modes[mode_input]
            print("Invalid input. Please choose a valid mode (f/l/n).")

    def delete_txt_files(self):
        """Delete the .txt files in the output directory."""
        if not self.output_path:
            print("Error", "Please specify an output directory.")
            return
        self.logic.delete_files(self.output_path)
        print("Clean up", "Done!")

    def cut_videos(self):
        """Split the videos at the commercial breaks."""
        if self.validate_input_output_dirs():
            threading.Thread(target=self._run_and_notify, args=(self.logic.cut_videos, self.done_cut_videos, "Cut Video", self.destructive_mode)).start()

    def detect_commercials(self):
        """Detect the commercials in the videos."""
        if self.validate_input_output_dirs():
            threading.Thread(target=self._run_and_notify, args=(self.logic.detect_commercials, self.done_detect_commercials, "Detect Black Frames", False, self.low_power_mode, self.fast_mode, self.reset_progress_bar)).start()

    def validate_input_output_dirs(self):
        """Validate the input and output directories."""
        input_dir = self.input_path
        output_dir = self.output_path
        if not (input_dir and output_dir):
            print("Please specify an input and output directory.")
            return False
        if not os.path.isdir(input_dir):
            print("Input directory does not exist.")
            return False
        if not os.access(output_dir, os.W_OK):
            print("Output directory is not writable.")
            return False
        return True

    @staticmethod
    def done_cut_videos(task_name):
        """Notify that the videos have been split."""
        print(task_name, "Done!")

    @staticmethod
    def done_detect_commercials(task_name):
        """Notify that the commercials have been detected."""
        print(task_name, "Done!")

    def commercial_breaker(self):
        # Display initial folder settings

        print("Commercial Breaker will use the following folders:")
        print(f"Anime to be cut: {self.input_path}")
        print(f"Cut anime: {self.output_path}")

        if not self.confirm("Would you like to continue with these folders? If you moved your filtered shows earlier, reply with 'y' (y/n): "):
            self.input_path = input("Enter the path to your filtered anime folder: ")
            self.output_path = input("Enter the path to your cut anime folder: ")

        # Options for destructive mode
        self.destructive_mode = self.confirm("Would you like to run Commercial Breaker in destructive mode? This mode will delete the original files after they have been cut. (y/n): ")

        # Select operating mode
        self.mode = self.choose_mode()

        # Confirm settings before proceeding
        print("The settings for Commercial Breaker are as follows:")
        print(f"Anime to be cut: {self.input_path}")
        print(f"Cut anime: {self.output_path}")
        print(f"Destructive mode: {'Enabled' if self.destructive_mode else 'Disabled'}")
        print(f"Mode: {self.mode}")

        if self.confirm("Would you like to continue with these settings? (y/n): "):
            if self.mode == "fast":
                self.low_power_mode = False
                self.fast_mode = True
            elif self.mode == "low power":
                self.low_power_mode = True
                self.fast_mode = False
            elif self.mode == "normal":
                self.low_power_mode = False
                self.fast_mode = False
        else:
            print("Restarting the setup...")
            #reset all settings to default
            self.input_path = f"{self.working_folder}\\toonami_filtered"
            self.output_path = f"{self.working_folder}\\cut"
            self.destructive_mode = False
            self.mode = "normal"
            self.run()

        print("We are ready to start processing the anime first we will detect the commercials breaks this can take a while. Would you like to continue? (y/n): ")
        if self.confirm("Would you like to continue? (y/n): "):
            self.detect_commercials()
            self.task_complete.wait()
        print("We are ready to start cutting the anime. This will take a while. Would you like to continue? (y/n): ")
        if self.confirm("Would you like to continue? (y/n): "):
            self.cut_videos()
            self.task_complete.wait()
        print("We are done processing the anime. Would you like to delete the .txt files in the output directory? (y/n): ")
        if self.confirm("Would you like to delete the .txt files in the output directory? (y/n): "):
            self.delete_txt_files()

    def run(self):
        if self.confirm("Would you like to run Commercial Breaker? This process can take a long time to complete. (y/n): "):
            self.commercial_breaker()
            
def main():
    cli = CommercialBreakerCLI()
    cli.run()

if __name__ == "__main__":
    main()