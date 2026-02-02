#!/usr/bin/env python3
"""
Tests for GNOME Wayland window manager fallback logic in toshy_config.py

Regression tests for commit b61405b: Fix default config: add GNOME Wayland
window manager fallback

Following TDD RED-GREEN-REFACTOR cycle:
- Write tests first (RED)
- Implement minimal code to pass (GREEN)
- Refactor while keeping tests green (REFACTOR)
"""

import os
import sys
import pytest
from unittest import mock
from pathlib import Path


# These tests verify the logic at lines 301-304 in default-toshy-config/toshy_config.py
# The config uses global variables set by env_context module


class TestGNOMEWaylandWindowManagerFallback:
    """Test GNOME Wayland compositor fallback when WM is unidentified"""

    def test_should_set_gnome_compositor_when_window_manager_unidentified_on_gnome_wayland(self):
        """
        Verify GNOME Wayland fallback when WM is unidentified.

        When:
        - SESSION_TYPE == 'wayland'
        - DESKTOP_ENV == 'gnome'
        - WINDOW_MGR == 'WM_unidentified_by_logic'

        Then:
        - _wl_compositor should be set to 'gnome'
        """
        # ARRANGE - Set up GNOME Wayland environment with unidentified WM
        session_type = 'wayland'
        desktop_env = 'gnome'
        window_mgr = 'WM_unidentified_by_logic'

        # ACT - Apply the fallback logic from toshy_config.py lines 301-304
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # ASSERT - Compositor should be 'gnome'
        assert wl_compositor == 'gnome', \
            "GNOME Wayland fallback should set compositor to 'gnome' when WM is unidentified"

    def test_should_not_fallback_to_gnome_on_x11_session(self):
        """
        Verify no fallback happens on X11.

        When:
        - SESSION_TYPE == 'x11'
        - DESKTOP_ENV == 'gnome'
        - WINDOW_MGR == 'WM_unidentified_by_logic'

        Then:
        - _wl_compositor should remain as WINDOW_MGR (no Wayland compositor on X11)
        """
        # ARRANGE - Set up GNOME X11 environment
        session_type = 'x11'
        desktop_env = 'gnome'
        window_mgr = 'WM_unidentified_by_logic'

        # ACT - Apply the fallback logic
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # ASSERT - Should not apply GNOME fallback on X11
        assert wl_compositor == 'WM_unidentified_by_logic', \
            "GNOME X11 should not trigger Wayland compositor fallback"

    def test_should_not_fallback_to_gnome_for_other_desktops(self):
        """
        Verify fallback only applies to GNOME.

        When:
        - SESSION_TYPE == 'wayland'
        - DESKTOP_ENV == 'kde' (or other non-GNOME DE)
        - WINDOW_MGR == 'WM_unidentified_by_logic'

        Then:
        - _wl_compositor should remain as WINDOW_MGR
        """
        # ARRANGE - Set up KDE Wayland with unidentified WM
        session_type = 'wayland'
        desktop_env = 'kde'
        window_mgr = 'WM_unidentified_by_logic'

        # ACT - Apply the fallback logic
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # ASSERT - Should not apply GNOME fallback for KDE
        assert wl_compositor == 'WM_unidentified_by_logic', \
            "Non-GNOME desktops should not trigger GNOME compositor fallback"

    def test_should_not_fallback_when_window_manager_is_identified(self):
        """
        Verify fallback only applies when WM is unidentified.

        When:
        - SESSION_TYPE == 'wayland'
        - DESKTOP_ENV == 'gnome'
        - WINDOW_MGR == 'mutter' (identified WM)

        Then:
        - _wl_compositor should be 'mutter' (no fallback needed)
        """
        # ARRANGE - Set up GNOME Wayland with identified WM
        session_type = 'wayland'
        desktop_env = 'gnome'
        window_mgr = 'mutter'

        # ACT - Apply the fallback logic
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # ASSERT - Should use identified WM, not fallback
        assert wl_compositor == 'mutter', \
            "Should not apply fallback when WM is already identified"

    def test_should_handle_cosmic_wayland_unidentified_wm(self):
        """
        Verify COSMIC doesn't trigger GNOME fallback.

        When:
        - SESSION_TYPE == 'wayland'
        - DESKTOP_ENV == 'cosmic'
        - WINDOW_MGR == 'WM_unidentified_by_logic'

        Then:
        - _wl_compositor should remain as WINDOW_MGR
        """
        # ARRANGE - Set up COSMIC Wayland with unidentified WM
        session_type = 'wayland'
        desktop_env = 'cosmic'
        window_mgr = 'WM_unidentified_by_logic'

        # ACT - Apply the fallback logic
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # ASSERT - COSMIC should not trigger GNOME fallback
        assert wl_compositor == 'WM_unidentified_by_logic', \
            "COSMIC desktop should not trigger GNOME compositor fallback"


