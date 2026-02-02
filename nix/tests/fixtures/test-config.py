#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test configuration file for Toshy custom config testing.
This file has a marker comment to verify it's being used.
"""

# MARKER: CUSTOM_TEST_CONFIG_LOADED

# Minimal valid xwaykeyz configuration
from xwaykeyz.models import keymap, modmap

# Basic modmap for testing
modmap("Test Modmap", {
    # Empty modmap, just needs to be valid
})

# Basic keymap for testing
keymap("Test Keymap", {
    # Empty keymap, just needs to be valid
})

print("TEST CONFIG: Custom Toshy test config loaded successfully")
