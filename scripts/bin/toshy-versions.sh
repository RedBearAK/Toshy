#!/usr/bin/env bash

# Echoes the versions of various Toshy components. 

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

"${VENV_PATH}/bin/python" "${HOME}/.config/toshy/scripts/toshy_versions.py" "$@"
