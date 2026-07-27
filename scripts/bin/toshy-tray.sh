#!/usr/bin/env bash


# Start Toshy GUI app after activating venv

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


# Set the process name for the Toshy Tray app launcher process
# echo "toshy-tray-stub" > /proc/$$/comm
# REMOVING: This seems to confuse systemd and cause error messages in the journal

# Absolute path to the venv
VENV_PATH="$HOME/.config/toshy/.venv"

# Verify the venv directory exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Activate the venv for complete environment setup
# shellcheck disable=SC1091
source "${VENV_PATH}/bin/activate"

# Seems to be unreliable to get program name to become "toshy-tray-app" but
# it works sometimes.
# The 'exec' should at least reduce some RAM usage by replacing this shell.
exec "${VENV_PATH}/bin/python" "$HOME/.config/toshy/toshy_tray.py"
