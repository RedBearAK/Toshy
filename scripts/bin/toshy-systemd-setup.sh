#!/usr/bin/env bash


# Set up the Toshy systemd services (session monitor and config).

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

# Get out of here if systemctl is not available
if command -v systemctl >/dev/null 2>&1; then
    # systemd is installed, proceed
    :
else
    # no systemd found, exit (but with message for this script)
    echo "There is no 'systemctl' on this system. Nothing to do."
    exit 0
fi


# This script is pointless if the system doesn't support "user" systemd services (e.g., CentOS 7)
if ! systemctl --user list-unit-files &>/dev/null; then
    echo "ERROR: Systemd user services are probably not supported here."
    echo
    exit 1
fi


LOCAL_BIN_PATH="$HOME/.local/bin"
USER_SYSD_PATH="$HOME/.config/systemd/user"
TOSHY_CFG_PATH="$HOME/.config/toshy"
SYSD_UNIT_PATH="$TOSHY_CFG_PATH/systemd-user-service-units"

DELAY=0.5

export PATH="$LOCAL_BIN_PATH:$PATH"

echo -e "\nSetting up Toshy service unit files in '$USER_SYSD_PATH'..."

mkdir -p "$USER_SYSD_PATH"
mkdir -p "$HOME/.config/autostart"

# Stop, disable, and remove existing unit files
eval "$LOCAL_BIN_PATH/toshy-systemd-remove"

cp -f "$SYSD_UNIT_PATH/toshy-cosmic-dbus.service"           "$USER_SYSD_PATH/"
cp -f "$SYSD_UNIT_PATH/toshy-kwin-dbus.service"              "$USER_SYSD_PATH/"
cp -f "$SYSD_UNIT_PATH/toshy-wlroots-dbus.service"          "$USER_SYSD_PATH/"
cp -f "$SYSD_UNIT_PATH/toshy-config.service"                "$USER_SYSD_PATH/"
cp -f "$SYSD_UNIT_PATH/toshy-session-monitor.service"       "$USER_SYSD_PATH/"

cp -f "$TOSHY_CFG_PATH/desktop/Toshy_Import_Vars.desktop"   "$HOME/.config/autostart/"


sleep $DELAY

# Give systemd user services access to environment variables like:
# XDG_SESSION_TYPE XDG_SESSION_DESKTOP XDG_CURRENT_DESKTOP
# Do this BEFORE daemon-reload? Maybe not necessary. 
# But silence errors (e.g., "XDG_SESSION_DESKTOP not set, ignoring")
vars_to_import="KDE_SESSION_VERSION XDG_SESSION_TYPE XDG_SESSION_DESKTOP XDG_CURRENT_DESKTOP DESKTOP_SESSION DISPLAY WAYLAND_DISPLAY"
# shellcheck disable=SC2086
systemctl --user import-environment $vars_to_import >/dev/null 2>&1

echo -e "\nIssuing systemctl daemon-reload..."

systemctl --user daemon-reload

sleep $DELAY

echo -e "\nStarting Toshy systemd services..."

service_names=(
    "toshy-cosmic-dbus.service"
    "toshy-kwin-dbus.service"
    "toshy-wlroots-dbus.service"
    "toshy-config.service"
    "toshy-session-monitor.service"
)

for service_name in "${service_names[@]}"; do
    systemctl --user reenable "$service_name"
    systemctl --user start "$service_name"
    sleep "$DELAY"
done

export SYSTEMD_PAGER=""

echo -e "\nDisplaying status of Toshy systemd services...\n"

systemctl --user status toshy-cosmic-dbus.service
echo ""

sleep $DELAY

systemctl --user status toshy-kwin-dbus.service
echo ""

sleep $DELAY

systemctl --user status toshy-wlroots-dbus.service
echo ""

sleep $DELAY

systemctl --user status toshy-session-monitor.service
echo ""

sleep $DELAY

systemctl --user status toshy-config.service

sleep $DELAY

echo -e "\nFinished installing Toshy systemd services.\n"

# The keymapper's problem with ignoring the first modifier key press after startup
# was fixed in 'xwaykeyz' 1.5.4, so we don't need to have these reminders anymore!
# echo -e "\nHINT: In X11, tap a modifier key before trying shortcuts.\n"
