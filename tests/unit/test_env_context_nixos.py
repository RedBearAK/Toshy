#!/usr/bin/env python3
"""
Tests for NixOS detection in env_context.py

Following TDD RED-GREEN-REFACTOR cycle:
- Write tests first (RED)
- Implement minimal code to pass (GREEN)
- Refactor while keeping tests green (REFACTOR)
"""

import os
import subprocess
import pytest
from unittest import mock
from toshy_common.env_context import EnvironmentInfo


class TestNixOSDetection:
    """Test NixOS detection from various sources"""

    def test_should_detect_nixos_from_os_release_id(self):
        """NixOS should be detected when ID=nixos in /etc/os-release"""
        mock_os_release = [
            'NAME="NixOS"',
            'ID=nixos',
            'VERSION="24.05 (Uakari)"',
            'VERSION_ID="24.05"',
            'PRETTY_NAME="NixOS 24.05 (Uakari)"'
        ]

        with mock.patch('os.path.isfile', return_value=False):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()
            assert env.DISTRO_ID == 'nixos'

    def test_should_detect_nixos_from_etc_nixos_marker(self):
        """NixOS should be detected from /etc/NIXOS file existence"""
        # Mock /etc/os-release without explicit ID
        mock_os_release = [
            'NAME="NixOS"',
            'PRETTY_NAME="NixOS"'
        ]

        def mock_isfile(path):
            if path == '/etc/NIXOS':
                return True
            elif path in ['/etc/os-release', '/etc/lsb-release', '/etc/arch-release']:
                return False
            return False

        with mock.patch('os.path.isfile', side_effect=mock_isfile):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()
            assert env.DISTRO_ID == 'nixos'

    def test_should_detect_nixos_from_name_when_id_missing(self):
        """NixOS should be detected from NAME field if ID is missing"""
        mock_os_release = [
            'NAME="NixOS"',
            'PRETTY_NAME="NixOS 24.05"'
        ]

        with mock.patch('os.path.isfile', return_value=False):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()
            assert env.DISTRO_ID == 'nixos'

    def test_should_handle_nixos_with_unstable_version(self):
        """NixOS unstable should also be detected"""
        mock_os_release = [
            'NAME="NixOS"',
            'ID=nixos',
            'VERSION="24.11 (Vicuna) (pre)"',
            'PRETTY_NAME="NixOS 24.11 (Vicuna) (pre)"'
        ]

        with mock.patch('os.path.isfile', return_value=False):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()
            assert env.DISTRO_ID == 'nixos'

    def test_should_not_detect_nixos_on_other_distros(self):
        """Other distros should not be misidentified as NixOS"""
        mock_os_release = [
            'NAME="Fedora Linux"',
            'ID=fedora',
            'VERSION_ID="39"'
        ]

        def mock_isfile(path):
            if path == '/etc/NIXOS':
                return False
            return False

        with mock.patch('os.path.isfile', side_effect=mock_isfile):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()
            assert env.DISTRO_ID != 'nixos'
            assert env.DISTRO_ID == 'fedora'


class TestNixOSEnvironmentInfo:
    """Test that EnvironmentInfo works correctly on NixOS"""

    def test_should_populate_distro_id_for_nixos(self):
        """DISTRO_ID should be set correctly for NixOS"""
        mock_os_release = [
            'NAME="NixOS"',
            'ID=nixos',
            'VERSION="24.05 (Uakari)"',
            'PRETTY_NAME="NixOS 24.05 (Uakari)"'
        ]

        with mock.patch('os.path.isfile', return_value=False):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()
            assert env.DISTRO_ID == 'nixos'

    def test_should_populate_distro_version_for_nixos(self):
        """DISTRO_VER should be set correctly for NixOS"""
        mock_os_release = [
            'NAME="NixOS"',
            'ID=nixos',
            'VERSION_ID="24.05"',
            'VERSION="24.05 (Uakari)"'
        ]

        with mock.patch('os.path.isfile', return_value=False):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()
            assert env.DISTRO_VER == '24.05'


class TestNixOSWindowManagerDetection:
    """Test window manager detection on NixOS, particularly for GNOME"""

    def test_should_detect_gnome_shell_on_nixos_gnome_wayland(self):
        """
        GNOME Shell should be detected on NixOS with GNOME Wayland.

        On NixOS, processes may have full Nix store paths, but is_process_running()
        should still detect them correctly.
        """
        # ARRANGE - Set up NixOS with GNOME Wayland environment
        mock_os_release = [
            'NAME="NixOS"',
            'ID=nixos',
            'VERSION_ID="24.05"'
        ]

        mock_env_vars = {
            'XDG_SESSION_TYPE': 'wayland',
            'XDG_CURRENT_DESKTOP': 'GNOME',
            'WAYLAND_DISPLAY': 'wayland-0'
        }

        # Mock pgrep to return success for gnome-shell
        def mock_check_output(cmd, *args, **kwargs):
            if 'gnome-shell' in ' '.join(cmd):
                return b'12345\n'  # PID of gnome-shell
            elif 'mutter' in ' '.join(cmd):
                return b'12346\n'  # PID of mutter
            raise subprocess.CalledProcessError(1, cmd)

        # ACT
        with mock.patch('os.path.isfile', return_value=False), \
             mock.patch.dict(os.environ, mock_env_vars, clear=True), \
             mock.patch('subprocess.check_output', side_effect=mock_check_output):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()

        # ASSERT - Window manager should be detected as gnome-shell or mutter
        assert env.WINDOW_MGR in ['gnome-shell', 'mutter'], \
            f"Expected gnome-shell or mutter, got '{env.WINDOW_MGR}'"
        assert env.WINDOW_MGR != 'WM_unidentified_by_logic', \
            "GNOME window manager should be detected, not unidentified"

    def test_should_explain_why_gnome_wm_not_detected_on_nixos(self):
        """
        This test documents the issue: when pgrep fails to find gnome-shell/mutter,
        WINDOW_MGR becomes 'WM_unidentified_by_logic'.

        This is a RED test - it demonstrates the problem before we fix it.
        """
        # ARRANGE - NixOS GNOME Wayland where pgrep fails
        mock_os_release = [
            'NAME="NixOS"',
            'ID=nixos',
            'VERSION_ID="24.05"'
        ]

        mock_env_vars = {
            'XDG_SESSION_TYPE': 'wayland',
            'XDG_CURRENT_DESKTOP': 'GNOME',
        }

        # Mock pgrep to fail (simulating the NixOS issue)
        def mock_check_output_fail(cmd, *args, **kwargs):
            # All pgrep calls fail
            raise subprocess.CalledProcessError(1, cmd)

        # ACT
        with mock.patch('os.path.isfile', return_value=False), \
             mock.patch.dict(os.environ, mock_env_vars, clear=True), \
             mock.patch('subprocess.check_output', side_effect=mock_check_output_fail):
            env = EnvironmentInfo()
            env.release_files['/etc/os-release'] = mock_os_release
            env.get_env_info()

        # ASSERT - This documents the bug
        assert env.DESKTOP_ENV == 'gnome'
        assert env.WINDOW_MGR == 'WM_unidentified_by_logic', \
            "When pgrep fails, WINDOW_MGR should be 'WM_unidentified_by_logic' (documenting the bug)"