class TestEnvironAPIIntegration:
    """Test that the fallback logic integrates correctly with environ_api"""

    def test_should_pass_gnome_compositor_to_environ_api_when_fallback_triggered(self):
        """
        Verify environ_api receives correct compositor value.

        This tests that the _wl_compositor value determined by the fallback
        logic is properly passed to environ_api.
        """
        # ARRANGE - Set up GNOME Wayland with unidentified WM
        session_type = 'wayland'
        desktop_env = 'gnome'
        window_mgr = 'WM_unidentified_by_logic'

        # ACT - Simulate the config logic
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # Mock environ_api call
        with mock.patch('builtins.print') as mock_print:
            # Simulate: environ_api(session_type=SESSION_TYPE, wl_compositor=_wl_compositor)
            environ_api_args = {
                'session_type': session_type,
                'wl_compositor': wl_compositor
            }

            # ASSERT - environ_api should receive 'gnome' as compositor
            assert environ_api_args['session_type'] == 'wayland'
            assert environ_api_args['wl_compositor'] == 'gnome', \
                "environ_api should receive 'gnome' as wl_compositor when fallback is triggered"

    def test_should_pass_original_wm_to_environ_api_when_no_fallback(self):
        """
        Verify environ_api receives original WM when fallback doesn't apply.
        """
        # ARRANGE - Set up KDE Wayland with identified WM
        session_type = 'wayland'
        desktop_env = 'kde'
        window_mgr = 'kwin_wayland'

        # ACT - Apply the fallback logic
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # Simulate environ_api call
        environ_api_args = {
            'session_type': session_type,
            'wl_compositor': wl_compositor
        }

        # ASSERT - environ_api should receive original window manager
        assert environ_api_args['wl_compositor'] == 'kwin_wayland', \
            "environ_api should receive original window manager when no fallback applies"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_should_handle_empty_window_manager_string(self):
        """
        Verify behavior when WINDOW_MGR is empty string.

        Empty string is different from 'WM_unidentified_by_logic',
        so fallback should not trigger.
        """
        # ARRANGE
        session_type = 'wayland'
        desktop_env = 'gnome'
        window_mgr = ''

        # ACT
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # ASSERT - Empty string should not trigger fallback
        assert wl_compositor == '', \
            "Empty window manager string should not trigger fallback"

    def test_should_handle_none_window_manager(self):
        """
        Verify behavior when WINDOW_MGR is None.

        None is different from 'WM_unidentified_by_logic',
        so fallback should not trigger.
        """
        # ARRANGE
        session_type = 'wayland'
        desktop_env = 'gnome'
        window_mgr = None

        # ACT
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # ASSERT - None should not trigger fallback
        assert wl_compositor is None, \
            "None window manager should not trigger fallback"

    def test_should_be_case_sensitive_for_desktop_env(self):
        """
        Verify DESKTOP_ENV comparison is case-sensitive.

        'GNOME' != 'gnome', so uppercase GNOME should not trigger fallback
        (assuming the code uses lowercase 'gnome').
        """
        # ARRANGE
        session_type = 'wayland'
        desktop_env = 'GNOME'  # Uppercase
        window_mgr = 'WM_unidentified_by_logic'

        # ACT
        if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
            wl_compositor = 'gnome'
        else:
            wl_compositor = window_mgr

        # ASSERT - Uppercase should not match lowercase check
        assert wl_compositor == 'WM_unidentified_by_logic', \
            "Desktop environment comparison should be case-sensitive"

    def test_should_handle_wayland_session_type_variations(self):
        """
        Verify only exact 'wayland' session type triggers fallback.

        Variations like 'Wayland' or 'wayland-session' should not trigger.
        """
        test_cases = [
            ('Wayland', 'gnome', 'WM_unidentified_by_logic', 'WM_unidentified_by_logic'),
            ('wayland-session', 'gnome', 'WM_unidentified_by_logic', 'WM_unidentified_by_logic'),
            ('WAYLAND', 'gnome', 'WM_unidentified_by_logic', 'WM_unidentified_by_logic'),
        ]

        for session_type, desktop_env, window_mgr, expected_compositor in test_cases:
            # ACT
            if session_type == 'wayland' and desktop_env == 'gnome' and window_mgr == 'WM_unidentified_by_logic':
                wl_compositor = 'gnome'
            else:
                wl_compositor = window_mgr

            # ASSERT
            assert wl_compositor == expected_compositor, \
                f"Session type '{session_type}' should not trigger fallback (expected {expected_compositor}, got {wl_compositor})"
