#!/usr/bin/env python3
"""
Tests for NixOS package integrity and hash validation

Following TDD RED-GREEN-REFACTOR cycle:
- Write tests first (RED) - These tests verify package quality
- Implement fixes to pass (GREEN)
- Refactor while keeping tests green (REFACTOR)
"""

import os
import re
import pytest
from pathlib import Path


class TestPackageHashes:
    """Test that package derivations use real hashes, not placeholders"""

    def test_should_allow_placeholder_hash_if_src_can_be_overridden(self):
        """toshy.nix can use placeholder if src parameter allows override (flake pattern)"""
        toshy_nix_path = Path(__file__).parent.parent.parent / "nix" / "packages" / "toshy.nix"

        assert toshy_nix_path.exists(), f"toshy.nix not found at {toshy_nix_path}"

        with open(toshy_nix_path, 'r') as f:
            content = f.read()

        # Check if src is a parameter (allowing override)
        has_src_param = re.search(r'{\s*[^}]*\bsrc\s*\?', content, re.MULTILINE)

        if has_src_param:
            # If src can be overridden, placeholder is acceptable
            # because flake will override with `src = self`
            assert 'src = if src != null' in content or 'src = src' in content or 'inherit src' in content, \
                "If src is a parameter, it should be used (not ignored)"

            # Should document that hash is placeholder
            assert 'Placeholder' in content or 'placeholder' in content or 'Update when' in content, \
                "Should document that hash is a placeholder when src can be overridden"
        else:
            # If src cannot be overridden, must have real hash
            placeholder_patterns = [
                r'hash\s*=\s*"sha256-A{40,}=?"',  # All A's
                r'hash\s*=\s*"sha256-0{40,}=?"',  # All 0's
                r'hash\s*=\s*"lib\.fakeHash',     # Nix lib.fakeHash
            ]

            for pattern in placeholder_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert len(matches) == 0, \
                    f"Found placeholder hash in toshy.nix without src override capability: {matches}"

    def test_should_not_use_placeholder_hash_in_xwaykeyz_package(self):
        """xwaykeyz.nix should use real SHA256 hash, not placeholder"""
        xwaykeyz_nix_path = Path(__file__).parent.parent.parent / "nix" / "packages" / "xwaykeyz.nix"

        assert xwaykeyz_nix_path.exists(), f"xwaykeyz.nix not found at {xwaykeyz_nix_path}"

        with open(xwaykeyz_nix_path, 'r') as f:
            content = f.read()

        # xwaykeyz already has a real hash, but verify it's valid format
        hash_pattern = r'hash\s*=\s*"sha256-([A-Za-z0-9+/=]+)"'
        matches = re.findall(hash_pattern, content)

        assert len(matches) > 0, "No hash found in xwaykeyz.nix"

        for hash_value in matches:
            # Check it's not a placeholder (all same character)
            assert not all(c == hash_value[0] for c in hash_value), \
                f"Hash appears to be placeholder: {hash_value}"

            # SHA256 base64 should be 43-44 chars
            assert 40 <= len(hash_value) <= 45, \
                f"Hash length suspicious: {len(hash_value)} chars"

    def test_should_have_valid_git_rev_or_src_override(self):
        """Package derivations should reference valid git commits or allow src override"""
        for package_file in ['toshy.nix', 'xwaykeyz.nix']:
            package_path = Path(__file__).parent.parent.parent / "nix" / "packages" / package_file

            with open(package_path, 'r') as f:
                content = f.read()

            # Check if src can be overridden
            has_src_param = re.search(r'{\s*[^}]*\bsrc\s*\?', content, re.MULTILINE)

            # Look for rev = "...";
            rev_pattern = r'rev\s*=\s*"([^"]+)"'
            matches = re.findall(rev_pattern, content)

            assert len(matches) > 0, f"No git rev found in {package_file}"

            for rev in matches:
                # If src can be overridden (flake pattern), branch names are OK
                if has_src_param and package_file == 'toshy.nix':
                    # For toshy with src override, any rev is acceptable
                    # (it won't be used when building from flake)
                    continue

                # For packages without src override, must be specific commit
                assert rev not in ['HEAD', 'main', 'master', 'latest', 'CHANGEME'], \
                    f"Placeholder rev in {package_file}: {rev}. " \
                    f"Either pin to specific commit or add src parameter for override."

                # If it looks like a commit hash, should be 40 chars (or 7+ for short)
                if re.match(r'^[a-f0-9]+$', rev):
                    assert len(rev) >= 7, \
                        f"Git commit hash too short in {package_file}: {rev}"


