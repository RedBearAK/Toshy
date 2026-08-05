#!/usr/bin/bash
# shellcheck disable=SC2034
VERSION='20260804'


# Run the Toshy terminal menu: a terminal-based counterpart to the tray
# icon menu, for systems without GTK or with misbehaving tray menus.
# Shows live service status and allows changing all Toshy preferences.

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

exec "${VENV_PATH}/bin/python" \
    "${HOME}/.config/toshy/toshy_common/terminal_menu/tmenu_main.py" "$@"
