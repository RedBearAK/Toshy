#!/usr/bin/env bash


# Remove the Toshy bin command symlinks from user-local bin location.

# Check if the script is being run as root
if [[ ${EUID} -eq 0 ]]; then
    echo "This script must not be run as root"
    exit 1
fi

# Check if $USER and $HOME environment variables are not empty
if [[ -z ${USER} ]] || [[ -z ${HOME} ]]; then
    echo "\$USER and/or \$HOME environment variables are not set. We need them."
    exit 1
fi

LOCAL_BIN="${HOME}/.local/bin"


echo -e "\nRemoving Toshy terminal commands..."

rm -f "${LOCAL_BIN}/toshy-systemd-setup"
rm -f "${LOCAL_BIN}/toshy-systemd-remove"
rm -f "${LOCAL_BIN}/toshy-services-status"
rm -f "${LOCAL_BIN}/toshy-services-disable"
rm -f "${LOCAL_BIN}/toshy-services-enable"
rm -f "${LOCAL_BIN}/toshy-services-restart"
rm -f "${LOCAL_BIN}/toshy-services-start"
rm -f "${LOCAL_BIN}/toshy-services-stop"
rm -f "${LOCAL_BIN}/toshy-services-log"
rm -f "${LOCAL_BIN}/toshy-config-start"
rm -f "${LOCAL_BIN}/toshy-config-stop"
rm -f "${LOCAL_BIN}/toshy-config-restart"
rm -f "${LOCAL_BIN}/toshy-config-start-verbose"
rm -f "${LOCAL_BIN}/toshy-config-verbose-start"
rm -f "${LOCAL_BIN}/toshy-debug"
rm -f "${LOCAL_BIN}/toshy-tray"
rm -f "${LOCAL_BIN}/toshy-gui"
rm -f "${LOCAL_BIN}/toshy-env"
rm -f "${LOCAL_BIN}/toshy-venv"
rm -f "${LOCAL_BIN}/toshy-fnmode"
rm -f "${LOCAL_BIN}/toshy-devices"
rm -f "${LOCAL_BIN}/toshy-versions"
rm -f "${LOCAL_BIN}/toshy-reinstall"
rm -f "${LOCAL_BIN}/toshy-machine-id"
rm -f "${LOCAL_BIN}/toshy-kwin-dbus-service"
rm -f "${LOCAL_BIN}/toshy-cosmic-dbus-service"
rm -f "${LOCAL_BIN}/toshy-wlroots-dbus-service"


echo ""
echo "Finished removing Toshy terminal commands:"
echo ""
echo "- toshy-systemd-setup"
echo "- toshy-systemd-remove"
echo "- toshy-services-status"
echo "- toshy-services-disable"
echo "- toshy-services-enable"
echo "- toshy-services-start"
echo "- toshy-services-restart"
echo "- toshy-services-stop"
echo "- toshy-services-log"
echo "- toshy-config-start"
echo "- toshy-config-stop"
echo "- toshy-config-restart"
echo "- toshy-config-start-verbose"
echo "- toshy-config-verbose-start"
echo "- toshy-tray"
echo "- toshy-gui"
echo "- toshy-env"
echo "- toshy-venv"
echo "- toshy-fnmode"
echo "- toshy-devices"
echo "- toshy-versions"
echo "- toshy-reinstall"
echo "- toshy-machine-id"
echo "- toshy-kwin-dbus-service"
echo "- toshy-cosmic-dbus-service"
echo "- toshy-wlroots-dbus-service"
echo ""
echo "The commands will still be available until you close the current terminal, or "
echo "run 'hash -r', or source your shell RC file to refresh executable hash table."
echo ""