class TestPackageMetadata:
    """Test that package derivations have proper metadata"""

    def test_should_have_description_in_toshy_package(self):
        """toshy.nix should have a description in meta"""
        toshy_nix_path = Path(__file__).parent.parent.parent / "nix" / "packages" / "toshy.nix"

        with open(toshy_nix_path, 'r') as f:
            content = f.read()

        # Should have meta.description
        assert 'description' in content, "Missing description in toshy.nix meta"
        assert 'Keyboard remapper' in content or 'keyboard' in content.lower(), \
            "Description should mention keyboard remapping"

    def test_should_have_license_in_packages(self):
        """Package derivations should declare license"""
        for package_file in ['toshy.nix', 'xwaykeyz.nix']:
            package_path = Path(__file__).parent.parent.parent / "nix" / "packages" / package_file

            with open(package_path, 'r') as f:
                content = f.read()

            # Should have license declaration
            assert 'license' in content, f"Missing license in {package_file}"
            assert 'gpl3' in content.lower() or 'licenses.gpl' in content, \
                f"Should declare GPL license in {package_file}"

    def test_should_have_homepage_in_packages(self):
        """Package derivations should have homepage"""
        for package_file in ['toshy.nix', 'xwaykeyz.nix']:
            package_path = Path(__file__).parent.parent.parent / "nix" / "packages" / package_file

            with open(package_path, 'r') as f:
                content = f.read()

            # Should have homepage
            assert 'homepage' in content, f"Missing homepage in {package_file}"
            assert 'github.com/RedBearAK' in content, \
                f"Homepage should point to correct GitHub repo in {package_file}"


class TestPackageStructure:
    """Test that package derivations are well-structured"""

    def test_should_use_fetchFromGitHub_for_sources(self):
        """Packages should use fetchFromGitHub for clarity"""
        for package_file in ['toshy.nix', 'xwaykeyz.nix']:
            package_path = Path(__file__).parent.parent.parent / "nix" / "packages" / package_file

            with open(package_path, 'r') as f:
                content = f.read()

            # Should use fetchFromGitHub (cleaner than fetchurl for GitHub)
            assert 'fetchFromGitHub' in content, \
                f"{package_file} should use fetchFromGitHub"

    def test_should_have_proper_python_dependencies(self):
        """toshy.nix should declare Python dependencies correctly"""
        toshy_nix_path = Path(__file__).parent.parent.parent / "nix" / "packages" / "toshy.nix"

        with open(toshy_nix_path, 'r') as f:
            content = f.read()

        # Should have Python environment with packages
        assert 'python3.withPackages' in content or 'pythonEnv' in content, \
            "Should create Python environment with packages"

        # Should include key dependencies
        required_deps = ['dbus-python', 'pygobject3', 'watchdog', 'psutil', 'evdev']
        for dep in required_deps:
            assert dep in content, f"Missing required Python dependency: {dep}"

    def test_should_use_makeWrapper_for_bin_commands(self):
        """toshy.nix should use makeWrapper for executable scripts"""
        toshy_nix_path = Path(__file__).parent.parent.parent / "nix" / "packages" / "toshy.nix"

        with open(toshy_nix_path, 'r') as f:
            content = f.read()

        # Should use makeWrapper
        assert 'makeWrapper' in content, \
            "Should use makeWrapper for creating executables"

        # Should set PYTHONPATH
        assert 'PYTHONPATH' in content, \
            "Should set PYTHONPATH for Python modules to be found"


