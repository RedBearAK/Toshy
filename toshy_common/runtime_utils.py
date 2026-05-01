__version__ = '20250710'

import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass

from toshy_common.logger import debug, error


@dataclass
class ToshyRuntime:
    """Container for Toshy runtime configuration and paths."""
    config_dir: str
    barebones_config: bool
    home_dir: str
    home_local_bin: str
    is_systemd: bool


def find_toshy_config_dir():
    """Find the Toshy configuration directory at runtime."""
    # 1. Check environment variable first (allows override)
    env_dir = os.getenv('TOSHY_CONFIG_DIR')
    if env_dir:
        config_dir = Path(env_dir)
        if config_dir.exists():
            return config_dir

    # 2. Standard user location
    config_dir = Path.home() / '.config' / 'toshy'
    if config_dir.exists():
        return config_dir

    raise RuntimeError(
        "Could not locate Toshy configuration directory. "
        "Try setting TOSHY_CONFIG_DIR environment variable."
    )


def pattern_found_in_module(pattern, module_path):
    """
    Check if a regex pattern is found in a module file.
    
    Args:
        pattern: Regex pattern to search for
        module_path: Path to the module file
        
    Returns:
        bool: True if pattern found, False otherwise
    """
    try:
        with open(module_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return bool(re.search(pattern, content))
    except FileNotFoundError as file_err:
        print(f"Error: The file {module_path} was not found.\n\t {file_err}")
        return False
    except IOError as io_err:
        print(f"Error: An issue occurred while reading the file {module_path}.\n\t {io_err}")
        return False


def check_barebones_config(toshy_config_dir):
    """
    Check if the config file is a "barebones" type.
    
    Args:
        toshy_config_dir: Path to Toshy configuration directory
        
    Returns:
        bool: True if barebones config, False otherwise
    """
    pattern = 'SLICE_MARK_START: barebones_user_cfg'
    module_path = os.path.join(toshy_config_dir, 'toshy_config.py')
    return pattern_found_in_module(pattern, module_path)


def is_init_systemd():
    """
    Check if the system is using systemd as the init system.
    
    Returns:
        bool: True if systemd is the init system, False otherwise
    """
    try:
        with open("/proc/1/comm", "r") as f:
            return f.read().strip() == 'systemd'
    except FileNotFoundError:
        debug("The /proc/1/comm file does not exist.")
        return False
    except PermissionError:
        debug("Permission denied when trying to read the /proc/1/comm file.")
        return False


def setup_python_paths(toshy_config_dir):
    """
    Set up Python import paths for Toshy components.
    
    Args:
        toshy_config_dir: Path to Toshy configuration directory (str or Path)
    """
    # Convert to string if Path object
    if isinstance(toshy_config_dir, Path):
        toshy_config_dir = str(toshy_config_dir)
    
    # Calculate paths
    home_dir = os.path.expanduser("~")
    home_local_bin = os.path.join(home_dir, '.local', 'bin')
    local_site_packages_dir = os.path.join(
        home_dir,
        f".local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    )
    
    # Update sys.path for imports
    sys.path.insert(0, local_site_packages_dir)
    sys.path.insert(0, toshy_config_dir)
    
    # Update PYTHONPATH environment variable
    existing_path = os.environ.get('PYTHONPATH', '')
    os.environ['PYTHONPATH'] = f'{toshy_config_dir}:{local_site_packages_dir}:{existing_path}'
    
    # Always update PATH (both apps need CLI tools)
    os.environ['PATH'] = f"{home_local_bin}:{os.environ['PATH']}"
    
    # debug(f"Python paths configured with Toshy config dir: {toshy_config_dir}")


def initialize_toshy_runtime():
    """
    Complete Toshy runtime initialization.
    
    Finds config directory, sets up paths, and checks for barebones config.
    
    Returns:
        ToshyRuntime: Object containing all runtime configuration
    """
    # Platform check
    if not str(sys.platform) == "linux":
        raise OSError("This app is designed to be run only on Linux")
    
    # Find Toshy configuration directory
    toshy_config_dir = find_toshy_config_dir()
    
    # Set up Python paths
    setup_python_paths(toshy_config_dir)
    
    # Check for barebones config
    barebones_config = check_barebones_config(toshy_config_dir)
    
    # Check if systemd is the init system
    systemd_init = is_init_systemd()
    
    # Get commonly needed paths
    home_dir = os.path.expanduser("~")
    home_local_bin = os.path.join(home_dir, '.local', 'bin')
    
    return ToshyRuntime(
        config_dir=str(toshy_config_dir),
        barebones_config=barebones_config,
        home_dir=home_dir,
        home_local_bin=home_local_bin,
        is_systemd=systemd_init
    )
