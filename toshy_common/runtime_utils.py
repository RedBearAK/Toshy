__version__ = '20260313'

import os
import re
import sys
import locale
import unicodedata

from pathlib import Path
from dataclasses import dataclass

from toshy_common.logger import debug, error


# If LC_ALL is unset (as observed on NebiOS 10.2), try to fix so
# that Unicode characters are supported. Fall back to sanitizing.
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        os.environ['LC_ALL'] = 'C.UTF-8'
    except locale.Error:
        pass  # truly broken, sanitize_text handles it


def _check_locale_utf8():
    """Check whether the current locale supports UTF-8 encoding."""
    try:
        encoding = locale.getpreferredencoding() or ''
        return 'utf' in encoding.lower()
    except Exception:
        return False


locale_is_utf8 = _check_locale_utf8()



# Common Unicode characters found in Linux desktop/app UI elements,
# mapped to their closest ASCII equivalents.
_unicode_to_ascii_map = {
    # Bullets and markers
    '\u2022':   '*',        # •  bullet
    '\u2023':   '>',        # ‣  triangular bullet
    '\u25cf':   '*',        # ●  black circle
    '\u25cb':   'o',        # ○  white circle
    '\u2043':   '-',        # ⁃  hyphen bullet

    # Dashes
    '\u2014':   '--',       # —  em dash
    '\u2013':   '-',        # –  en dash
    '\u2012':   '-',        # ‒  figure dash

    # Quotation marks
    '\u201c':   '"',        # "  left double quotation
    '\u201d':   '"',        # "  right double quotation
    '\u2018':   "'",        # '  left single quotation
    '\u2019':   "'",        # '  right single quotation
    '\u00ab':   '<<',       # «  left guillemet
    '\u00bb':   '>>',       # »  right guillemet

    # Arrows
    '\u2192':   '->',       # →  rightwards arrow
    '\u2190':   '<-',       # ←  leftwards arrow
    '\u2191':   '^',        # ↑  upwards arrow
    '\u2193':   'v',        # ↓  downwards arrow

    # Common symbols
    '\u2026':   '...',      # …  horizontal ellipsis
    '\u00d7':   'x',        # ×  multiplication sign
    '\u2212':   '-',        # −  minus sign
    '\u00b7':   '*',        # ·  middle dot
    '\u2010':   '-',        # ‐  hyphen
    '\u00a0':   ' ',        # non-breaking space
}


def sanitize_text(text):
    """Sanitize Unicode text to ASCII-safe equivalents when the locale
    does not support UTF-8. Returns the text unchanged when UTF-8 is
    available.

    Uses a manual mapping for common UI characters, NFKD normalization
    for decomposable characters (accented letters, ligatures), and
    a final ASCII encode with '?' replacement as a safety net."""

    if not isinstance(text, str):
        error(f"sanitize_text expected str, got {type(text).__name__}")
        return str(text)

    if locale_is_utf8:
        return text

    # Apply the manual mapping for known characters
    for unicode_char, ascii_replacement in _unicode_to_ascii_map.items():
        if unicode_char in text:
            text = text.replace(unicode_char, ascii_replacement)

    # NFKD normalization decomposes characters like é → e + combining accent
    text = unicodedata.normalize('NFKD', text)

    # Encode to ASCII, replacing anything still non-ASCII with '?'
    text = text.encode('ascii', 'replace').decode('ascii')

    return text


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
