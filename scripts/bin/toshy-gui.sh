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


# Set the process name for the Toshy Preferences GUI app launcher process
# echo "toshy-pref-stub" > /proc/$$/comm
# REMOVING: This seems to confuse systemd and cause error messages in the journal

# Resolve and activate the Toshy Python runtime (venv or external)
# shellcheck disable=SC1091
source "$HOME/.config/toshy/scripts/toshy-runtime-env.sh" || exit 1

# Original exec command before modularising toshy_gui app package:
# exec "${TOSHY_PYTHON}" "$HOME/.config/toshy/toshy_gui.py"

# Launch GUI app as a Python "module":
export PYTHONPATH="${HOME}/.config/toshy:${PYTHONPATH}"
exec "${TOSHY_PYTHON}" -m toshy_gui "$@"
