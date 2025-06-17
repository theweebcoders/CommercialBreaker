import asyncio
import webbrowser
import sys
import socket
from plexauth import PlexAuth
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from API.utils.ErrorManager import get_error_manager



class PlexServerList:

    def __init__(self):
        self.plex_servers = []
        self.plex_token = None
        self.auth_url_callback = None  # New callback for auth URL
        self.auth_url = None  # Store the auth URL as an instance attribute
        self.error_manager = get_error_manager()

    def set_auth_url_callback(self, callback):
        """Allow setting a callback function to handle the auth URL"""
        self.auth_url_callback = callback

    def check_internet_connection(self):
        """Check if we have internet connectivity by trying to reach common DNS servers."""
        try:
            # Try to connect to Cloudflare DNS (1.1.1.1) on port 53
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            return True
        except (socket.timeout, socket.error):
            try:
                # Fallback to Google DNS (8.8.8.8)
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                return True
            except (socket.timeout, socket.error):
                return False

    def check_plex_connection(self):
        """Check if Plex.tv is reachable."""
        try:
            socket.create_connection(("plex.tv", 443), timeout=5)
            return True
        except (socket.timeout, socket.error):
            return False

    def GetPlexToken(self):
        # Check internet connectivity first
        if not self.check_internet_connection():
            self.error_manager.send_critical(
                source="PlexServerList",
                operation="GetPlexToken",
                message="No internet connection detected",
                details="Unable to connect to external DNS servers (1.1.1.1, 8.8.8.8)",
                suggestion="Please check your internet connection and try again"
            )
            raise Exception("No internet connection")
        
        # Check Plex.tv specifically
        if not self.check_plex_connection():
            self.error_manager.send_error_level(
                source="PlexServerList",
                operation="GetPlexToken",
                message="Cannot connect to Plex.tv",
                details="Internet connection is working but Plex.tv is unreachable",
                suggestion="Plex.tv may be down or blocked. Check https://status.plex.tv for service status"
            )
            raise Exception("Cannot connect to Plex.tv")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch_token():
            PAYLOAD = {
                'X-Plex-Product': 'Commercial Breaker',
                'X-Plex-Version': '0.0.1',
                'X-Plex-Device': 'Test Device',
                'X-Plex-Platform': 'Test Platform',
                'X-Plex-Device-Name': 'Test Device Name',
                'X-Plex-Device-Vendor': 'Test Vendor',
                'X-Plex-Model': 'Test Model',
                'X-Plex-Client-Platform': 'Test Client Platform'
            }
            try:
                async with PlexAuth(PAYLOAD) as plexauth:
                    await plexauth.initiate_auth()
                    auth_url = plexauth.auth_url()
                    self.auth_url = auth_url  # Store the auth URL in the instance
                    
                    # Use the callback if provided, otherwise fall back to default behavior
                    if self.auth_url_callback and callable(self.auth_url_callback):
                        self.auth_url_callback(auth_url)
                    else:
                        # Fallback for non-web UI
                        webbrowser.open(auth_url)
                        print("Please open the following URL in your browser to authenticate with Plex: \n" + auth_url)
                    
                    return await plexauth.token()
            except ConnectionError as e:
                # Check if it's a DNS resolution error (no internet)
                if "nodename nor servname provided" in str(e) or "Name or service not known" in str(e):
                    self.error_manager.send_critical(
                        source="PlexServerList",
                        operation="GetPlexToken",
                        message="DNS resolution failed - no internet connection",
                        details=f"Cannot resolve plex.tv hostname: {str(e)}",
                        suggestion="Check your internet connection and DNS settings"
                    )
                else:
                    self.error_manager.send_error_level(
                        source="PlexServerList",
                        operation="GetPlexToken",
                        message="Cannot connect to Plex authentication servers",
                        details=f"Failed to connect to Plex API: {str(e)}",
                        suggestion="Check if Plex services are accessible or try again later"
                    )
                raise
            except TimeoutError as e:
                self.error_manager.send_error_level(
                    source="PlexServerList",
                    operation="GetPlexToken",
                    message="Plex authentication timed out",
                    details=f"Authentication request timed out: {str(e)}",
                    suggestion="Check your internet speed or try again later"
                )
                raise
            except Exception as e:
                # Check for common connection-related errors in the exception message
                error_str = str(e).lower()
                if any(term in error_str for term in ["network", "connection", "dns", "resolve", "timeout"]):
                    self.error_manager.send_error_level(
                        source="PlexServerList",
                        operation="GetPlexToken",
                        message="Network connectivity issue during Plex authentication",
                        details=f"Network error: {str(e)}",
                        suggestion="Check your internet connection and try again"
                    )
                else:
                    self.error_manager.send_error_level(
                        source="PlexServerList",
                        operation="GetPlexToken",
                        message="Failed to authenticate with Plex",
                        details=f"Authentication error: {str(e)}",
                        suggestion="Ensure you have valid Plex credentials and try authenticating again"
                    )
                raise

        try:
            self.plex_token = loop.run_until_complete(fetch_token())
        except Exception:
            # Error already logged in fetch_token
            raise
        finally:
            loop.close()

    def GetPlexServerList(self):
        """
        Fetches and stores the list of Plex servers associated with the user's Plex account. It obtains the Plex token and uses it to authenticate with the Plex account.
        Allowing the program to interact with the user's Plex servers and provide the user with a list of their Plex servers.
        """
        try:
            self.GetPlexToken()
        except Exception:
            # Error already logged in GetPlexToken
            raise
            
        try:
            account = MyPlexAccount(token=self.plex_token)
            resources = account.resources()
            self.plex_servers = [resource.name for resource in resources]
            
            if not self.plex_servers:
                self.error_manager.send_warning(
                    source="PlexServerList",
                    operation="GetPlexServerList",
                    message="No Plex servers found",
                    details="The Plex account has no associated servers",
                    suggestion="Ensure you have at least one Plex Media Server set up and accessible"
                )
                
        except Exception as e:
            self.error_manager.send_error_level(
                source="PlexServerList",
                operation="GetPlexServerList",
                message="Failed to fetch Plex server list",
                details=f"Error connecting to MyPlex account: {str(e)}",
                suggestion="Check your Plex token validity and internet connection"
            )
            raise

    def run(self):
        self.GetPlexServerList()


