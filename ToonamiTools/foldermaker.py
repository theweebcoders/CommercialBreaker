import os
from API.utils.ErrorManager import get_error_manager


class FolderMaker:
    def __init__(self, dir_input):
        self.folders = ['cut', 'toonami_filtered']
        self.dir_input = dir_input
        self.error_manager = get_error_manager()
        
    def run(self):
        print(f"Starting to create folders in {self.dir_input}...")
        
        # Check if parent directory exists
        if not os.path.exists(self.dir_input):
            self.error_manager.send_error_level(
                source="FolderMaker",
                operation="run",
                message=f"Parent directory not found: {self.dir_input}",
                details="The specified directory does not exist",
                suggestion="Check that the path is correct and the parent folder exists"
            )
            raise FileNotFoundError(f"Directory not found: {self.dir_input}")
            
        # Check if we have write permissions
        if not os.access(self.dir_input, os.W_OK):
            self.error_manager.send_error_level(
                source="FolderMaker",
                operation="run",
                message=f"Cannot write to directory: {self.dir_input}",
                details="Permission denied",
                suggestion="Check that you have write permissions for the selected folder"
            )
            raise PermissionError(f"No write access to: {self.dir_input}")
        
        # Create each folder
        for folder in self.folders:
            folder_path = os.path.join(self.dir_input, folder)
            try:
                os.makedirs(folder_path, exist_ok=True)
                print(f"Created folder: {folder_path}")
            except Exception as e:
                self.error_manager.send_error_level(
                    source="FolderMaker",
                    operation="run",
                    message=f"Failed to create folder: {folder}",
                    details=str(e),
                    suggestion="Check disk space and permissions, then try again"
                )
                raise
                
        print("All folders have been successfully created.")