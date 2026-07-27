#!/usr/bin/env bash


# Show the devices that xwaykeyz or keyszer sees

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


# Resolve and activate the Toshy Python runtime (venv or external)
# shellcheck disable=SC1091
source "$HOME/.config/toshy/scripts/toshy-runtime-env.sh" || exit 1

echo -e "\nList of devices seen by the keymapper (xwaykeyz or keyszer): \n"

if command -v xwaykeyz >/dev/null 2>&1; then
    exec xwaykeyz --list-devices
else
    echo -e "The \"xwaykeyz\" command was not found in: \n$PATH."
    exit 1
fi
