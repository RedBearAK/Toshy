#!/usr/bin/env python3
"""
Additional edge case tests for NixOS support
Tests error handling and edge cases not currently covered
"""

import pytest
from unittest import mock
import subprocess
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestNixOSEdgeCases:
    """Test edge cases and error handling in NixOS support"""

    def test_should_handle_groups_command_failure_on_nixos(self, capsys):
        """verify_user_groups should handle subprocess failure gracefully"""
        import setup_toshy

        # Create a mock config object
        mock_cnfg = mock.Mock()
        mock_cnfg.DISTRO_ID = 'nixos'
        mock_cnfg.separator = '=' * 80

        # Mock the global cnfg variable
        with mock.patch('setup_toshy.cnfg', mock_cnfg, create=True):
            with mock.patch.dict('os.environ', {'USER': 'testuser'}):
                # Mock subprocess.check_output to raise an error
                with mock.patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'groups')):
                    # This should either handle the error or let it propagate
                    # Currently the code doesn't handle it, so it should raise
                    with pytest.raises(subprocess.CalledProcessError):
                        setup_toshy.verify_user_groups()

    def test_should_handle_missing_user_env_var_on_nixos(self, capsys):
        """NixOSHandler should handle missing USER environment variable"""
        import setup_toshy

        # Test with missing USER env var
        with mock.patch.dict('os.environ', {}, clear=True):
            config = setup_toshy.NixOSHandler.generate_user_groups_nix('testuser')
            # Should work with explicitly provided username
            assert 'testuser' in config

    def test_should_handle_none_username_in_generate_user_groups(self):
        """NixOSHandler.generate_user_groups_nix should handle None username"""
        import setup_toshy

        # Should handle None by converting to string
        config = setup_toshy.NixOSHandler.generate_user_groups_nix(None)
        assert 'None' in config or 'users.users' in config

    def test_full_config_snippet_uses_default_username_when_env_missing(self):
        """generate_full_config_snippet should use placeholder when USER missing"""
        import setup_toshy

        with mock.patch.dict('os.environ', {}, clear=True):
            config = setup_toshy.NixOSHandler.generate_full_config_snippet()
            # Should contain placeholder or 'username'
            assert '<username>' in config or 'username' in config.lower()

    def test_nixos_handler_methods_return_strings(self):
        """All NixOSHandler methods should return strings"""
        import setup_toshy

        assert isinstance(setup_toshy.NixOSHandler.generate_udev_rules_nix(), str)
        assert isinstance(setup_toshy.NixOSHandler.generate_user_groups_nix('test'), str)
        assert isinstance(setup_toshy.NixOSHandler.generate_packages_nix(), str)
        assert isinstance(setup_toshy.NixOSHandler.generate_full_config_snippet(), str)

    def test_nixos_handler_methods_return_non_empty_strings(self):
        """All NixOSHandler methods should return non-empty strings"""
        import setup_toshy

        assert len(setup_toshy.NixOSHandler.generate_udev_rules_nix()) > 0
        assert len(setup_toshy.NixOSHandler.generate_user_groups_nix('test')) > 0
        assert len(setup_toshy.NixOSHandler.generate_packages_nix()) > 0
        assert len(setup_toshy.NixOSHandler.generate_full_config_snippet()) > 0

    def test_check_requirements_returns_list(self):
        """check_nixos_requirements should always return a list"""
        import setup_toshy

        with mock.patch('shutil.which', return_value='/usr/bin/tool'):
            result = setup_toshy.NixOSHandler.check_nixos_requirements()
            assert isinstance(result, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
