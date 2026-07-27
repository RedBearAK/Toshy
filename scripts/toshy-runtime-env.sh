#!/usr/bin/env bash
# Repo location: toshy/scripts/toshy-runtime-env.sh

# Sourced-only helper that resolves the location of the Toshy Python
# runtime and prepares the calling script's environment to use it.
#
# Resolution order:
#   1. TOSHY_RUNTIME_DIR environment variable (per-invocation override)
#   2. Runtime link:  ${XDG_STATE_HOME:-~/.local/state}/toshy/runtime
#      (symlink or directory; maintained by external packaging, e.g. a
#      Nix home-manager module pointing at a Python env store path)
#   3. Default venv:  ~/.config/toshy/.venv
#
# If the env var is set or the runtime link exists, it MUST be valid
# (contain bin/python). A broken override is a loud error, never a
# silent fallback to the venv.
#
# Usage in launcher scripts (root/HOME guards remain the caller's job):
#
#   source "$HOME/.config/toshy/scripts/toshy-runtime-env.sh" || exit 1
#
# On success this file will have:
#   - Put the runtime's bin dir on PATH (via venv activate if present,
#     otherwise by direct PATH prepend for external runtimes)
#   - Exported TOSHY_PYTHON as the absolute path to the interpreter
#   - Exported TOSHY_RUNTIME_DIR as the resolved runtime location

# Deliberately not named SCRIPT_VERSION: this file is sourced, and
# assigning SCRIPT_VERSION here would clobber the caller's variable.
# shellcheck disable=SC2034
TOSHY_RUNTIME_ENV_VERSION='20260727'


# Guard: this file must be sourced, not executed.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "toshy-runtime-env.sh is meant to be sourced by other scripts, not executed." >&2
    exit 1
fi

_toshy_state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/toshy"
_toshy_runtime_link="${_toshy_state_dir}/runtime"
_toshy_venv_dir="$HOME/.config/toshy/.venv"

if [[ -n "${TOSHY_RUNTIME_DIR:-}" ]]; then
    _toshy_runtime_dir="${TOSHY_RUNTIME_DIR}"
    _toshy_runtime_src="TOSHY_RUNTIME_DIR environment variable"
elif [[ -L "${_toshy_runtime_link}" || -e "${_toshy_runtime_link}" ]]; then
    # Existence of the link (even dangling) means an external runtime
    # was deliberately configured. It must validate below.
    _toshy_runtime_dir="${_toshy_runtime_link}"
    _toshy_runtime_src="runtime link: ${_toshy_runtime_link}"
else
    _toshy_runtime_dir="${_toshy_venv_dir}"
    _toshy_runtime_src="default venv location"
fi

if [[ ! -x "${_toshy_runtime_dir}/bin/python" ]]; then
    echo "Toshy runtime error: no usable Python runtime found."                     >&2
    echo "  Selected via: ${_toshy_runtime_src}"                                    >&2
    echo "  Expected interpreter at: ${_toshy_runtime_dir}/bin/python"              >&2
    if [[ "${_toshy_runtime_dir}" == "${_toshy_venv_dir}" ]]; then
        echo "  The Toshy venv appears to be missing or damaged."                   >&2
        echo "  Re-run the Toshy installer to recreate it."                         >&2
    else
        echo "  The runtime override exists but is broken (dangling symlink,"       >&2
        echo "  stale path, or not a Python environment)."                          >&2
        echo "  Fix or remove the override to fall back to the default venv at:"    >&2
        echo "  ${_toshy_venv_dir}"                                                 >&2
    fi
    return 1
fi

if [[ -f "${_toshy_runtime_dir}/bin/activate" ]]; then
    # Venv-style runtime: activate handles PATH and VIRTUAL_ENV.
    # shellcheck disable=SC1091
    source "${_toshy_runtime_dir}/bin/activate"
else
    # External runtime (e.g. Nix store env): no activate script exists.
    # Putting its bin dir first on PATH is the whole job.
    export PATH="${_toshy_runtime_dir}/bin:${PATH}"
fi

export TOSHY_PYTHON="${_toshy_runtime_dir}/bin/python"

# [?] Exporting the resolved dir means child processes inherit it and
# will short-circuit to the env var branch on re-resolution. Consistent,
# but drop this export if that inheritance seems too magical.
export TOSHY_RUNTIME_DIR="${_toshy_runtime_dir}"

unset _toshy_state_dir _toshy_runtime_link _toshy_venv_dir
unset _toshy_runtime_dir _toshy_runtime_src

# End of file #