class TestFlakeStructure:
    """Test that flake.nix is well-structured"""

    def test_should_override_toshy_src_in_flake(self):
        """flake.nix should override toshy src to use flake's own source"""
        flake_nix_path = Path(__file__).parent.parent.parent / "flake.nix"

        assert flake_nix_path.exists(), "flake.nix not found"

        with open(flake_nix_path, 'r') as f:
            content = f.read()

        # Should pass src = self to toshy package
        assert 'src = self' in content, \
            "flake.nix should override toshy src with 'src = self' to use flake source"

        # Should be in the toshy package call
        toshy_call_pattern = r'toshy\s*=.*callPackage.*toshy\.nix.*\{[^}]*src\s*=\s*self'
        assert re.search(toshy_call_pattern, content, re.DOTALL), \
            "src = self should be passed to toshy package in callPackage"

    def test_should_have_overlay_in_flake(self):
        """flake.nix should provide overlay for nixpkgs"""
        flake_nix_path = Path(__file__).parent.parent.parent / "flake.nix"

        assert flake_nix_path.exists(), "flake.nix not found"

        with open(flake_nix_path, 'r') as f:
            content = f.read()

        # Should have overlay
        assert 'overlay' in content, "flake.nix should define overlay"
        assert 'xwaykeyz' in content, "Overlay should include xwaykeyz"
        assert 'toshy' in content, "Overlay should include toshy"

    def test_should_have_nixos_and_home_manager_modules(self):
        """flake.nix should export NixOS and home-manager modules"""
        flake_nix_path = Path(__file__).parent.parent.parent / "flake.nix"

        with open(flake_nix_path, 'r') as f:
            content = f.read()

        # Should export modules
        assert 'nixosModules' in content, "Should export nixosModules"
        assert 'homeManagerModules' in content, "Should export homeManagerModules"

        # Should reference module files
        assert 'nix/modules/nixos.nix' in content or './nix/modules/nixos.nix' in content
        assert 'nix/modules/home-manager.nix' in content or './nix/modules/home-manager.nix' in content

    def test_should_have_checks_for_integration_tests(self):
        """flake.nix should define checks for integration tests"""
        flake_nix_path = Path(__file__).parent.parent.parent / "flake.nix"

        with open(flake_nix_path, 'r') as f:
            content = f.read()

        # Should have checks attribute
        assert 'checks' in content, "flake.nix should define checks"

        # Should include key integration tests
        test_names = [
            'toshy-basic-test',
            'toshy-home-manager-test',
            'toshy-multi-de-test',
        ]

        for test_name in test_names:
            assert test_name in content, f"checks should include {test_name}"


