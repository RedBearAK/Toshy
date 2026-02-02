#!/usr/bin/env python3
"""
Tests for NixOS support in setup_toshy.py

Following TDD RED-GREEN-REFACTOR cycle:
- Write tests first (RED)
- Implement minimal code to pass (GREEN)
- Refactor while keeping tests green (REFACTOR)
"""

import pytest
from unittest import mock
import sys
import os
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestNixOSDistroGroups:
    """Test NixOS presence in distro group mappings"""

    def test_should_have_nixos_in_distro_groups(self):
        """NixOS should be listed in distro_groups_map"""
        # Import setup_toshy module
        import setup_toshy

        # Check that nixos-based group exists
        assert 'nixos-based' in setup_toshy.distro_groups_map

        # Check that nixos is in the nixos-based group
        assert 'nixos' in setup_toshy.distro_groups_map['nixos-based']

    def test_nixos_based_group_should_only_contain_nixos(self):
        """nixos-based group should contain only 'nixos'"""
        import setup_toshy

        # NixOS is unique enough to have its own group
        assert setup_toshy.distro_groups_map['nixos-based'] == ['nixos']


class TestNixOSHandler:
    """Test NixOSHandler class functionality"""

    def test_should_generate_udev_rules_nix_config(self):
        """NixOSHandler should generate valid udev rules configuration"""
        import setup_toshy

        config = setup_toshy.NixOSHandler.generate_udev_rules_nix()

        # Should contain Nix configuration structure
        assert 'services.udev.extraRules' in config
        assert 'SUBSYSTEM=="input"' in config
        assert 'KERNEL=="uinput"' in config
        assert 'GROUP="input"' in config
        assert 'MODE="0660"' in config

    def test_should_generate_user_groups_nix_config(self):
        """NixOSHandler should generate user groups configuration"""
        import setup_toshy

        username = "testuser"
        config = setup_toshy.NixOSHandler.generate_user_groups_nix(username)

        # Should contain user groups configuration
        assert f'users.users.{username}.extraGroups' in config
        assert '"input"' in config
        assert '"systemd-journal"' in config

    def test_should_generate_packages_nix_config(self):
        """NixOSHandler should generate packages list"""
        import setup_toshy

        config = setup_toshy.NixOSHandler.generate_packages_nix()

        # Should contain package list structure
        assert 'environment.systemPackages' in config
        assert 'with pkgs;' in config

        # Check for required packages
        required_packages = [
            'git', 'python3', 'dbus-python', 'libnotify',
            'zenity', 'cairo', 'gobject-introspection',
            'systemd', 'gcc', 'evtest'
        ]

        for package in required_packages:
            assert package in config

    def test_should_generate_full_config_snippet(self):
        """NixOSHandler should generate complete configuration.nix snippet"""
        import setup_toshy

        config = setup_toshy.NixOSHandler.generate_full_config_snippet()

        # Should be a complete Nix configuration
        assert '{ config, pkgs, ... }:' in config
        assert 'environment.systemPackages' in config
        assert 'services.udev.extraRules' in config
        assert 'users.users.' in config
        assert 'boot.kernelModules' in config
        assert '"uinput"' in config

        # Should have instructions
        assert 'configuration.nix' in config
        assert 'nixos-rebuild switch' in config

    def test_should_check_nixos_requirements_when_all_present(self):
        """NixOSHandler should return empty list when all tools present"""
        import setup_toshy

        # Mock shutil.which to return paths for all tools
        with mock.patch('shutil.which', return_value='/usr/bin/tool'):
            missing = setup_toshy.NixOSHandler.check_nixos_requirements()
            assert missing == []

    def test_should_check_nixos_requirements_when_some_missing(self):
        """NixOSHandler should return list of missing tools"""
        import setup_toshy

        # Mock shutil.which to return None for python3
        def mock_which(tool):
            if tool == 'python3':
                return None
            return '/usr/bin/' + tool

        with mock.patch('shutil.which', side_effect=mock_which):
            missing = setup_toshy.NixOSHandler.check_nixos_requirements()
            assert 'python3' in missing
            assert len(missing) == 1

    def test_should_check_nixos_requirements_when_all_missing(self):
        """NixOSHandler should return all tools when none present"""
        import setup_toshy

        # Mock shutil.which to return None for all tools
        with mock.patch('shutil.which', return_value=None):
            missing = setup_toshy.NixOSHandler.check_nixos_requirements()
            assert 'python3' in missing
            assert 'git' in missing
            assert 'gcc' in missing
            assert 'pkg-config' in missing
            assert len(missing) >= 4


