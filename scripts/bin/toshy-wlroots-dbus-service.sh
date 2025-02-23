#!/usr/bin/env bash


# Start Toshy Wlroots D-Bus service, after terminating existing
# processes and activating Python virtual environment

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

TOSHY_CFG="${HOME}/.config/toshy"
TOSHY_WLROOTS="${TOSHY_CFG}/wlroots-dbus-service"
FILE_NAME="toshy_wlroots_dbus_service"

pkill -f "${FILE_NAME}"

sleep 0.5

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

# start the script that will create the D-Bus object/interface
"${VENV_PATH}/bin/python" "${TOSHY_WLROOTS}/${FILE_NAME}.py"
