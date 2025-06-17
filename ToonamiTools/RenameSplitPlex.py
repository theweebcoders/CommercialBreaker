import re
from plexapi.server import PlexServer
from API.utils.ErrorManager import get_error_manager


class PlexLibraryUpdater:
    def __init__(self, plex_url, plex_token, library_name):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.library_name = library_name
        self.pattern = r'\/([^\/]+)\.mp4$'
        self.error_manager = get_error_manager()
        
        # Validate inputs
        if not plex_url or not plex_token:
            self.error_manager.send_error_level(
                source="RenameSplitPlex",
                operation="__init__",
                message="Missing Plex connection details",
                details="Plex URL or token not provided",
                suggestion="Make sure you're logged into Plex before running this operation"
            )
            raise ValueError("Missing Plex connection details")
            
        # Try to connect to Plex
        try:
            self.plex = PlexServer(self.plex_url, self.plex_token)
        except Exception as e:
            error_msg = str(e).lower()
            if "unauthorized" in error_msg or "401" in error_msg:
                self.error_manager.send_error_level(
                    source="RenameSplitPlex",
                    operation="__init__",
                    message="Cannot authenticate with Plex server",
                    details="Invalid or expired authentication token",
                    suggestion="Your Plex login may have expired. Try logging in again"
                )
            elif "connection" in error_msg or "refused" in error_msg or "timeout" in error_msg:
                self.error_manager.send_error_level(
                    source="RenameSplitPlex",
                    operation="__init__",
                    message="Cannot reach Plex server",
                    details=f"Failed to connect to {plex_url}",
                    suggestion="Check that your Plex server is running and the URL is correct"
                )
            else:
                self.error_manager.send_error_level(
                    source="RenameSplitPlex",
                    operation="__init__",
                    message="Failed to connect to Plex",
                    details=str(e),
                    suggestion="Check your Plex server settings and try again"
                )
            raise
            
        # Try to access the library
        try:
            self.library = self.plex.library.section(self.library_name)
        except Exception as e:
            self.error_manager.send_error_level(
                source="RenameSplitPlex",
                operation="__init__",
                message=f"Cannot find library '{self.library_name}'",
                details="The specified library doesn't exist on your Plex server",
                suggestion="Check that you selected the correct library name from your Plex server"
            )
            raise

    def update_titles(self):
        try:
            # Iterate through all the videos in the library
            videos = self.library.all()
            
            if not videos:
                self.error_manager.send_warning(
                    source="RenameSplitPlex",
                    operation="update_titles",
                    message="Library is empty",
                    details=f"No videos found in library '{self.library_name}'",
                    suggestion="Make sure your library has been scanned and contains media"
                )
                return
                
        except Exception as e:
            self.error_manager.send_error_level(
                source="RenameSplitPlex",
                operation="update_titles",
                message="Failed to retrieve library items",
                details=str(e),
                suggestion="There was an error accessing your Plex library. Check your connection and try again."
            )
            raise
            
        updated_count = 0
        failed_count = 0
        
        for video in videos:
            try:
                file_path = video.media[0].parts[0].file

                # Apply the regex pattern to extract the file name
                match = re.search(self.pattern, file_path)
                if match:
                    new_title = match.group(1)

                    # Check if the title already matches the target title
                    if video.title == new_title:
                        print(f"Title already matches for file: {file_path}. Skipping.")
                        continue

                    # Rename the video title
                    video.edit(**{'title.value': new_title, 'title.locked': 1})
                    print(f"Title updated to: {new_title}")
                    updated_count += 1
                else:
                    print(f"Pattern did not match for file: {file_path}")
                    
            except Exception as e:
                print(f"Error updating title for video: {e}")
                failed_count += 1
                continue

        if failed_count > 0:
            self.error_manager.send_warning(
                source="RenameSplitPlex",
                operation="update_titles",
                message=f"Some titles could not be updated",
                details=f"Successfully updated {updated_count} titles, failed to update {failed_count}",
                suggestion="Check Plex permissions and server logs for more details"
            )
        
        print(f"Title update complete. Updated {updated_count} titles.")