class TestGNOMEExtensionPackage:
    """
    Test GNOME Shell extension package integrity

    Regression tests for commit 462da82: Fix GNOME extension: use correct commit hash

    The extension package should use a specific commit hash rather than a version tag
    to ensure reproducibility and avoid breakage from upstream changes.
    """

    def test_should_use_specific_commit_hash_for_gnome_extension(self):
        """
        Verify extension uses commit hash, not version tag.

        The extension should use:
        - rev = "e7917a98fe9d4e7b8e9b16c127adbb17642d0b6e"

        Not:
        - rev = "v${version}"
        """
        extension_nix = Path(__file__).parent.parent.parent / "nix/packages/gnome-shell-extension-focused-window-dbus.nix"

        with open(extension_nix, 'r') as f:
            content = f.read()

        # ASSERT - Should use specific commit hash
        assert 'rev = "e7917a98fe9d4e7b8e9b16c127adbb17642d0b6e"' in content, \
            "Extension should use specific commit hash"

    def test_gnome_extension_should_not_use_version_tag_as_rev(self):
        """
        Verify rev is not a version tag.

        Using `rev = "v${version}"` can break when upstream changes tags.
        Using a commit hash is more stable.
        """
        extension_nix = Path(__file__).parent.parent.parent / "nix/packages/gnome-shell-extension-focused-window-dbus.nix"

        with open(extension_nix, 'r') as f:
            content = f.read()

        # ASSERT - Should NOT use version variable in rev
        assert 'rev = "v${version}"' not in content, \
            "Extension rev should not use version tag pattern"
        assert 'rev = "${version}"' not in content, \
            "Extension rev should not interpolate version variable"

    def test_gnome_extension_hash_should_match_commit(self):
        """
        Verify hash matches specified commit.

        The hash should be:
        sha256-oHx7ZlsTGWfbrSqnZB/XdcTsjeiOjZCHmu7stV9686Y=

        This corresponds to commit e7917a98fe9d4e7b8e9b16c127adbb17642d0b6e
        """
        extension_nix = Path(__file__).parent.parent.parent / "nix/packages/gnome-shell-extension-focused-window-dbus.nix"

        with open(extension_nix, 'r') as f:
            content = f.read()

        # ASSERT - Hash should match commit
        expected_hash = "sha256-oHx7ZlsTGWfbrSqnZB/XdcTsjeiOjZCHmu7stV9686Y="
        assert f'hash = "{expected_hash}"' in content, \
            f"Extension hash should be {expected_hash}"

    def test_should_use_unstable_version_format(self):
        """
        Verify version uses unstable date format.

        Since we're using a specific commit rather than a release,
        the version should be formatted as "unstable-YYYY-MM-DD"
        """
        extension_nix = Path(__file__).parent.parent.parent / "nix/packages/gnome-shell-extension-focused-window-dbus.nix"

        with open(extension_nix, 'r') as f:
            content = f.read()

        # ASSERT - Should use unstable version format
        assert 'version = "unstable-2024-08-08"' in content, \
            "Extension version should use unstable date format"

    def test_gnome_extension_should_have_correct_uuid(self):
        """
        Verify extension UUID is correct.

        The extension UUID should match the one expected by GNOME Shell:
        focused-window-dbus@flexagoon.com
        """
        extension_nix = Path(__file__).parent.parent.parent / "nix/packages/gnome-shell-extension-focused-window-dbus.nix"

        with open(extension_nix, 'r') as f:
            content = f.read()

        # ASSERT - UUID should be correct
        assert 'uuid = "focused-window-dbus@flexagoon.com"' in content, \
            "Extension UUID should be focused-window-dbus@flexagoon.com"

    def test_gnome_extension_should_fetch_from_correct_repo(self):
        """
        Verify extension is fetched from correct GitHub repository.

        Should fetch from: flexagoon/focused-window-dbus
        """
        extension_nix = Path(__file__).parent.parent.parent / "nix/packages/gnome-shell-extension-focused-window-dbus.nix"

        with open(extension_nix, 'r') as f:
            content = f.read()

        # ASSERT - Should fetch from correct repo
        assert 'owner = "flexagoon"' in content, \
            "Extension should be owned by flexagoon"
        assert 'repo = "focused-window-dbus"' in content, \
            "Extension repo should be focused-window-dbus"

    def test_gnome_extension_should_install_to_correct_location(self):
        """
        Verify extension installs to correct GNOME Shell extensions directory.

        Extensions should be installed to:
        $out/share/gnome-shell/extensions/${uuid}
        """
        extension_nix = Path(__file__).parent.parent.parent / "nix/packages/gnome-shell-extension-focused-window-dbus.nix"

        with open(extension_nix, 'r') as f:
            content = f.read()

        # ASSERT - Should install to correct location
        assert 'share/gnome-shell/extensions/${uuid}' in content, \
            "Extension should install to GNOME Shell extensions directory"

    def test_gnome_extension_should_have_proper_metadata(self):
        """
        Verify extension package has proper metadata.

        Should include:
        - description
        - homepage
        - license (GPL-3.0-plus)
        """
        extension_nix = Path(__file__).parent.parent.parent / "nix/packages/gnome-shell-extension-focused-window-dbus.nix"

        with open(extension_nix, 'r') as f:
            content = f.read()

        # ASSERT - Should have metadata
        assert 'description' in content, "Extension should have description"
        assert 'homepage' in content, "Extension should have homepage"
        assert 'license' in content, "Extension should have license"
        assert 'gpl3Plus' in content or 'GPL-3.0' in content, \
            "Extension should be GPL-3.0 licensed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
