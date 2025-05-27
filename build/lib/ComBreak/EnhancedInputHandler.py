"""
EnhancedInputHandler module provides flexible input methods for the Commercial Breaker application.
"""
import os
from pathlib import Path
import config

class EnhancedInputHandler:
    """
    Utility class to handle various input types for Commercial Breaker processing.
    Supports individual files, folders, or a mixture of both.
    """
    def __init__(self):
        self.files = []
        self.folders = []
        self.filtered_paths = []
        self.video_file_extensions = tuple(config.video_file_types)
        self._consolidated_paths = []
        
    def add_files(self, file_paths):
        """
        Add individual files to the input handler.
        
        Args:
            file_paths (list): List of file paths to add
        """
        paths_added = False
        for path in file_paths:
            file_path = Path(path)
            if file_path.is_file() and file_path.suffix.lower() in self.video_file_extensions:
                # Store the absolute path for consistency
                abs_path = file_path.absolute()
                if abs_path not in self.files:
                    self.files.append(abs_path)
                    paths_added = True
        
        # Clear the cache if any paths were added to force regeneration
        if paths_added:
            self._consolidated_paths = []
        
    def add_folders(self, folder_paths):
        """
        Add folders to the input handler (legacy mode).
        
        Args:
            folder_paths (list): List of folder paths to add
        """
        folders_added = False
        for path in folder_paths:
            folder_path = Path(path)
            if folder_path.is_dir():
                # Store the absolute path for consistency
                abs_path = folder_path.absolute()
                if abs_path not in self.folders:
                    self.folders.append(abs_path)
                    folders_added = True
        
        # Clear the cache if any folders were added to force regeneration
        if folders_added:
            self._consolidated_paths = []
    
    def merge_with_database_filter(self, db_filtered_paths):
        """
        Integrate database-filtered paths with the manually selected files/folders.
        
        Args:
            db_filtered_paths (list): List of paths from database filtering
        """
        paths_added = False
        for path in db_filtered_paths:
            path_obj = Path(path)
            abs_path = path_obj.absolute()
            if abs_path not in self.filtered_paths:
                self.filtered_paths.append(abs_path)
                paths_added = True
                
        # Clear the cache if any paths were added
        if paths_added:
            self._consolidated_paths = []
        
    def get_consolidated_paths(self):
        """
        Return a consolidated and deduplicated list of all video files.
        Combines manually selected files, files from selected folders, and filtered paths.
        
        Returns:
            list: List of all valid video file paths
        """
        # Only use cached version if it exists
        if self._consolidated_paths:
            return self._consolidated_paths
            
        consolidated = set()
        
        # Add individual files
        for file_path in self.files:
            consolidated.add(str(file_path))
        
        # Add files from folders
        for folder in self.folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(self.video_file_extensions):
                        file_path = Path(root) / file
                        consolidated.add(str(file_path))
        
        # Add filtered paths
        for path in self.filtered_paths:
            consolidated.add(str(path))
        
        self._consolidated_paths = list(consolidated)
        return self._consolidated_paths
    
    def clear_all(self):
        """Clear all selected paths."""
        self.files.clear()
        self.folders.clear()
        self.filtered_paths.clear()
        self._consolidated_paths.clear()
        
    def has_input(self):
        """Check if any input has been added."""
        return bool(self.files or self.folders or self.filtered_paths)
        
    def get_output_path_for_file(self, input_file, output_base_dir):
        """
        Determine the appropriate output path for a given input file.
        For folder-based inputs, preserves the directory structure.
        For individual files, preserves show name and season folders.
        
        Args:
            input_file (str): The input file path
            output_base_dir (str): The base output directory
            
        Returns:
            Path: The output directory path for the file
        """
        input_file_path = Path(input_file)
        
        # For files within selected folders, maintain the original structure
        for folder in self.folders:
            try:
                rel_path = input_file_path.relative_to(folder)
                output_dir = Path(output_base_dir) / rel_path.parent
                return output_dir
            except ValueError:
                # Not a subpath of this folder, continue checking
                continue
        
        # For individually selected files, look for season folders and show names
        parts = list(input_file_path.parts)
        parent_dir = input_file_path.parent.name.lower()
        
        # Check if the immediate parent is a season folder
        is_season_folder = False
        show_name = None
        
        # Check if parent directory is a season folder
        if parent_dir.startswith("season") or "season" in parent_dir:
            is_season_folder = True
            # If it's a season folder, the show name is likely one level up
            if len(parts) >= 3:  # Need at least /show/season/file.mp4
                show_name = parts[-3]
        
        # Build the output path based on what we found
        if is_season_folder and show_name:
            # We have a show with season folders
            output_dir = Path(output_base_dir) / show_name / parts[-2]
        else:
            # No season structure, just use the immediate parent folder
            output_dir = Path(output_base_dir) / input_file_path.parent.name
        
        return output_dir