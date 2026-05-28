"""
ComBreakDirect Server - Routes requests to the appropriate dock.

Architecture (Factory Metaphor):
- Loading Dock: Receives raw materials, processes, stores (INPUT)
- Factory Floor: Internal to docks - does the work
- Unloading Dock: Hands out finished products (OUTPUT)

Server is just the security guard directing traffic to the right dock.
"""

import re

from flask import Flask, Response, jsonify, request

import config
from .docks import LoadingDock, UnloadingDock
from .utilities import resolve_commercial_folder, resolve_storage_path


class ComBreakDirectServer:
    """Clean server that just coordinates the three dock areas."""

    def __init__(self, host: str | None = None, port: int | None = None, status_callback=None):
        self.host = host or getattr(config, "CBDIRECT_HOST", "0.0.0.0")
        self.port = port or getattr(config, "CBDIRECT_PORT", 8083)
        base_url = getattr(config, "CBDIRECT_BASE_URL", f"http://{self.host}:{self.port}")
        self.base_url = base_url.rstrip('/')
        self._status_callback = status_callback

        # Initialize the two dock areas
        commercial_folder = resolve_commercial_folder()
        storage_path = resolve_storage_path()

        # LoadingDock
        self.loading_dock = LoadingDock(
            commercial_folder=str(commercial_folder),
            base_url=self.base_url,
            storage_path=str(storage_path)
        )

        # UnloadingDock
        self.unloading_dock = UnloadingDock(loading_dock=self.loading_dock)
        self._break_render_thread = None
        self._break_render_timer = None

        # Pre-render commercial breaks for existing channels loaded from disk (BLOCKING)
        if self.unloading_dock.get_channel_count() > 0:
            print(f"[SERVER] Pre-rendering commercial breaks for {self.unloading_dock.get_channel_count()} existing channel(s)...")
            self._status("Pre-rendering commercial breaks (this may take a moment)")

            if self.loading_dock.break_renderer:
                for channel_data in self.unloading_dock.get_all_channels():
                    print(f"[SERVER] Pre-rendering breaks for channel {channel_data.get('number')}...")
                    self.loading_dock.break_renderer.pre_render_upcoming_breaks(channel_data, hours_ahead=1.0)
                print(f"[SERVER] Initial pre-rendering complete")

                # NOW start background thread for ongoing updates
                def valid_channels():
                    return self.unloading_dock.get_all_channels()

                print("[SERVER] Starting background commercial break renderer...")
                self._break_render_thread = self.loading_dock.break_renderer.start_background_renderer(valid_channels)

            self._status("Commercial break rendering complete")

        # Flask app
        self.app = Flask(__name__)
        self._setup_routes()

        print(f"[SERVER] ComBreakDirect ready on {self.base_url}")
        self._status(f"ComBreakDirect server initialized on {self.base_url}")

    def _setup_routes(self):
        """Setup the three APIs for the three docks."""

        # ============ WEBUI ROUTES ============
        @self.app.route('/', methods=['GET'])
        def webui_home():
            """Serve the WebUI landing page."""
            from .UI import generate_landing_page
            # Use request Host header to get actual accessible URL
            request_host = request.headers.get('Host', f"{self.host}:{self.port}")
            actual_url = f"http://{request_host}"
            return generate_landing_page(actual_url)

        # ============ LOADING DOCK API ============
        @self.app.route('/channels', methods=['POST'])
        def create_channel():
            """Loading dock - receives cutless data from client."""
            print(f"[SERVER] Loading dock processing request...")
            try:
                data = request.get_json()
                commercial_folder = (data or {}).get('commercial_folder')
                if commercial_folder:
                    self.loading_dock.update_commercial_folder(commercial_folder)

                # Send to Loading Dock
                channel_number = self.loading_dock.process_lineup(data)

                self._status(f"Lineup received for channel {channel_number}")
                self._status("Pre-rendering commercials")

                # Get channel data from Unloading Dock for break rendering
                channel_data = self.unloading_dock.get_channel(channel_number)
                self._start_break_rendering(channel_data=channel_data)

                self._status("Commercial pre-rendering complete")
                self._status(f"Channel {channel_number} ready")

                return jsonify({
                    'success': True,
                    'channel_number': channel_number,
                    'playlist_url': f"{self.base_url}/playlist.m3u8",
                    'guide_url': f"{self.base_url}/api/xmltv.xml"
                })
            except Exception as e:
                print(f"[SERVER] Error: {e}")
                return jsonify({'error': str(e)}), 500

        # ============ UNLOADING DOCK API (Metadata Output) ============
        @self.app.route('/playlist.m3u8', methods=['GET'])
        def get_playlist():
            """Unloading dock - generate M3U8 playlist."""
            try:
                # Use the request's host to generate proper URLs (DizqueTV pattern)
                request_host = request.headers.get('Host', f"{self.host}:{self.port}")
                external_url = f"http://{request_host}"

                playlist = self.unloading_dock.get_master_playlist(external_url)
                return Response(playlist, mimetype='application/vnd.apple.mpegurl')
            except Exception as e:
                return f"Error: {e}", 500

        @self.app.route('/api/xmltv.xml', methods=['GET'])
        def get_xmltv():
            """Unloading dock - generate XMLTV guide."""
            try:
                xmltv = self.unloading_dock.get_xmltv_guide()
                return Response(xmltv, mimetype='application/xml')
            except Exception as e:
                return f"Error: {e}", 500

        # ============ PLEX DISCOVERY API ============
        @self.app.route('/discover.json', methods=['GET'])
        def discover():
            """HDHomeRun-style device discovery for Plex (continuous MPEG-TS streams)."""
            request_host = request.headers.get('Host', f'{self.host}:{self.port}')
            return jsonify({
                "FriendlyName": "ComBreakDirect",
                "Manufacturer": "CommercialBreaker",
                "ModelNumber": "HDTC-2US",
                "FirmwareVersion": "1.0.0",
                "TunerCount": 1,
                "FirmwareName": "hdhomerun3_atsc",
                "DeviceID": "CB000001",
                "DeviceAuth": "test1234",
                "BaseURL": f"http://{request_host}",
                "LineupURL": f"http://{request_host}/lineup.json"
            })

        @self.app.route('/lineup.json', methods=['GET'])
        def lineup():
            """HDHomeRun-style channel lineup for Plex (continuous MPEG-TS)."""
            request_host = request.headers.get('Host', f'{self.host}:{self.port}')
            channels = self.unloading_dock.get_lineup_json(request_host)
            return jsonify(channels)

        @self.app.route('/lineup_status.json', methods=['GET'])
        def lineup_status():
            """HDHomeRun-style lineup status for Plex."""
            return jsonify({
                "ScanInProgress": 0,
                "ScanPossible": 1,
                "Source": "Cable",
                "SourceList": ["Cable"]
            })

        # ============ CONTINUOUS VIDEO STREAM (BROADCAST TOWER) ============
        @self.app.route('/video/channel/<int:channel_number>', methods=['GET'])
        def stream_continuous_video(channel_number):
            """
            Continuous MPEG-TS stream using BroadcastTower architecture.

            Like a TV broadcast - multiple antennas can receive same signal.
            Each client gets independent antenna with minimal buffer for signal stability.
            """
            channel_data = self.unloading_dock.get_channel(channel_number)
            if not channel_data:
                return "Channel not found", 404

            # Ensure channel studio and broadcast tower are ready
            self.unloading_dock.ensure_channel_ready(channel_number, channel_data)

            # Generate unique client ID for logging
            import uuid
            client_id = f"{request.remote_addr}:{uuid.uuid4().hex[:8]}"

            def generate():
                """Generator that yields MPEG-TS chunks to Flask Response."""
                antenna = None
                try:
                    # Connect antenna to broadcast tower
                    antenna = self.unloading_dock.connect_client(channel_number, client_id)

                    # Receive signal and stream to client
                    for chunk in antenna:
                        yield chunk

                    print(f"[SERVER] Stream ended normally for {client_id} on channel {channel_number}")

                except Exception as e:
                    print(f"[SERVER] Stream error for {client_id} on channel {channel_number}: {e}")

                finally:
                    # Disconnect antenna (disconnect detection works here!)
                    if antenna:
                        antenna.disconnect()
                        print(f"[SERVER] Disconnected antenna {client_id} from channel {channel_number}")

            return Response(
                generate(),
                mimetype='video/mp2t',
                headers={
                    'Content-Type': 'video/mp2t',
                    'Cache-Control': 'no-cache',
                    'Access-Control-Allow-Origin': '*'
                }
            )

        # ============ STATUS ============
        @self.app.route('/status', methods=['GET'])
        def status():
            """Server status."""
            channel_status = self.unloading_dock.get_status()
            return jsonify({
                'status': 'running',
                'version': 'ComBreakDirect-Clean',
                'channels': channel_status
            })

        @self.app.route('/wipe', methods=['POST'])
        def wipe():
            """Wipe all data - channels, broadcast towers, pre-rendered breaks."""
            print(f"[SERVER] WIPE requested - clearing all data")
            try:
                # Clear channel data from FactoryFloor
                if self.loading_dock and self.loading_dock.factory_floor:
                    self.loading_dock.factory_floor.channels.clear()
                    # Delete channels.json
                    storage_path = self.loading_dock.factory_floor.storage_path
                    if storage_path.exists():
                        storage_path.unlink()
                        print(f"[SERVER] Deleted {storage_path}")

                # Clear broadcast towers and studios
                if self.unloading_dock.broadcast_towers:
                    self.unloading_dock.broadcast_towers.clear()
                    print(f"[SERVER] Cleared broadcast towers")

                if self.unloading_dock.active_studios:
                    self.unloading_dock.active_studios.clear()
                    print(f"[SERVER] Cleared studio threads")

                # Clear pre-rendered commercial breaks
                if self.loading_dock and self.loading_dock.break_renderer:
                    temp_folder = self.loading_dock.break_renderer.temp_folder
                    if temp_folder.exists():
                        for item in temp_folder.iterdir():
                            if item.suffix == '.mkv' or item.suffix == '.txt':
                                item.unlink()
                        print(f"[SERVER] Cleared pre-rendered breaks from {temp_folder}")

                    # Clear break cache
                    self.loading_dock.break_renderer.break_cache.clear()

                self._status("All data wiped successfully")
                return jsonify({
                    'success': True,
                    'message': 'All data wiped - channels, towers, and pre-rendered breaks cleared'
                })
            except Exception as e:
                print(f"[SERVER] Wipe error: {e}")
                return jsonify({'error': str(e)}), 500

    def start_server(self, debug=False):
        """Start the server."""
        print(f"[SERVER] Starting on {self.base_url}")
        print(f"[SERVER] Playlist: {self.base_url}/playlist.m3u8")
        print(f"[SERVER] Guide: {self.base_url}/api/xmltv.xml")
        print(f"[SERVER] HDHomeRun stream: {self.base_url}/stream/chN?seq=0")
        self._status("ComBreakDirect server starting...")
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
        self._status("ComBreakDirect server stopped")

    def _start_break_rendering(self, channel_data: dict | None = None):
        """Start or update commercial break rendering for a channel."""
        if not self.loading_dock.break_renderer:
            return

        if channel_data:
            self.loading_dock.break_renderer.pre_render_upcoming_breaks(channel_data, hours_ahead=1.0)

        def valid_channels():
            return self.unloading_dock.get_all_channels()

        if self._break_render_thread and self._break_render_thread.is_alive():
            return

        print("[SERVER] Starting background commercial break rendering...")
        self._break_render_thread = self.loading_dock.break_renderer.start_background_renderer(valid_channels)

    def _status(self, message: str) -> None:
        if not self._status_callback:
            return
        try:
            self._status_callback(message)
        except Exception:
            pass
