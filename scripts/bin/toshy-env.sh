#!/usr/bin/env bash


# Run the Toshy environment module to show what it sees

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

# Need PYTHONPATH update to allow absolute imports from "toshy_common" package
export PYTHONPATH="${HOME}/.config/toshy:${PYTHONPATH}"

exec "${TOSHY_PYTHON}" "${HOME}/.config/toshy/toshy_common/env_context.py"
