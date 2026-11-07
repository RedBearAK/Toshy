#!/usr/bin/env bash


# Idempotent login autostart for the Toshy config process.
#
# Meant to be run from an XDG autostart entry at every login, on every
# kind of system. It does nothing when systemd is the init system (the
# systemd user services own startup there, whether enabled or not), and
# nothing when the keymapper is already running. Otherwise it hands off
# to 'toshy-config-start', which does the actual (re)start.
#
# Unlike 'toshy-config-start', this never stops or restarts anything.

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

# Same init system test as toshy_common/runtime_utils.py (is_init_systemd)
if [[ -r /proc/1/comm ]] && [[ "$(< /proc/1/comm)" == "systemd" ]]; then
    echo "Init system is systemd. Leaving startup to the Toshy systemd services."
    exit 0
fi

# Without pgrep we cannot tell whether the keymapper is running, so do not risk
# handing off to a command that would stop and restart a running keymapper.
if ! command -v pgrep >/dev/null 2>&1; then
    echo "The 'pgrep' command was not found. Cannot check for a running keymapper. Doing nothing."
    exit 1
fi

# Same process pattern that 'toshy-config-stop' uses to find the keymapper
if pgrep -u "$USER" -f "/bin/xwaykeyz" >/dev/null; then
    echo "Toshy keymapper process is already running. Nothing to do."
    exit 0
fi

echo "No Toshy keymapper process found. Starting Toshy config..."
exec "$HOME/.local/bin/toshy-config-start"
