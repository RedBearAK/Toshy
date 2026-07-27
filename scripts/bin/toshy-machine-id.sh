#!/usr/bin/env bash


# Run the Toshy machine context module to get the hashed machine ID, for
# use in the config file with 'if' conditions or keymap conditionals.

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
VENV_PATH="$HOME/.config/toshy/.venv"

# Verify the venv directory exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Activate the venv for complete environment setup
# shellcheck disable=SC1091
source "${VENV_PATH}/bin/activate"

# Fix the PYTHONPATH so 'toshy_common' module is found (prevent ModuleNotFoundError)
export PYTHONPATH="${HOME}/.config/toshy:${PYTHONPATH}"

exec "${VENV_PATH}/bin/python" "$HOME/.config/toshy/toshy_common/machine_context.py"
