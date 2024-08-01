#!/usr/bin/env bash


# Start the Toshy manual script

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

"$HOME/.local/bin/toshy-services-stop"

pkill -f "bin/xwaykeyz"
pkill -f "bin/keyszer"
# systemctl stop xkeysnail.service
pkill -f "bin/xkeysnail"

############################  COMPANION D-BUS SERVICES  #####################################

# start KDE D-Bus service in case we are in Wayland+KDE (it will stop itself if not)
nohup "${HOME}/.local/bin/toshy-kde-dbus-service" >/dev/null 2>&1 &

# start COSMIC D-Bus service in case we are in Wayland+COSMIC (it will stop itself if not)
nohup "${HOME}/.local/bin/toshy-cosmic-dbus-service" >/dev/null 2>&1 &

# start Wlroots D-Bus service in case we are in a wlroots-based DE/WM (it will stop itself if not)
nohup "${HOME}/.local/bin/toshy-wlroots-dbus-service" >/dev/null 2>&1 &


# pause to let D-Bus service(s) start up
sleep 2

# shellcheck disable=SC1091
source "$HOME/.config/toshy/.venv/bin/activate"

# overcome a possible strange and rare problem connecting to X display
if command xhost &> /dev/null; then
    if [[ "$XDG_SESSION_TYPE" == "x11" ]]; then
        xhost +local:
    fi
fi

if command -v xwaykeyz >/dev/null 2>&1; then
    xwaykeyz -w -c "$HOME/.config/toshy/toshy_config.py"
elif command -v keyszer >/dev/null 2>&1; then
    keyszer -w -c "$HOME/.config/toshy/toshy_config.py"
else
    echo -e "Neither \"xwaykeyz\" nor \"keyszer\" command was found in: \n$PATH."
    echo "Toshy config cannot be loaded until one of these is installed."
    exit 1
fi