class TestInstallUdevRulesNixOS:
    """Test install_udev_rules() behavior on NixOS"""

    def test_should_skip_udev_write_on_nixos(self, capsys):
        """install_udev_rules should skip direct installation on NixOS"""
        import setup_toshy

        # Create a mock config object
        mock_cnfg = mock.Mock()
        mock_cnfg.DISTRO_ID = 'nixos'
        mock_cnfg.separator = '=' * 80

        # Mock the global cnfg variable (create=True since it doesn't exist until runtime)
        with mock.patch('setup_toshy.cnfg', mock_cnfg, create=True):
            # Call install_udev_rules
            setup_toshy.install_udev_rules()

            # Capture output
            captured = capsys.readouterr()

            # Should print NixOS instructions
            assert 'NixOS detected' in captured.out
            assert 'udev rules must be configured declaratively' in captured.out
            assert 'services.udev.extraRules' in captured.out
            assert 'configuration.nix' in captured.out

    def test_should_not_call_sudo_on_nixos(self):
        """install_udev_rules should not attempt privileged operations on NixOS"""
        import setup_toshy

        # Create a mock config object
        mock_cnfg = mock.Mock()
        mock_cnfg.DISTRO_ID = 'nixos'
        mock_cnfg.separator = '=' * 80

        # Mock the global cnfg variable and subprocess (create=True since it doesn't exist until runtime)
        with mock.patch('setup_toshy.cnfg', mock_cnfg, create=True):
            with mock.patch('subprocess.run') as mock_run:
                # Call install_udev_rules
                setup_toshy.install_udev_rules()

                # Verify no subprocess calls were made (no sudo tee)
                mock_run.assert_not_called()

    def test_should_continue_normally_on_non_nixos(self, capsys):
        """install_udev_rules should not return early on non-NixOS systems"""
        import setup_toshy

        # Create a mock config object for non-NixOS
        mock_cnfg = mock.Mock()
        mock_cnfg.DISTRO_ID = 'fedora'
        mock_cnfg.separator = '=' * 80

        # Mock the global cnfg (create=True since it doesn't exist until runtime)
        with mock.patch('setup_toshy.cnfg', mock_cnfg, create=True):
            # Mock os.path.exists to prevent directory creation
            with mock.patch('os.path.exists', return_value=True):
                # Mock file operations
                with mock.patch('builtins.open', mock.mock_open(read_data='old content')):
                    try:
                        setup_toshy.install_udev_rules()
                    except SystemExit:
                        # Function might exit for other reasons, that's OK
                        pass

                    # Capture output
                    captured = capsys.readouterr()

                    # Should NOT print NixOS-specific messages
                    assert 'NixOS detected' not in captured.out
                    assert 'must be configured declaratively' not in captured.out

                    # Should proceed with normal udev installation
                    assert 'Installing "udev" rules file' in captured.out


class TestVerifyUserGroupsNixOS:
    """Test verify_user_groups() behavior on NixOS"""

    def test_should_skip_usermod_on_nixos(self, capsys):
        """verify_user_groups should skip direct usermod on NixOS"""
        import setup_toshy

        # Create a mock config object
        mock_cnfg = mock.Mock()
        mock_cnfg.DISTRO_ID = 'nixos'
        mock_cnfg.separator = '=' * 80

        # Mock environment
        with mock.patch('setup_toshy.cnfg', mock_cnfg, create=True):
            with mock.patch.dict('os.environ', {'USER': 'testuser'}):
                with mock.patch('subprocess.check_output', return_value=b'testuser : testuser adm cdrom'):
                    # Call verify_user_groups
                    setup_toshy.verify_user_groups()

                    # Capture output
                    captured = capsys.readouterr()

                    # Should print NixOS instructions
                    assert 'NixOS detected' in captured.out
                    assert 'user groups configured declaratively' in captured.out
                    assert 'users.users.testuser.extraGroups' in captured.out
                    assert 'configuration.nix' in captured.out

    def test_should_not_call_usermod_on_nixos(self):
        """verify_user_groups should not call usermod on NixOS"""
        import setup_toshy

        # Create a mock config object
        mock_cnfg = mock.Mock()
        mock_cnfg.DISTRO_ID = 'nixos'
        mock_cnfg.separator = '=' * 80

        # Mock the global cnfg variable
        with mock.patch('setup_toshy.cnfg', mock_cnfg, create=True):
            with mock.patch.dict('os.environ', {'USER': 'testuser'}):
                with mock.patch('subprocess.check_output', return_value=b'testuser : testuser input'):
                    with mock.patch('subprocess.run') as mock_run:
                        # Call verify_user_groups
                        setup_toshy.verify_user_groups()

                        # Verify usermod was not called
                        # (no subprocess.run calls should be made for adding groups)
                        mock_run.assert_not_called()

    def test_should_warn_if_user_missing_input_group_on_nixos(self, capsys):
        """verify_user_groups should warn if user not in input group on NixOS"""
        import setup_toshy

        # Create a mock config object
        mock_cnfg = mock.Mock()
        mock_cnfg.DISTRO_ID = 'nixos'
        mock_cnfg.separator = '=' * 80

        # Mock the global cnfg variable
        with mock.patch('setup_toshy.cnfg', mock_cnfg, create=True):
            with mock.patch.dict('os.environ', {'USER': 'testuser'}):
                # Mock groups output WITHOUT 'input' group
                with mock.patch('subprocess.check_output', return_value=b'testuser adm cdrom'):
                    # Call verify_user_groups
                    setup_toshy.verify_user_groups()

                    # Capture output
                    captured = capsys.readouterr()

                    # Should warn about missing input group
                    assert 'WARNING' in captured.out or 'not in "input" group' in captured.out


