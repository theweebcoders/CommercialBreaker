"""
ComBreakDirect WebUI - Integrated with Flask on port 8083.

Provides landing page with setup information and copy buttons.
"""


def get_base_styles() -> str:
    """Get the Toonami-themed CSS styles."""
    return """
    <style>
        @keyframes grid-scroll {
            0% { background-position: 0 0; }
            100% { background-position: 60px 60px; }
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }

        @keyframes gold-shimmer {
            0% {
                background-position: -200% center;
            }
            100% {
                background-position: 200% center;
            }
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Rajdhani', Arial, sans-serif;
            background-color: #000924;
            background-image: linear-gradient(45deg, rgba(0, 140, 255, 0.2) 1px, transparent 1px), linear-gradient(-45deg, rgba(0, 140, 255, 0.3) 1px, transparent 1px);
            background-size: 30px 30px;
            animation: grid-scroll 20s linear infinite;
            color: #00ccff;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        h1 {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            color: #0ff;
            text-shadow: 0 0 5px #00ccff, 0 0 10px #0099ff, 0 0 20px #0066ff, 0 0 40px #003399;
            margin: 20px 0;
            letter-spacing: 0.1em;
        }

        .subtitle {
            font-size: 1.5rem;
            font-weight: 600;
            text-align: center;
            margin: 10px 0 30px 0;
            letter-spacing: 0.2em;
            background: linear-gradient(
                90deg,
                #8B7355 0%,
                #D4AF37 20%,
                #FFD700 40%,
                #FFED4E 50%,
                #FFD700 60%,
                #D4AF37 80%,
                #8B7355 100%
            );
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gold-shimmer 3s linear infinite;
            text-shadow:
                0 0 10px rgba(255, 215, 0, 0.5),
                0 0 20px rgba(255, 215, 0, 0.3),
                0 2px 4px rgba(0, 0, 0, 0.5);
            filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.4));
        }

        .card {
            background: rgba(0, 30, 60, 0.6);
            border: 1px solid rgba(0, 140, 255, 0.4);
            clip-path: polygon(0 10px, 10px 0, calc(100% - 10px) 0, 100% 10px, 100% calc(100% - 10px), calc(100% - 10px) 100%, 10px 100%, 0 calc(100% - 10px));
            padding: 30px;
            margin: 20px 0;
            box-shadow: 0 0 20px rgba(0, 140, 255, 0.3), inset 0 0 15px rgba(0, 100, 200, 0.1);
        }

        .card-title {
            font-size: 1.5rem;
            color: #00ffff;
            margin-bottom: 20px;
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.7);
            font-weight: bold;
        }

        .url-row {
            display: flex;
            align-items: center;
            margin: 15px 0;
            gap: 10px;
        }

        .url-label {
            color: #00ccff;
            font-weight: bold;
            min-width: 150px;
        }

        .url-field {
            flex: 1;
            font-family: monospace;
            font-size: 14px;
            color: #a5f3fc;
            background: rgba(0, 20, 40, 0.8);
            border: 1px solid rgba(0, 140, 255, 0.4);
            border-radius: 4px;
            padding: 10px;
        }

        .copy-btn {
            font-family: 'Rajdhani', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: #00ffff;
            background: linear-gradient(90deg, rgba(0, 50, 100, 0.6) 0%, rgba(0, 100, 150, 0.4) 100%);
            border: 1px solid rgba(0, 255, 255, 0.6);
            clip-path: polygon(15px 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%, 0 15px);
            padding: 8px 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 0 10px rgba(0, 255, 255, 0.3), inset 0 0 8px rgba(0, 100, 255, 0.2);
            text-shadow: 0 0 5px rgba(0, 255, 255, 0.5);
        }

        .copy-btn:hover {
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.6), inset 0 0 12px rgba(0, 150, 255, 0.3);
            transform: translateY(-2px);
            text-shadow: 0 0 8px rgba(0, 255, 255, 0.8);
        }

        .nav-buttons {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 20px;
        }

        .nav-btn {
            font-family: 'Rajdhani', sans-serif;
            font-size: 16px;
            font-weight: 600;
            color: #00ffff;
            background: rgba(0, 50, 100, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.6);
            border-radius: 4px;
            padding: 12px 24px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
            text-shadow: 0 0 5px rgba(0, 255, 255, 0.7);
            text-decoration: none;
            display: inline-block;
        }

        .nav-btn:hover {
            box-shadow: 0 0 25px rgba(0, 255, 255, 0.5);
            transform: translateY(-2px);
            color: #ffffff;
        }

        .instructions {
            color: #a5f3fc;
            line-height: 1.8;
        }

        .instructions b {
            color: #00ffff;
        }

        .channel-header {
            font-size: 1.3rem;
            color: #00ffff;
            margin: 20px 0 10px 0;
            font-weight: bold;
        }

        .program-item {
            color: #a5f3fc;
            margin: 5px 0;
            padding-left: 20px;
        }

        video {
            width: 100%;
            border-radius: 4px;
            box-shadow: 0 0 20px rgba(0, 140, 255, 0.3);
        }

        .error {
            color: #ff6666;
            text-align: center;
            padding: 20px;
        }

        .channel-selector {
            font-family: 'Rajdhani', sans-serif;
            font-size: 16px;
            color: #00ffff;
            background: rgba(0, 20, 40, 0.8);
            border: 1px solid rgba(0, 255, 255, 0.6);
            border-radius: 4px;
            padding: 10px 15px;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
        }

        .channel-selector:hover {
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
        }

        .channel-selector option {
            background: #001133;
            color: #00ffff;
        }

        /* Popup overlay */
        .popup-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 9999;
            justify-content: center;
            align-items: center;
        }

        .popup-overlay.show {
            display: flex;
        }

        .popup-box {
            background: rgba(0, 30, 60, 0.95);
            border: 2px solid rgba(0, 255, 255, 0.6);
            clip-path: polygon(0 15px, 15px 0, calc(100% - 15px) 0, 100% 15px, 100% calc(100% - 15px), calc(100% - 15px) 100%, 15px 100%, 0 calc(100% - 15px));
            padding: 40px;
            max-width: 600px;
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.5), inset 0 0 20px rgba(0, 100, 200, 0.2);
            animation: pulse 2s ease-in-out infinite;
        }

        .popup-title {
            font-size: 2rem;
            color: #00ffff;
            text-align: center;
            margin-bottom: 20px;
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.8);
            font-weight: bold;
        }

        .popup-message {
            color: #a5f3fc;
            font-size: 1.1rem;
            line-height: 1.8;
            margin-bottom: 30px;
            text-align: center;
        }

        .popup-message strong {
            color: #00ffff;
            text-shadow: 0 0 5px rgba(0, 255, 255, 0.5);
        }

        .popup-close-btn {
            font-family: 'Rajdhani', sans-serif;
            font-size: 18px;
            font-weight: 700;
            color: #00ffff;
            background: linear-gradient(90deg, rgba(0, 50, 100, 0.8) 0%, rgba(0, 100, 150, 0.6) 100%);
            border: 2px solid rgba(0, 255, 255, 0.8);
            clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
            padding: 12px 40px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.4), inset 0 0 10px rgba(0, 150, 255, 0.3);
            text-shadow: 0 0 8px rgba(0, 255, 255, 0.7);
            display: block;
            margin: 0 auto;
        }

        .popup-close-btn:hover {
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.7), inset 0 0 15px rgba(0, 180, 255, 0.5);
            transform: translateY(-2px);
            text-shadow: 0 0 12px rgba(0, 255, 255, 1);
        }
    </style>
    """


