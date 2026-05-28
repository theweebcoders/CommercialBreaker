"""
PlexConnectionHelper - Smart Plex server connection with automatic URL retry.

This helper provides reliable Plex server connections by:
1. Attempting smart reconnection using server name (tries all available URLs)
2. Falling back to stored URL if smart reconnection fails

This solves the problem of temporary relay URLs timing out by always trying
fresh connection information when available.
"""

from typing import Optional
from API.utils.DatabaseManager import get_db_manager
from API.utils.PlexServer import SimplePlexServer as PlexServer
from API.utils.PlexClient import PlexAccountClient, PlexAuthError


class PlexConnectionHelper:
    """Helper class for establishing reliable Plex server connections."""

    @staticmethod
    def connect_smart(plex_token: str, plex_url: str, timeout: int = 15) -> PlexServer:
        """
        Create a Plex server connection with smart URL selection.

        This method first attempts to reconnect using the stored server name,
        which triggers a fresh lookup of all available URLs (local, relay, direct)
        and tries them in order of preference. If that fails or server name is
        unavailable, it falls back to the stored URL.

        Args:
            plex_token: Plex authentication token
            plex_url: Stored Plex server URL (used as fallback)
            timeout: Connection timeout in seconds (default: 15)

        Returns:
            PlexServer: Connected Plex server instance

        Raises:
            Exception: If connection fails with both smart reconnection and fallback URL
        """
        # Try smart reconnection first
        try:
            # Get stored server name and client identifier from database
            db_manager = get_db_manager()

            server_name_row = db_manager.fetchone(
                "SELECT value FROM app_data WHERE key = ?",
                ("plex_server_name",)
            )

            client_id_row = db_manager.fetchone(
                "SELECT value FROM app_data WHERE key = ?",
                ("plex_client_identifier",)
            )

            # If we have a server name, try smart reconnection
            if server_name_row and server_name_row["value"]:
                server_name = server_name_row["value"]
                client_id = client_id_row["value"] if client_id_row else None

                # Create Plex account client
                account = PlexAccountClient(
                    token=plex_token,
                    client_identifier=client_id
                )

                # Get all available server resources
                resources = account.resources()

                # Find our server by name
                selected_resource = next(
                    (r for r in resources if r.name == server_name),
                    None
                )

                if selected_resource:
                    # Use smart connect - tries all URLs (local, relay, direct)
                    # with short timeouts per URL
                    connection = selected_resource.connect(timeout=timeout)

                    # Successfully connected with fresh URL
                    return PlexServer(connection.baseurl, plex_token)

        except (PlexAuthError, Exception):
            # Smart reconnection failed, fall through to stored URL
            pass

        # Fallback: Use stored URL
        # This happens if:
        # - Server name not in database
        # - Smart reconnection failed
        # - Server not found in resources list
        return PlexServer(plex_url, plex_token)

    @staticmethod
    def connect_with_server_name(
        plex_token: str,
        server_name: str,
        client_identifier: Optional[str] = None,
        timeout: int = 15
    ) -> PlexServer:
        """
        Connect to a Plex server by name without needing a stored URL.

        Useful for operations that only need token + server name.

        Args:
            plex_token: Plex authentication token
            server_name: Name of the Plex server to connect to
            client_identifier: Optional client UUID
            timeout: Connection timeout in seconds (default: 15)

        Returns:
            PlexServer: Connected Plex server instance

        Raises:
            PlexAuthError: If server not found or connection fails
        """
        # Create Plex account client
        account = PlexAccountClient(
            token=plex_token,
            client_identifier=client_identifier
        )

        # Get all available server resources
        resources = account.resources()

        # Find our server by name
        selected_resource = next(
            (r for r in resources if r.name == server_name),
            None
        )

        if not selected_resource:
            raise PlexAuthError(f"Server '{server_name}' not found in account resources")

        # Use smart connect - tries all URLs
        connection = selected_resource.connect(timeout=timeout)

        return PlexServer(connection.baseurl, plex_token)