class PlexLibraryManager:
    """
    This class is responsible for managing the Plex library. It fetches and stores the details of a selected Plex server.
    This is important to the program as it allows the user to select a Plex server and use the libraries on that server in the program.
    """
    def __init__(self, selected_server, plex_token):
        self.selected_server = selected_server
        self.plex_token = plex_token  # Storing the token
        self.plex_url = None
        self.error_manager = get_error_manager()
        """
        Takes the selected Plex server and the Plex token as arguements.
        """

    def GetPlexDetails(self):
        """
        Fetches and stores the details of the selected Plex server. It uses the Plex token to authenticate with the Plex account and connect to the selected server. The base URL of the server is then stored for future use. 
        This is important to retain user's selection so it can be stored for future use.
        """
        try:
            account = MyPlexAccount(token=self.plex_token)
            selected_resource = next(
                (resource for resource in account.resources() if resource.name == self.selected_server), 
                None
            )
            
            if selected_resource is None:
                self.error_manager.send_error_level(
                    source="PlexLibraryManager",
                    operation="GetPlexDetails",
                    message=f"Plex server '{self.selected_server}' not found",
                    details="The selected server is not available in the account resources",
                    suggestion="Check if the server name is correct and the server is online"
                )
                raise ValueError(f"Server '{self.selected_server}' not found")
                
            plex = selected_resource.connect()
            self.plex_url = plex._baseurl  # Storing the URL
            
        except ConnectionError as e:
            self.error_manager.send_error_level(
                source="PlexLibraryManager",
                operation="GetPlexDetails",
                message=f"Cannot connect to Plex server '{self.selected_server}'",
                details=f"Connection failed: {str(e)}",
                suggestion="Check if the Plex server is running and accessible on your network"
            )
            raise
        except Exception as e:
            self.error_manager.send_error_level(
                source="PlexLibraryManager",
                operation="GetPlexDetails",
                message="Failed to get Plex server details",
                details=f"Error accessing server '{self.selected_server}': {str(e)}",
                suggestion="Verify the server is online and your Plex token is valid"
            )
            raise

    def run(self):
        self.GetPlexDetails()
        return self.plex_url


class PlexLibraryFetcher:
    """
    This class is responsible for fetching and storing the libraries from a selected Plex server.
    It uses the Plex token to authenticate with the Plex account and connect to the server using its base URL.
    The libraries are then fetched and stored for future use.
    """
    def __init__(self, plex_url, plex_token):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.libraries = []
        self.error_manager = get_error_manager()

    """
    Takes the base URL of the selected Plex server and the Plex token as arguements.
    """

    def GetPlexLibraries(self):
        try:
            server = PlexServer(self.plex_url, self.plex_token)
            libraries = server.library.sections()
            self.libraries = [library.title for library in libraries]
            
            if not self.libraries:
                self.error_manager.send_warning(
                    source="PlexLibraryFetcher",
                    operation="GetPlexLibraries",
                    message="No libraries found on Plex server",
                    details="The Plex server has no configured libraries",
                    suggestion="Add libraries to your Plex server or check server configuration"
                )
                
        except ConnectionError as e:
            self.error_manager.send_error_level(
                source="PlexLibraryFetcher",
                operation="GetPlexLibraries",
                message="Cannot connect to Plex server",
                details=f"Failed to connect to {self.plex_url}: {str(e)}",
                suggestion="Check if the Plex server is running and the URL is correct"
            )
            raise
        except Exception as e:
            self.error_manager.send_error_level(
                source="PlexLibraryFetcher",
                operation="GetPlexLibraries",
                message="Failed to fetch Plex libraries",
                details=f"Error accessing libraries from {self.plex_url}: {str(e)}",
                suggestion="Verify your Plex token is valid and the server is accessible"
            )
            raise

    def run(self):
        self.GetPlexLibraries()
