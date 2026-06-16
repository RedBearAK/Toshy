#!/usr/bin/bash


# Run the Toshy keyboard-layout context module to show the detected
# layout, the correction map it produces, and live layout-change events
# (this exercises the detector and analyzer behind the context module)

# shellcheck disable=SC2034
VERSION='20260608'

# Check if the script is being run as root
if [[ $EUID -eq 0 ]]; then
    echo "This script must not be run as root"
    exit 1
fi

# Check if $USER and $HOME environment variables are not empty
if [[ -z $USER ]] || [[ -z $HOME ]]; then
    echo "\$USER and/or \$HOME environment variables are not set. We need them."
    exit 1
fi


# Absolute path to the venv
VENV_PATH="${HOME}/.config/toshy/.venv"

# Verify the venv directory exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Activate the venv for complete environment setup
# shellcheck disable=SC1091
source "${VENV_PATH}/bin/activate"

# Need PYTHONPATH update to allow absolute imports from "toshy_common" package
export PYTHONPATH="${HOME}/.config/toshy:${PYTHONPATH}"

# Launched as a module (-m) rather than by file path: with the package root on
# PYTHONPATH this runs with proper package context, so only real "toshy_common.*"
# imports resolve. A stray bare sibling import fails loudly instead of silently
# working off the module's own directory (which is what the file-path form allows).
exec "${VENV_PATH}/bin/python" -m toshy_common.kblayout_context
