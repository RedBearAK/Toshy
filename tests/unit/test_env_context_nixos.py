#!/usr/bin/env python3
"""
Tests for NixOS detection in env_context.py

Following TDD RED-GREEN-REFACTOR cycle:
- Write tests first (RED)
- Implement minimal code to pass (GREEN)
- Refactor while keeping tests green (REFACTOR)
"""

import os
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
