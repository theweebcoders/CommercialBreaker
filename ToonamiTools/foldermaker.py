import os


class FolderMaker:
    def __init__(self, dir_input):
        self.folders = ['cut', 'toonami_filtered']
        self.dir_input = dir_input
    def run(self):
        print(f"Starting to create folders in {self.dir_input}...")
        # Create each folder
        for folder in self.folders:
            os.makedirs(os.path.join(self.dir_input, folder), exist_ok=True)
            print(f"Created folder: {os.path.join(self.dir_input, folder)}")
        print("All folders have been successfully created.")
