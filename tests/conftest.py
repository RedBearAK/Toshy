"""
Pytest configuration and shared fixtures for Toshy tests.

This file contains fixtures and configuration that are available
to all tests in the suite.
"""

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def clean_environment():
    """
    Provide a clean environment for tests.

    Clears all environment variables and restores them after the test.
    """
    original_env = os.environ.copy()
    os.environ.clear()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_kde_environment():
    """Provide a mock KDE Plasma environment."""
    env = {
        'XDG_CURRENT_DESKTOP': 'KDE',
        'XDG_SESSION_DESKTOP': 'plasma',
        'KDE_FULL_SESSION': 'true',
        'DESKTOP_SESSION': 'plasma',
        'XDG_SESSION_TYPE': 'wayland'
    }
    with mock.patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_gnome_environment():
    """Provide a mock GNOME environment."""
    env = {
        'XDG_CURRENT_DESKTOP': 'GNOME',
        'XDG_SESSION_DESKTOP': 'gnome',
        'GNOME_DESKTOP_SESSION_ID': 'this-is-deprecated',
        'DESKTOP_SESSION': 'gnome',
        'XDG_SESSION_TYPE': 'wayland'
    }
    with mock.patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_x11_session():
    """Provide a mock X11 session type."""
    with mock.patch.dict(os.environ, {'XDG_SESSION_TYPE': 'x11'}, clear=False):
        yield


@pytest.fixture
def mock_wayland_session():
    """Provide a mock Wayland session type."""
    with mock.patch.dict(os.environ, {'XDG_SESSION_TYPE': 'wayland'}, clear=False):
        yield


@pytest.fixture
def mock_fedora_os_release():
    """Provide mock /etc/os-release content for Fedora."""
    return """
NAME="Fedora Linux"
VERSION="38 (Workstation Edition)"
ID=fedora
VERSION_ID=38
PRETTY_NAME="Fedora Linux 38 (Workstation Edition)"
ANSI_COLOR="0;38;2;60;110;180"
LOGO=fedora-logo-icon
CPE_NAME="cpe:/o:fedoraproject:fedora:38"
"""


@pytest.fixture
def mock_ubuntu_os_release():
    """Provide mock /etc/os-release content for Ubuntu."""
    return """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 22.04.3 LTS"
VERSION_ID="22.04"
"""


@pytest.fixture
def mock_dbus_connection():
    """Provide a mock D-Bus connection."""
    with mock.patch('dbus.SystemBus') as mock_bus:
        yield mock_bus


@pytest.fixture
def temp_config_dir(tmp_path):
    """
    Provide a temporary configuration directory.

    Creates a temporary directory structure mimicking ~/.config/toshy/
    """
    config_dir = tmp_path / "toshy"
    config_dir.mkdir()

    # Create subdirectories
    (config_dir / "scripts").mkdir()
    (config_dir / ".venv").mkdir()

    yield config_dir


@pytest.fixture
def sample_sqlite_db(temp_config_dir):
    """
    Provide a sample SQLite database for testing.

    Creates an empty database file in the temp config directory.
    """
    import sqlite3

    db_path = temp_config_dir / "toshy_user_preferences.sqlite"
    conn = sqlite3.connect(str(db_path))

    # Create a simple table for testing
    conn.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()

    yield db_path

    conn.close()


# Markers configuration (also in pytest.ini, but defined here for clarity)
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "dbus: marks tests that require D-Bus")
    config.addinivalue_line("markers", "systemd: marks tests that require systemd")
    config.addinivalue_line("markers", "gui: marks tests for GUI components")
