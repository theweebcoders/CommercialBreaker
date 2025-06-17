import uuid
from plexapi.server import PlexServer
from API.utils.ErrorManager import get_error_manager


class PlexAutoSplitter:
    def __init__(self, plex_url, plex_token, library_name):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.library_name = library_name
        self.error_manager = get_error_manager()
        
        # Validate inputs
        if not plex_url or not plex_token:
            self.error_manager.send_error_level(
                source="PlexAutoSplitter",
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
                    source="PlexAutoSplitter",
                    operation="__init__",
                    message="Cannot authenticate with Plex server",
                    details="Invalid or expired authentication token",
                    suggestion="Your Plex login may have expired. Try logging in again"
                )
            elif "connection" in error_msg or "refused" in error_msg or "timeout" in error_msg:
                self.error_manager.send_error_level(
                    source="PlexAutoSplitter",
                    operation="__init__",
                    message="Cannot reach Plex server",
                    details=f"Failed to connect to {plex_url}",
                    suggestion="Check that your Plex server is running and the URL is correct"
                )
            else:
                self.error_manager.send_error_level(
                    source="PlexAutoSplitter",
                    operation="__init__",
                    message="Failed to connect to Plex",
                    details=str(e),
                    suggestion="Check your Plex server settings and try again"
                )
            raise

    def split_merged_item(self, rating_key):
        client_identifier = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        URL = f'/library/metadata/{rating_key}/split'
        PARAMS = {
            'X-Plex-Product': 'Plex Web',
            'X-Plex-Version': '4.108.0',
            'X-Plex-Client-Identifier': client_identifier,
            'X-Plex-Platform': 'Firefox',
            'X-Plex-Platform-Version': '116.0',
            'X-Plex-Features': 'external-media,indirect-media,hub-style-list',
            'X-Plex-Model': 'bundled',
            'X-Plex-Device': 'Windows',
            'X-Plex-Device-Name': 'Firefox',
            'X-Plex-Device-Screen-Resolution': '1718x847,3440x1440',
            'X-Plex-Token': self.plex_token,
            'X-Plex-Language': 'en',
            'X-Plex-Session-Id': session_id,
        }
        
        try:
            response = self.plex._session.put(self.plex_url + URL, params=PARAMS)
            
            if response.status_code == 200:
                print(f"Successfully split item with ratingKey: {rating_key}")
                return True
            else:
                print(f"Failed to split item with ratingKey: {rating_key}: {response.text}")
                return False
                
        except Exception as e:
            self.error_manager.send_error_level(
                source="PlexAutoSplitter",
                operation="split_merged_item",
                message=f"Error splitting item {rating_key}",
                details=str(e),
                suggestion="Check that the item exists and can be split"
            )
            return False

    def split_merged_items(self):
        try:
            # Get the library
            library = self.plex.library.section(self.library_name)
        except Exception as e:
            self.error_manager.send_error_level(
                source="PlexAutoSplitter",
                operation="split_merged_items",
                message=f"Cannot find library '{self.library_name}'",
                details="The specified library doesn't exist on your Plex server",
                suggestion="Check that you selected the correct library name from your Plex server"
            )
            raise
            
        # Track results
        split_success = 0
        split_failed = 0
        
        try:
            merged_items_found = True
            while merged_items_found:
                merged_items_found = False
                
                # Get all items in library
                all_items = library.all()
                
                if not all_items:
                    self.error_manager.send_error_level(
                        source="PlexAutoSplitter",
                        operation="split_merged_items",
                        message="No items found in library",
                        details=f"The library '{self.library_name}' appears to be empty",
                        suggestion="Make sure your Plex library has been scanned and contains media"
                    )
                    return
                
                for item in all_items:
                    if len(item.media) > 1:
                        print(f"Found merged item with ratingKey: {item.ratingKey}")
                        merged_items_found = True
                        
                        if self.split_merged_item(item.ratingKey):
                            split_success += 1
                        else:
                            split_failed += 1
                            
            # Report results if there were failures
            if split_failed > 0:
                self.error_manager.send_warning(
                    source="PlexAutoSplitter",
                    operation="split_merged_items",
                    message=f"Some items could not be split",
                    details=f"Successfully split {split_success} items, failed to split {split_failed} items",
                    suggestion="The failed items may already be split or have other issues. Check your Plex server logs"
                )
            elif split_success > 0:
                print(f"All {split_success} merged items have been successfully split.")
            else:
                print("No merged items found - all items are already split.")
                
        except Exception as e:
            self.error_manager.send_error_level(
                source="PlexAutoSplitter",
                operation="split_merged_items",
                message="Failed to process library items",
                details=str(e),
                suggestion="There was an error accessing your Plex library. Try refreshing the library in Plex"
            )
            raise