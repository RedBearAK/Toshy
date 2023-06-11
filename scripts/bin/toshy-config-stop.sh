#!/usr/bin/env bash


# Stop the Toshy manual script

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

echo -e "Stopping Toshy manual config script...\n"

pkill -f "/bin/keyszer"
pkill -f "toshy-config-start"
pkill -f "toshy_config"
