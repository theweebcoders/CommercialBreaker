#!/usr/bin/env python3
"""Entry point for launching the ComBreakDirect server."""

import argparse
import pathlib
import sys
import threading

# Ensure project root is on sys.path
repo_root = pathlib.Path(__file__).resolve().parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import config
from ComBreakDirect.ComBreakDirectServer import ComBreakDirectServer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the ComBreakDirect server")
    parser.add_argument(
        "--host",
        default=getattr(config, "CBDIRECT_HOST", "0.0.0.0"),
        help="Host interface for the server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=getattr(config, "CBDIRECT_PORT", 8083),
        help="TCP port for the API server",
    )
    parser.add_argument(
        "--webui-port",
        type=int,
        default=8084,
        help="TCP port for the WebUI server",
    )
    parser.add_argument(
        "--no-webui",
        action="store_true",
        help="Disable the WebUI server",
    )
    return parser


def start_server(host: str | None = None, port: int | None = None,
                 webui_port: int = 8084, enable_webui: bool = True,
                 status_callback=None) -> None:
    host = host or getattr(config, "CBDIRECT_HOST", "0.0.0.0")
    port = port or getattr(config, "CBDIRECT_PORT", 8083)

    # Create the API server (WebUI is integrated into Flask routes)
    server = ComBreakDirectServer(host=host, port=port, status_callback=status_callback)

    # Start the API server (this blocks)
    server.start_server(debug=False)


def main() -> None:
    args = build_arg_parser().parse_args()
    start_server(
        args.host,
        args.port,
        args.webui_port,
        not args.no_webui
    )


if __name__ == "__main__":
    main()
