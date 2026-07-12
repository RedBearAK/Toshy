#!/usr/bin/env bash


# This script will install a KWin script structure found in the path designated in '$script_path'

exit_w_error() {
    local msg="$1"
    echo -e "\nERROR: ${msg} \nExiting...\n"
    exit 1
}

install_w_kpackagetool6() {
    if ! command -v kpackagetool6 &> /dev/null; then
        exit_w_error "The 'kpackagetool6' command was not found. Cannot install KWin script."
    fi
    echo "Installing KWin script: '${script_name}'"
    if ! kpackagetool6 --type="${script_type}" --install "${script_path}" &> /dev/null; then
        kpackagetool6 --type="${script_type}" --upgrade "${script_path}"
    fi
}

install_w_kpackagetool5() {
    if ! command -v kpackagetool5 &> /dev/null; then
        exit_w_error "The 'kpackagetool5' command was not found. Cannot install KWin script."
    fi
    echo "Installing KWin script: '${script_name}'"
    if ! kpackagetool5 --type="${script_type}" --install "${script_path}" &> /dev/null; then
        kpackagetool5 --type="${script_type}" --upgrade "${script_path}"
    fi
}

KDE_ver=${KDE_SESSION_VERSION:-0}   # Default to zero value if environment variable not set
script_type="KWin/Script"
script_path="."
script_name=""


if [ -f "./metadata.json" ]; then
    # The "P" option for grep causes a problem on Chimera Linux, which uses BSD utils
    # script_name=$(grep -oP '"Id":\s*"[^"]*' ./metadata.json | grep -oP '[^"]*$')
    script_name=$(grep '"Id":' ./metadata.json | sed 's/.*"Id":[[:space:]]*"\([^"]*\).*/\1/')
elif [ -f "./metadata.desktop" ]; then
    script_name=$(grep '^X-KDE-PluginInfo-Name=' ./metadata.desktop | cut -d '=' -f2)
    echo "FYI: 'metadata.desktop' files are deprecated. Use 'metadata.json' format."
else
    exit_w_error "No suitable metadata file found. Unable to get script name."
fi

if [ "$script_name" == "" ]; then
    exit_w_error "Failed to parse KWin script name from metadata file."
fi

if [[ ${KDE_ver} -eq 0 ]]; then
    echo "KDE_SESSION_VERSION environment variable was not set."
    exit_w_error "Cannot install '${script_name}' KWin script."
elif [[ ${KDE_ver} -eq 6 ]]; then
    if ! install_w_kpackagetool6; then
        exit_w_error "Problem installing '${script_name}' with kpackagetool6."
    fi
    if ! command -v kwriteconfig6 &> /dev/null; then
        exit_w_error "The 'kwriteconfig6' command was not found. Cannot enable KWin script."
    fi
    kwriteconfig6 --file kwinrc --group Plugins --key "$script_name"Enabled true
elif [[ ${KDE_ver} -eq 5 ]]; then
    if ! install_w_kpackagetool5; then
        exit_w_error "Problem installing '${script_name}' with kpackagetool5."
    fi
    if ! command -v kwriteconfig5 &> /dev/null; then
        exit_w_error "The 'kwriteconfig5' command was not found. Cannot enable KWin script."
    fi
    kwriteconfig5 --file kwinrc --group Plugins --key "$script_name"Enabled true
else
    echo "KDE_SESSION_VERSION had a value, but that value was unrecognized: '${KDE_ver}'"
    exit_w_error "This script is meant to run only on KDE 5 or 6."
fi


sleep 0.5

# We need to gracefully cascade through common D-Bus utils to 
# find one that is available to use for the KWin reconfigure 
# command. Sometimes 'qdbus' is not available. Start with 'gdbus'.

# Extended array of D-Bus command names with prioritized qdbus variants
dbus_commands=("gdbus" "qdbus6" "qdbus-qt6" "qdbus-qt5" "qdbus" "dbus-send")

# Functions to handle reconfiguration with different dbus utilities
reconfigure() {
    case "$1" in
        gdbus)
            gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure
            ;;
        qdbus6 | qdbus-qt6 | qdbus-qt5 | qdbus)
            "$1" org.kde.KWin /KWin reconfigure
            ;;
        dbus-send)
            dbus-send --session --type=method_call --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure
            ;;
        *)
            echo "Unsupported DBus utility: $1" >&2
            return 1
            ;;
    esac
}

# Unquoted 'true' and 'false' values are built-in commands in bash, 
# returning 0 or 1 exit status.
# So they can sort of be treated like Python's 'True' or 'False' in 'if' conditions.
dbus_cmd_found=false

# Iterate through the dbus_commands array
for cmd in "${dbus_commands[@]}"; do
    if command -v "${cmd}" &> /dev/null; then
        dbus_cmd_found=true
        echo "Refreshing KWin configuration using $cmd."
        reconfigure "${cmd}" &> /dev/null
        sleep 0.5
        # Break out of the loop once a command is found and executed
        break
    fi
done

if ! $dbus_cmd_found; then
    echo "No suitable DBus utility found. KWin configuration may need manual reloading."
fi


echo "Finished installing KWin script: '${script_name}'"
