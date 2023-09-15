import tkinter as tk
from tkinter import filedialog, Frame
from pathlib import Path
import os
import tempfile
import shutil


class FolderMatchingTool:
    def __init__(self, root):
        self.in_folder = ""
        self.out_folder = ""
        self.current_file = None
        self.temp_files = {}
        self.text_box = None
        self.result_label = None

        root.title("Folder Matching Tool")

        tk.Button(root, text="Select Anime Folder", command=self.select_in_folder).pack()
        self.in_label = tk.Label(root, text="")
        self.in_label.pack()

        tk.Button(root, text="Select Cut Folder", command=self.select_out_folder).pack()
        self.out_label = tk.Label(root, text="")
        self.out_label.pack()

        tk.Button(root, text="Edit Timestamps", command=self.process_folders).pack()
        self.result_label = tk.Label(root, text="")
        self.result_label.pack()

    def select_in_folder(self):
        self.in_folder = filedialog.askdirectory()
        self.in_label.config(text="Selected Anime Folder: " + self.in_folder)

    def select_out_folder(self):
        self.out_folder = filedialog.askdirectory()
        self.out_label.config(text="Selected Cut Folder: " + self.out_folder)

    def display_file_contents(self, file_path):
        if self.current_file:
            with open(self.temp_files[self.current_file], 'w') as file:
                file.write(self.text_box.get(1.0, tk.END))

        if file_path not in self.temp_files:
            self.temp_files[file_path] = tempfile.NamedTemporaryFile(mode='w+', delete=False).name
            with open(file_path, 'r') as original_file, open(self.temp_files[file_path], 'w') as temp_file:
                shutil.copyfileobj(original_file, temp_file)

        with open(self.temp_files[file_path], 'r') as file:
            self.text_box.delete(1.0, tk.END)
            self.text_box.insert(tk.END, file.read())

        self.current_file = file_path

    def save_changes(self):
        for original_file, temp_file_path in self.temp_files.items():
            with open(original_file, 'w') as original, open(temp_file_path, 'r') as temp:
                shutil.copyfileobj(temp, original)
            os.unlink(temp_file_path)

        self.result_label.config(text="Changes Saved!")

    def process_folders(self):
        self.temp_files = {}

        for subdir, _, files in os.walk(self.in_folder):
            for file_name in files:
                if file_name.endswith(".mkv"):
                    relative_path = os.path.relpath(subdir, self.in_folder)
                    out_subdir = os.path.join(self.out_folder, relative_path)
                    txt_file_path = os.path.join(out_subdir, file_name + ".txt")

                    if not os.path.exists(txt_file_path):
                        Path(out_subdir).mkdir(parents=True, exist_ok=True)
                        open(txt_file_path, 'w').close()

        timestamps_window = tk.Toplevel(root)
        timestamps_window.title("Timestamps")

        self.text_box = tk.Text(timestamps_window, width=40)
        self.text_box.pack(side=tk.LEFT)

        main_files_frame = Frame(timestamps_window)
        main_files_frame.pack(side=tk.RIGHT)

        for subdir, _, files in os.walk(self.out_folder):
            folder_frame = Frame(main_files_frame, relief="solid", borderwidth=1)
            folder_frame.pack(pady=5)
            tk.Label(folder_frame, text=os.path.basename(subdir)).pack()  # Display folder name

            for file_name in files:
                if file_name.endswith(".mkv.txt"):
                    file_path = os.path.join(subdir, file_name)
                    file_frame = Frame(folder_frame, relief="solid", borderwidth=1)
                    file_frame.pack(pady=2)
                    file_label = tk.Label(file_frame, text=file_name)
                    file_label.bind("<Button-1>", lambda e, path=file_path: self.display_file_contents(path))
                    file_label.pack()

        tk.Button(timestamps_window, text="Save", command=self.save_changes).pack(side=tk.BOTTOM, anchor=tk.SE)

        self.result_label.config(text="Processing Complete!")

root = tk.Tk()
app = FolderMatchingTool(root)
root.mainloop()