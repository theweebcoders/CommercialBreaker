import os
from API.utils.ErrorManager import get_error_manager


class GetPlexTimestamps:
    def __init__(self, plex_url, plex_token, library_name, save_dir):
        self.error_manager = get_error_manager()
        
        # Validate inputs
        if not plex_url or not plex_token:
            self.error_manager.send_error_level(
                source="GetPlexTimestamps",
                operation="__init__",
                message="Missing Plex connection details",
                details="Plex URL or token not provided",
                suggestion="Make sure you're logged into Plex before running this operation"
            )
            raise ValueError("Missing Plex connection details")
            
        try:
            from plexapi.server import PlexServer
            self.plex = PlexServer(plex_url, plex_token)
        except Exception as e:
            if "unauthorized" in str(e).lower():
                self.error_manager.send_error_level(
                    source="GetPlexTimestamps",
                    operation="__init__",
                    message="Cannot connect to Plex server",
                    details="Invalid authentication token",
                    suggestion="Your Plex login may have expired. Try logging in again"
                )
            elif "connection" in str(e).lower() or "refused" in str(e).lower():
                self.error_manager.send_error_level(
                    source="GetPlexTimestamps",
                    operation="__init__",
                    message="Cannot reach Plex server",
                    details=f"Failed to connect to {plex_url}",
                    suggestion="Check that your Plex server is running and accessible"
                )
            else:
                self.error_manager.send_error_level(
                    source="GetPlexTimestamps",
                    operation="__init__",
                    message="Failed to connect to Plex",
                    details=str(e),
                    suggestion="Check your Plex server settings and try again"
                )
            raise
            
        self.library_name = library_name
        self.save_dir = save_dir

    def run(self):
        # Get all the media in the library
        try:
            section = self.plex.library.section(self.library_name)
        except Exception as e:
            self.error_manager.send_error_level(
                source="GetPlexTimestamps",
                operation="run",
                message=f"Cannot find library '{self.library_name}'",
                details="The specified library doesn't exist on your Plex server",
                suggestion="Check that you selected the correct library name from your Plex server"
            )
            raise
            
        try:
            all_media = section.all()
        except Exception as e:
            self.error_manager.send_error_level(
                source="GetPlexTimestamps",
                operation="run",
                message="Cannot read media from Plex library",
                details=str(e),
                suggestion="There may be an issue with your Plex library"
            )
            raise
            
        print(f'Loaded {len(all_media)} media items from the Plex library.')
        
        if not all_media:
            self.error_manager.send_warning(
                source="GetPlexTimestamps",
                operation="run",
                message="No media found in library",
                details=f"The library '{self.library_name}' appears to be empty",
                suggestion="Make sure your Plex library contains the shows you want to process"
            )
            return

        # Create the save directory if it doesn't exist
        try:
            os.makedirs(self.save_dir, exist_ok=True)
        except Exception as e:
            self.error_manager.send_error_level(
                source="GetPlexTimestamps",
                operation="run",
                message=f"Cannot create directory: {self.save_dir}",
                details=str(e),
                suggestion="Check that you have permission to create folders in the selected location"
            )
            raise

        # Check write permissions
        test_file = os.path.join(self.save_dir, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            self.error_manager.send_error_level(
                source="GetPlexTimestamps",
                operation="run",
                message=f"Cannot write to directory: {self.save_dir}",
                details="Permission denied",
                suggestion="Check that you have write permissions for the selected folder"
            )
            raise

        # Track if we found any intros
        intro_count = 0
        processed_count = 0

        # Open a text file in the specified directory to write the output
        try:
            with open(os.path.join(self.save_dir, 'intros.txt'), 'w', encoding='utf-8') as file:
                for media_item in all_media:
                    print(f'Processing: {media_item.title}')
                    try:
                        episodes = media_item.episodes()
                    except:
                        # Not a TV show, skip
                        continue
                        
                    for episode in episodes:
                        processed_count += 1
                        try:
                            item = self.plex.fetchItem(f'/library/metadata/{episode.ratingKey}')
                            if hasattr(item, 'markers'):
                                for marker in item.markers:
                                    if marker.type == 'intro':
                                        intro_count += 1
                                        start_time_offset = marker.start
                                        end_time_offset = marker.end
                                        start_time_converted = start_time_offset / 1000
                                        end_time_converted = end_time_offset / 1000
                                        file_path = item.media[0].parts[0].file
                                        # Get the file name from the file path by splitting on the last slash
                                        file_name = file_path.split('/')[-1]
                                        print(f'Found intro for {file_name} at {start_time_converted} to {end_time_converted}.')
                                        #intro_line = f'{file_name} = "intro" Start of intro is "{start_time_converted}" End of intro is "{end_time_converted}"\n'
                                        cut_line = f'{file_name} = {end_time_converted}\n'
                                        #file.write(intro_line)
                                        file.write(cut_line)
                        except Exception as e:
                            # Individual episode failure, continue processing
                            print(f'Error processing episode: {e}')
                            continue

            print(f'Intros written to {os.path.join(self.save_dir, "intros.txt")}.')
            
            # Warn if no intros found
            if intro_count == 0 and processed_count > 0:
                self.error_manager.send_warning(
                    source="GetPlexTimestamps",
                    operation="run",
                    message="No intro markers found",
                    details=f"Processed {processed_count} episodes but found no intro skip markers",
                    suggestion="Make sure intro detection has been run in Plex for this library"
                )
            elif intro_count < processed_count * 0.1:  # Less than 10% have intros
                self.error_manager.send_warning(
                    source="GetPlexTimestamps",
                    operation="run",
                    message=f"Only {intro_count} intro markers found",
                    details=f"Out of {processed_count} episodes, only {intro_count} have intro markers",
                    suggestion="Consider running intro detection in Plex to find more intro timestamps"
                )
                
        except Exception as e:
            self.error_manager.send_error_level(
                source="GetPlexTimestamps",
                operation="run",
                message="Failed to write intro timestamps file",
                details=str(e),
                suggestion="Check disk space and permissions, then try again"
            )
            raise