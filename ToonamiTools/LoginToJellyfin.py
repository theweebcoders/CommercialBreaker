import asyncio
import webbrowser
import requests
from jellyfin_apiclient_python import JellyfinClient


class JellyfinServerList:

    def __init__(self):
        self.jellyfin_servers = []
        self.jellyfin_token = None
        self.jellyfin_user_id = None
        self.auth_url_callback = None  # New callback for auth URL
        self.auth_url = None  # Store the auth URL as an instance attribute
        self.client = JellyfinClient()

    def set_auth_url_callback(self, callback):
        """Allow setting a callback function to handle the auth URL"""
        self.auth_url_callback = callback

    def GetJellyfinToken(self):
        """
        Initiates Quick Connect authentication with Jellyfin.
        Similar to Plex PIN authentication but uses Jellyfin's Quick Connect.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch_token():
            try:
                # Set up client device info
                self.client.config.app(
                    "Commercial Breaker", "0.0.1", "Test Device", "test-device-id"
                )

                # For Quick Connect, we need a server URL first
                # This is a simplified approach - in practice, you might want to discover servers
                # or have the user provide a server URL first
                server_url = self._prompt_for_server_url()

                if not server_url:
                    raise ValueError(
                        "Server URL is required for Jellyfin authentication"
                    )

                # Connect to the server
                self.client.config.data["auth.server"] = server_url

                # Initiate Quick Connect
                quick_connect_response = requests.post(
                    f"{server_url}/QuickConnect/Initiate",
                    headers={"Content-Type": "application/json"},
                )

                if quick_connect_response.status_code != 200:
                    raise ValueError(
                        f"Failed to initiate Quick Connect: {quick_connect_response.status_code}"
                    )

                quick_connect_data = quick_connect_response.json()
                secret = quick_connect_data.get("Secret")
                code = quick_connect_data.get("Code")

                if not secret or not code:
                    raise ValueError("Failed to get Quick Connect secret or code")

                # Create auth URL for user to approve
                auth_url = (
                    f"{server_url}/web/index.html#!/quickconnect?api_key={secret}"
                )
                self.auth_url = auth_url

                # Use the callback if provided, otherwise fall back to default behavior
                if self.auth_url_callback and callable(self.auth_url_callback):
                    self.auth_url_callback(auth_url)
                else:
                    # Fallback for non-web UI
                    webbrowser.open(auth_url)
                    print(
                        "Please open the following URL in your browser to authenticate with Jellyfin:"
                    )
                    print(
                        f"Alternatively, go to your Jellyfin dashboard and enter this code: {code}"
                    )
                    print(f"URL: {auth_url}")

                # Poll for authentication completion
                authenticated = False
                max_attempts = 60  # 5 minutes with 5-second intervals
                attempt = 0

                while not authenticated and attempt < max_attempts:
                    await asyncio.sleep(5)  # Wait 5 seconds between polls
                    attempt += 1

                    # Check if Quick Connect is authenticated
                    status_response = requests.get(
                        f"{server_url}/QuickConnect/Connect", params={"Secret": secret}
                    )

                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get("Authenticated"):
                            authenticated = True

                            # Get the access token
                            auth_response = requests.post(
                                f"{server_url}/Users/AuthenticateWithQuickConnect",
                                json={"Secret": secret},
                                headers={"Content-Type": "application/json"},
                            )

                            if auth_response.status_code == 200:
                                auth_data = auth_response.json()
                                self.jellyfin_token = auth_data.get("AccessToken")
                                self.jellyfin_user_id = auth_data.get("User", {}).get(
                                    "Id"
                                )

                                # Set credentials in the client
                                credentials = {
                                    "Servers": [
                                        {
                                            "UserId": self.jellyfin_user_id,
                                            "AccessToken": self.jellyfin_token,
                                            "address": server_url,
                                        }
                                    ]
                                }
                                self.client.set_credentials(credentials)
                                return self.jellyfin_token
                            else:
                                raise ValueError(
                                    f"Failed to authenticate: {auth_response.status_code}"
                                )

                if not authenticated:
                    raise ValueError("Authentication timed out. Please try again.")

            except Exception as e:
                print(f"Jellyfin authentication error: {e}")
                raise

        self.jellyfin_token = loop.run_until_complete(fetch_token())
        loop.close()

    def _prompt_for_server_url(self):
        """
        Prompt user for Jellyfin server URL.
        In a GUI context, this would be handled by the UI.
        """
        if hasattr(self, "_server_url") and self._server_url:
            return self._server_url

        # For CLI/fallback, prompt user
        print("Please enter your Jellyfin server URL (e.g., http://localhost:8096):")
        server_url = input().strip()
        if server_url and not server_url.startswith(("http://", "https://")):
            server_url = f"http://{server_url}"
        return server_url

    def set_server_url(self, server_url):
        """Allow setting server URL programmatically (for GUI use)"""
        self._server_url = server_url

    def GetJellyfinServerList(self):
        """
        Fetches and stores the list of Jellyfin servers associated with the user's account.
        Note: Unlike Plex, Jellyfin typically uses a single server instance.
        """
        if not self.jellyfin_token:
            self.GetJellyfinToken()

        try:
            # For Jellyfin, we typically have one server that we connected to
            # But we can get server info to populate the list
            credentials = self.client.get_credentials()
            if credentials and "Servers" in credentials:
                servers = credentials["Servers"]
                self.jellyfin_servers = [
                    f"Jellyfin Server ({server.get('address', 'Unknown')})"
                    for server in servers
                ]
            else:
                # Fallback - create a generic entry
                self.jellyfin_servers = ["Jellyfin Server"]

        except Exception as e:
            print(f"An error occurred getting Jellyfin servers: {e}")
            # Provide a fallback
            self.jellyfin_servers = ["Jellyfin Server"]

    def run(self):
        self.GetJellyfinServerList()


class JellyfinLibraryManager:
    """
    This class is responsible for managing the Jellyfin library. It fetches and stores the details of a selected Jellyfin server.
    This is important to the program as it allows the user to select a Jellyfin server and use the libraries on that server in the program.
    """

    def __init__(self, selected_server, jellyfin_token, jellyfin_user_id):
        self.selected_server = selected_server
        self.jellyfin_token = jellyfin_token
        self.jellyfin_user_id = jellyfin_user_id
        self.jellyfin_url = None
        self.client = JellyfinClient()
        """
        Takes the selected Jellyfin server and the Jellyfin token as arguments.
        """

    def GetJellyfinDetails(self):
        """
        Fetches and stores the details of the selected Jellyfin server. It uses the Jellyfin token to authenticate with the Jellyfin server and connect to the selected server. The base URL of the server is then stored for future use.
        This is important to retain user's selection so it can be stored for future use.
        """
        try:
            credentials = self.client.get_credentials()
            if credentials and "Servers" in credentials:
                # Find the server that matches our selection
                for server in credentials["Servers"]:
                    if server.get("UserId") == self.jellyfin_user_id:
                        self.jellyfin_url = server.get("address")
                        break

            if not self.jellyfin_url:
                raise ValueError("Could not find Jellyfin server URL in credentials")

        except Exception as e:
            print(f"Error getting Jellyfin details: {e}")
            raise

    def run(self):
        self.GetJellyfinDetails()
        return self.jellyfin_url


class JellyfinLibraryFetcher:
    """
    This class is responsible for fetching and storing the libraries from a selected Jellyfin server.
    It uses the Jellyfin token to authenticate with the Jellyfin server and connect to the server using its base URL.
    The libraries are then fetched and stored for future use.
    """

    def __init__(self, jellyfin_url, jellyfin_token, jellyfin_user_id):
        self.jellyfin_url = jellyfin_url
        self.jellyfin_token = jellyfin_token
        self.jellyfin_user_id = jellyfin_user_id
        self.libraries = []

    """
    Takes the base URL of the selected Jellyfin server and the Jellyfin token as arguments.
    """

    def GetJellyfinLibraries(self):
        """
        Fetches libraries from Jellyfin server using the REST API.
        """
        try:
            headers = {
                "Authorization": f"MediaBrowser Token={self.jellyfin_token}",
                "Content-Type": "application/json",
            }

            # Get user's accessible libraries
            response = requests.get(
                f"{self.jellyfin_url}/Users/{self.jellyfin_user_id}/Views",
                headers=headers,
            )

            if response.status_code == 200:
                libraries_data = response.json()
                items = libraries_data.get("Items", [])

                # Filter for media libraries (typically Movies, TV Shows, etc.)
                self.libraries = []
                for item in items:
                    library_name = item.get("Name")
                    collection_type = item.get("CollectionType")

                    # Include libraries that might contain anime/TV content
                    if (
                        collection_type in ["tvshows", "movies", "mixed"]
                        or not collection_type
                    ):
                        self.libraries.append(library_name)

            else:
                raise ValueError(f"Failed to fetch libraries: {response.status_code}")

        except Exception as e:
            print(f"Error fetching Jellyfin libraries: {e}")
            raise

    def run(self):
        self.GetJellyfinLibraries()
