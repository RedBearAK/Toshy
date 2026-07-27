#!/usr/bin/env bash

# Tell the user how to activate the Toshy Python runtime, and activate
# it when this script is sourced (via the 'toshy-venv' command alias).

# Check if the script is being run as root
if [[ $EUID -eq 0 ]]; then
    echo "This script must not be run as root"
    return 1  # Use return instead of exit when script is sourced
fi

# Check if $USER and $HOME environment variables are not empty
if [[ -z $USER ]] || [[ -z $HOME ]]; then
    echo "\$USER and/or \$HOME environment variables are not set. We need them."
    return 1  # Use return instead of exit when script is sourced
fi

if [[ -z "$VIRTUAL_ENV" ]]; then
    # If the VIRTUAL_ENV variable is empty, the virtual environment is not active.
    echo -e "\n To activate the Toshy Python runtime, run this command: \n"
    echo -e "\t\t\t source toshy-venv \n"
    echo -e " (Ignore the text above if you've already run the command as shown.) \n"
else
    # If the VIRTUAL_ENV variable is not empty, the virtual environment is active.
    echo -e "\n The Toshy Python virtual environment is ACTIVE in this shell already.\n"
    return 0
fi

# Resolve and activate the Toshy Python runtime (venv or external)
# shellcheck disable=SC1091
source "$HOME/.config/toshy/scripts/toshy-runtime-env.sh" || return 1

if [[ -z "$VIRTUAL_ENV" ]]; then
    # Runtime resolved but no venv activation happened: externally managed.
    echo -e " NOTE: The Toshy runtime is externally managed (not a venv):"
    echo -e "\t${TOSHY_RUNTIME_DIR}"
    echo -e " Its bin folder has been placed at the front of PATH in this shell.\n"
fi
