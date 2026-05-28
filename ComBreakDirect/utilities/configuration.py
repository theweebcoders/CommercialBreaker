"""Utilities for resolving ComBreakDirect runtime paths."""

from __future__ import annotations

import os
from pathlib import Path

import config


def resolve_data_root() -> Path:
    # Import here to avoid circular import
    from API.utils.FlagManager import FlagManager

    if FlagManager.docker:
        root = os.environ.get('CBDIRECT_DATA_ROOT', '/app/working/combreak_direct')
    else:
        root = os.environ.get('CBDIRECT_DATA_ROOT') or getattr(
            config,
            'CBDIRECT_DATA_ROOT',
            Path(__file__).resolve().parents[1] / 'combreak_direct_data',
        )
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_commercial_folder() -> Path:
    # Import here to avoid circular import
    from API.utils.FlagManager import FlagManager

    if FlagManager.docker:
        folder = os.environ.get('COMMERCIAL_FOLDER', '/app/commercials')
    else:
        folder = os.environ.get('COMMERCIAL_FOLDER')
        if not folder:
            folder = getattr(config, 'COMMERCIAL_FOLDER', None)
        if not folder:
            folder = resolve_data_root() / 'commercials'
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_storage_path() -> Path:
    # Import here to avoid circular import
    from API.utils.FlagManager import FlagManager

    if FlagManager.docker:
        storage = os.environ.get('CBDIRECT_STORAGE_PATH', '/app/working/combreak_direct/channels.json')
    else:
        storage = os.environ.get('CBDIRECT_STORAGE_PATH')
        if not storage:
            storage = getattr(config, 'CBDIRECT_STORAGE_PATH', None)
        if not storage:
            storage = resolve_data_root() / 'channels.json'
    path = Path(storage)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
