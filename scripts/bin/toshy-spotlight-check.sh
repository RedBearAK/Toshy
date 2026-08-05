#!/usr/bin/env bash


# Show detected launcher and input-switching shortcuts and the keymaps
# Toshy would build from them, after activating the Toshy Python runtime.

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

# Launch the spotlight_input package diagnostic as a Python "module".
# TOSHY_LAUNCHER_NAME tells the module's argparse help to display the
# command name as invoked (the ~/.local/bin symlink name), so a renamed
# command automatically shows its new name.
export PYTHONPATH="${HOME}/.config/toshy:${PYTHONPATH}"
export TOSHY_LAUNCHER_NAME="${0##*/}"
exec "${TOSHY_PYTHON}" -m toshy_common.spotlight_input "$@"

# End of file #
