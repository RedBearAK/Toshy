#!/usr/bin/env bash

# Echoes the versions of various Toshy components. 

# Resolve and activate the Toshy Python runtime (venv or external)
# shellcheck disable=SC1091
source "$HOME/.config/toshy/scripts/toshy-runtime-env.sh" || exit 1

"${TOSHY_PYTHON}" "${HOME}/.config/toshy/scripts/toshy_versions.py" "$@"
