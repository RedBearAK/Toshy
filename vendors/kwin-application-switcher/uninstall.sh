#!/usr/bin/env bash


# This is a script to remove an installed KWin script matching a script found in the current folder

exit_w_error() {
    local msg="$1"
    echo -e "\nERROR: ${msg} \nExiting...\n"
    exit 1
}

unload_kwin_script() {
    echo "Attempting to unload KWin script '${script_name}' prior to removal."

    local output=""
    local success=0
    local not_loaded=0

    if command -v gdbus &> /dev/null; then
        output=$(gdbus call --session --dest org.kde.KWin --object-path /Scripting \
                            --method org.kde.kwin.Scripting.unloadScript "${script_name}")
        [[ "$output" == "(true,)" ]] && success=1
        [[ "$output" == "(false,)" ]] && not_loaded=1
    elif command -v qdbus &> /dev/null; then
        output=$(qdbus org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "${script_name}")
        [[ "$output" == "true" ]] && success=1
        [[ "$output" == "false" ]] && not_loaded=1
    elif command -v dbus-send &> /dev/null; then
        output=$(dbus-send --session --print-reply --type=method_call --dest=org.kde.KWin \
                            /Scripting org.kde.kwin.Scripting.unloadScript string:"${script_name}")
        echo "$output" | grep -q "boolean true" && success=1
        echo "$output" | grep -q "boolean false" && not_loaded=1
    else
        echo "No available D-Bus utility to unload the KWin script."
        echo "You may need to log out to remove the KWin script from memory."
        success=0  # Indicates failure to unload due to lack of tools
    fi

    if [[ $success -eq 1 ]]; then
        echo "Successfully unloaded the KWin script."
    elif [[ $not_loaded -eq 1 ]]; then
        echo "The KWin script was already unloaded or does not exist."
    else
        echo "ERROR: Failed to unload the KWin script. Here is the output:"
        echo ""
        echo "$output"
        echo ""
        echo "Uninstalling the script now may leave it active in memory until you log out."
        read -r -p "Continue with uninstalling the script files anyway? [y/N]: " response
        case $response in
            [Yy]* )
                echo "Proceeding with removal. The KWin script might still be active in memory."
                ;;
            * )
                echo "Try to unload the script manually from GUI KWin Scripts settings panel."
                exit_w_error "Run this script again to uninstall, or click trash icon in GUI and Apply."
                ;;
        esac
    fi
}

remove_w_kpackagetool6() {
    if ! command -v kpackagetool6 &> /dev/null; then
        exit_w_error "The 'kpackagetool6' command is missing. Cannot remove KWin script."
    else
        echo "Removing '${script_name}' KWin script."
        kpackagetool6 --type=${script_type} --remove "${script_name}"
    fi
}

remove_w_kpackagetool5() {
    if ! command -v kpackagetool5 &> /dev/null; then
        exit_w_error "The 'kpackagetool5' command is missing. Cannot remove KWin script."
    else
        echo "Removing '${script_name}' KWin script."
        kpackagetool5 --type=${script_type} --remove "${script_name}"
    fi
}

KDE_ver=${KDE_SESSION_VERSION:-0}   # Default to zero value if environment variable not set
script_type="KWin/Script"
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

if [[ $KDE_ver -eq 0 ]]; then
    echo "KDE_SESSION_VERSION environment variable was not set."
    exit_w_error "Cannot remove '${script_name}' KWin script."
elif [[ $KDE_ver -eq 6 ]]; then
    unload_kwin_script
    if ! remove_w_kpackagetool6; then
        exit_w_error "Problem while removing '${script_name}' KWin script."
    fi
    echo "KWin script '${script_name}' was removed."
elif [[ ${KDE_ver} -eq 5 ]]; then
    unload_kwin_script
    if ! remove_w_kpackagetool5; then
        exit_w_error "Problem while removing '${script_name}' KWin script."
    fi
    echo "KWin script '${script_name}' was removed."
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


echo "Finished removing KWin script: '${script_name}'"