class TestNixOSHelperScript:
    """Test toshy-nixos-helper.sh script"""

    def test_helper_script_exists_and_executable(self):
        """Helper script should exist and be executable"""
        script_path = 'scripts/toshy-nixos-helper.sh'
        assert os.path.exists(script_path), f"Script not found: {script_path}"
        assert os.access(script_path, os.X_OK), f"Script not executable: {script_path}"

    def test_helper_script_has_shebang(self):
        """Helper script should have proper shebang"""
        with open('scripts/toshy-nixos-helper.sh', 'r') as f:
            first_line = f.readline()
            assert first_line.startswith('#!/'), "Missing shebang"
            assert 'bash' in first_line, "Should use bash"

    def test_helper_script_validates_nixos(self):
        """Helper script should validate it's running on NixOS"""
        # Read script content
        with open('scripts/toshy-nixos-helper.sh', 'r') as f:
            content = f.read()

        # Should check for NixOS
        assert '/etc/NIXOS' in content or 'ID=nixos' in content
        assert 'This script is for NixOS only' in content or 'ERROR' in content

    def test_helper_script_generates_complete_config(self):
        """Helper script should generate complete NixOS configuration"""
        with open('scripts/toshy-nixos-helper.sh', 'r') as f:
            content = f.read()

        # Should contain all required sections
        required_sections = [
            'configuration.nix',
            'environment.systemPackages',
            'services.udev.extraRules',
            'users.users.',
            'boot.kernelModules',
            'uinput',
            'nixos-rebuild switch'
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_helper_script_includes_required_packages(self):
        """Helper script should list all required packages"""
        with open('scripts/toshy-nixos-helper.sh', 'r') as f:
            content = f.read()

        required_packages = [
            'python3', 'git', 'gcc', 'pkg-config',
            'dbus-python', 'libnotify', 'zenity',
            'cairo', 'gobject-introspection', 'systemd'
        ]

        for package in required_packages:
            assert package in content, f"Missing package: {package}"


class TestCLIIntegration:
    """Test CLI argument parsing for NixOS support"""

    def test_should_have_nixos_in_list_distros_output(self):
        """list-distros command should include nixos"""
        import subprocess

        result = subprocess.run(
            ['./setup_toshy.py', 'list-distros'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Should complete successfully
        assert result.returncode == 0

        # Should list nixos
        assert 'nixos' in result.stdout.lower()

    def test_should_detect_nixos_in_show_env(self):
        """show-env command should detect NixOS when on NixOS"""
        # This test can only run on actual NixOS, so we'll make it conditional
        import subprocess
        import os
        import pytest

        # Check if we're on NixOS
        is_nixos = os.path.exists('/etc/NIXOS')
        if not is_nixos and os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                is_nixos = 'nixos' in f.read().lower()

        if not is_nixos:
            # Skip test on non-NixOS systems
            pytest.skip("Not running on NixOS")

        result = subprocess.run(
            ['./setup_toshy.py', 'show-env'],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        assert 'nixos' in result.stdout.lower()
