import subprocess
import config
from pathlib import Path

def get_executable_path(executable_name, config_path):
    """Check if an executable is on PATH, otherwise return the path from config."""
    try:
        # Use subprocess.run for better control and error handling
        # Check=True will raise CalledProcessError if the command fails
        # stdout/stderr=subprocess.PIPE prevents output from cluttering the console
        subprocess.run([executable_name, "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return executable_name  # Executable is on PATH
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Handle both command failure and executable not found
        # Check if the config_path exists and is a file
        if config_path and Path(config_path).is_file():
            return config_path # Use config path if valid
        else:
            # Raise an error if neither PATH nor config path works
            raise FileNotFoundError(f"Executable '{executable_name}' not found on PATH or in configured path: {config_path}")
