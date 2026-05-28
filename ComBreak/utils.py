import functools
import subprocess
import config
from pathlib import Path


@functools.lru_cache(maxsize=None)
def get_executable_path(executable_name, config_path):
    """Check if an executable is on PATH, otherwise return the path from config.

    Result is cached per (executable_name, config_path) — executables don't relocate mid-run,
    and this function is called inside per-frame and per-segment loops.
    """
    try:
        subprocess.run([executable_name, "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return executable_name  # Executable is on PATH
    except (subprocess.CalledProcessError, FileNotFoundError):
        if config_path and Path(config_path).is_file():
            return config_path
        else:
            raise FileNotFoundError(f"Executable '{executable_name}' not found on PATH or in configured path: {config_path}")
