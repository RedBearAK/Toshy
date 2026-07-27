#!/usr/bin/env bash


# Start Toshy COSMIC D-Bus service, after terminating existing
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
TOSHY_COSMIC="${TOSHY_CFG}/cosmic-dbus-service"
FILE_NAME="toshy_cosmic_dbus_service"

pkill -f "${FILE_NAME}"

sleep 0.5

# Resolve and activate the Toshy Python runtime (venv or external)
# shellcheck disable=SC1091
source "$HOME/.config/toshy/scripts/toshy-runtime-env.sh" || exit 1

# start the script that will create the D-Bus object/interface
# use "-u" option on Python to enable unbuffered output mode
exec "${TOSHY_PYTHON}" -u "${TOSHY_COSMIC}/${FILE_NAME}.py"
