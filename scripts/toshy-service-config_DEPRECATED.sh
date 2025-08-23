#!/usr/bin/bash


# Start the actual run of the keymapper with Toshy config, making 
# sure to stop existing processes.

# Make sure keymapper binary can be found in user-home-local "bin" location
export PATH=$HOME/.local/bin:$PATH


# If XDG_RUNTIME_DIR is not set or is empty
if [ -z "${XDG_RUNTIME_DIR}" ]; then
    echo "Toshy Config Svc: XDG_RUNTIME_DIR not set. Unable to determine where to store the marker file."
    # exit 1
else
    # Full path to the marker file
    MARKER_FILE="${XDG_RUNTIME_DIR}/toshy-service-config.start"
    # Check if a marker file exists
    if [ ! -f "${MARKER_FILE}" ]; then
        # If it does not exist, wait for a certain time period
        sleep 3
        # Create the marker file to signify that the service has started once
        touch "${MARKER_FILE}"
    fi
fi


# Activate the Python virtual environment
# shellcheck disable=SC1091
source "$HOME/.config/toshy/.venv/bin/activate"


# Check if the desktop session is X11
if [[ "$XDG_SESSION_TYPE" == "x11" ]]; then
    # Check if xset is installed
    if command -v xset &> /dev/null; then
        # Loop until the X server is ready using xset
        while true; do
            if xset -q &>/dev/null; then
                break
            else
                echo "Toshy Config Service: X server not ready?" >&2
                # Sleep for a short period before trying again
                sleep 2
            fi
        done
    else
        DELAY="5"
        echo "Toshy Config Service: xset not found, sleeping for $DELAY seconds." >&2
        # Fallback to a short sleep delay
        sleep $DELAY
    fi
elif [[ -z "$XDG_SESSION_TYPE" ]]; then
    sleep 2
    echo "Toshy Config Service: XDG_SESSION_TYPE not set. Restarting service." >&2
    exit 1
fi


if command -v xwaykeyz >/dev/null 2>&1 || command -v keyszer >/dev/null 2>&1; then
    : # no-op operator
else
    echo -e "Neither \"xwaykeyz\" nor \"keyszer\" command was not found in: \n$PATH."
    echo "Toshy config cannot be loaded until \"xwaykeyz\" or \"keyszer\" is installed."
    exit 1
fi


# shut down any existing xwaykeyz, keyszer or xkeysnail process
pkill -f "bin/xwaykeyz"
pkill -f "bin/keyszer"
pkill -f "bin/xkeysnail"

# overcome a possible strange and rare problem connecting to X display
if command xhost &> /dev/null; then
    if [[ "$XDG_SESSION_TYPE" == "x11" ]]; then
        xhost +local:
    fi
fi

# Set the process name for the keymapper config process (causes errors, see note)
# echo "toshy-config" > /proc/$$/comm
# REMOVING: This seems to confuse systemd and cause error messages in the journal

if command -v xwaykeyz >/dev/null 2>&1; then
    xwaykeyz -w -c "$HOME/.config/toshy/toshy_config.py"
else
    echo -e "The \"xwaykeyz\" command was not found in: \n$PATH."
    echo "Toshy config cannot be loaded until \"xwaykeyz\" is available."
    exit 1
fi