def generate_landing_page(base_url: str) -> str:
    """Generate the landing page HTML."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>ComBreakDirect</title>
        <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&display=swap" rel="stylesheet">
        {get_base_styles()}
    </head>
    <body>
        <div class="container">
            <h1>ComBreakDirect</h1>
            <div class="subtitle">Stay Gold</div>

            <div class="card">
                <div class="card-title">Connection Information</div>

                <div class="url-row">
                    <div class="url-label">Tuner URL:</div>
                    <input type="text" class="url-field" readonly value="{base_url}" id="tuner_url">
                    <button class="copy-btn" onclick="copyToClipboard('tuner_url', this)">Copy</button>
                </div>

                <div class="url-row">
                    <div class="url-label">M3U8 Playlist:</div>
                    <input type="text" class="url-field" readonly value="{base_url}/playlist.m3u8" id="m3u8_url">
                    <button class="copy-btn" onclick="copyToClipboard('m3u8_url', this)">Copy</button>
                </div>

                <div class="url-row">
                    <div class="url-label">XMLTV Guide:</div>
                    <input type="text" class="url-field" readonly value="{base_url}/api/xmltv.xml" id="xmltv_url">
                    <button class="copy-btn" onclick="copyToClipboard('xmltv_url', this)">Copy</button>
                </div>
            </div>

            <div class="card">
                <div class="card-title">Setup Instructions</div>
                <div class="instructions">
                    <p><b>Plex Setup (HDHomeRun Emulation):</b></p>
                    <p>1. Open Plex Settings → Live TV & DVR</p>
                    <p>2. Click "Setup Plex DVR"</p>
                    <p>3. Select "HDHomeRun" as the device type</p>
                    <p>4. Plex should auto-detect the tuner, or paste the Tuner URL above</p>
                    <p>5. Follow the channel lineup wizard</p>
                    <br>

                    <p><b>Jellyfin Setup:</b></p>
                    <p>1. Dashboard → Live TV → Tuner Devices</p>
                    <p>2. Add → Select HDHomeRun</p>
                    <p>3. Enter the server IP address and port</p>
                    <p>4. Channels will auto-discover from the lineup</p>
                    <br>

                    <p><b>Direct Streaming (Advanced):</b></p>
                    <p>Individual channels can be accessed via:</p>
                    <p style="font-family: monospace; padding-left: 20px;">{base_url}/video/channel/[number]</p>
                    <p>Example: {base_url}/video/channel/60</p>
                </div>
            </div>
        </div>

        <!-- Dismissible Popup -->
        <div class="popup-overlay" id="keepRunningPopup">
            <div class="popup-box">
                <div class="popup-title">⚠️ Keep CommercialBreaker Running</div>
                <div class="popup-message">
                    <strong>Important:</strong> Unlike DizqueTV and Tunarr (which run independently),
                    ComBreakDirect is part of CommercialBreaker. You'll need to <strong>keep CommercialBreaker running</strong>
                    for your channel to stream. If you close TOM/Absolution/Clydes, ComBreakDirect stops too.
                    <br><br>
                    <strong>Desktop (TOM) users:</strong> Use the close button (not Cmd+Q on Mac or Alt+F4 on Windows)
                    to minimize to the system tray and keep streaming.
                    <br><br>
                    Think of it like keeping your broadcast tower powered on!
                </div>
                <button class="popup-close-btn" onclick="dismissPopup()">Got It!</button>
            </div>
        </div>

        <script>
            function copyToClipboard(elementId, button) {{
                const input = document.getElementById(elementId);
                input.select();
                document.execCommand('copy');

                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.style.color = '#00ff00';

                setTimeout(() => {{
                    button.textContent = originalText;
                    button.style.color = '#00ffff';
                }}, 2000);
            }}

            // Popup management with localStorage
            function dismissPopup() {{
                const popup = document.getElementById('keepRunningPopup');
                popup.classList.remove('show');
                localStorage.setItem('combreakdirect_popup_dismissed', 'true');
            }}

            // Show popup on page load if not dismissed
            window.addEventListener('DOMContentLoaded', function() {{
                const dismissed = localStorage.getItem('combreakdirect_popup_dismissed');
                if (!dismissed) {{
                    const popup = document.getElementById('keepRunningPopup');
                    popup.classList.add('show');
                }}
            }});
        </script>
    </body>
    </html>
    """
