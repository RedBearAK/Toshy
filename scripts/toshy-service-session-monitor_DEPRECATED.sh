#!/usr/bin/bash

# Monitor whether the user's desktop session is "Active" according to loginctl.

# Should handle the case of user remaining "logged in" but using "switch user"
# to let another user log in to their own desktop and use the screen. 
# We don't want the keymapper to interfere with the other user's input or 
# with their separate usage of this or any other keymapper. 

if ! command -v loginctl >/dev/null 2>&1; then
    echo "The \"loginctl\" command is not available. Toshy session monitor will not work here."
    exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
    echo "The \"systemctl\" command is not available. Toshy session monitor will not work here."
    exit 1
fi

# If XDG_RUNTIME_DIR is not set or is empty
if [[ -z "${XDG_RUNTIME_DIR}" ]]; then
    echo "SESSMON_SVC: XDG_RUNTIME_DIR not set. Unable to determine where to store the marker file."
else
    MARKER_FILE="${XDG_RUNTIME_DIR}/toshy-service-sessmon.start"
    if [[ ! -f "${MARKER_FILE}" ]]; then
        sleep 3
        touch "${MARKER_FILE}"
    fi
fi

USER="$(whoami)"
STOPPED_BY_ME="false"

# Function to stop Toshy services
stop_toshy_services() {
    local reason="$1"
    echo "SESSMON_SVC: Stopping config service because $reason"
    systemctl --user stop toshy-config.service >/dev/null 2>&1
    sleep 0.5
    systemctl --user stop toshy-kwin-dbus.service >/dev/null 2>&1
    systemctl --user stop toshy-cosmic-dbus.service >/dev/null 2>&1
    systemctl --user stop toshy-wlroots-dbus.service >/dev/null 2>&1
    STOPPED_BY_ME="true"
}

# Function to start Toshy services
start_toshy_services() {
    if [[ "$STOPPED_BY_ME" == "true" ]]; then
        systemctl --user restart toshy-kwin-dbus.service >/dev/null 2>&1
        systemctl --user restart toshy-cosmic-dbus.service >/dev/null 2>&1
        systemctl --user restart toshy-wlroots-dbus.service >/dev/null 2>&1
        sleep 0.5
        systemctl --user restart toshy-config.service >/dev/null 2>&1
        STOPPED_BY_ME="false"
    fi
}

# give the session info and config service a bit of time to stabilize
sleep 2

# check that loginctl is actually going to work right now
retry=0
while true; do
    # suppress all output of command, then check exit status
    loginctl session-status >/dev/null 2>&1
    status=$?
    if [[ $status -eq 0 ]]; then
        # The command succeeded, so break out of the loop
        break
    else
        # The command failed, so wait for a bit and then try again
        sleep 2
        ((retry++))
        if [[ $retry -gt 10 ]]; then
            echo "SESSMON_SVC: Attempt to use loginctl failed after 10 attempts. Exiting."
            exit 1
        fi
    fi
done

while true; do
    sleep 2

    # Get session count and handle complete logout
    SESSION_COUNT=$(loginctl list-sessions -p UserName 2>/dev/null | grep -c "${USER}" || echo "0")

    if [[ "$SESSION_COUNT" == "0" ]]; then          # Use string comparison to prevent syntax error
        systemctl --user stop toshy-config.service
        systemctl --user stop toshy-kwin-dbus.service
        systemctl --user stop toshy-cosmic-dbus.service
        systemctl --user stop toshy-wlroots-dbus.service
        # User is logged out entirely if there are no sessions, 
        # so in this case stop the session monitor too:
        systemctl --user stop toshy-session-monitor.service
        continue
    fi

    # get the current session ID (number)
    SESSION_ID="$(loginctl session-status 2>/dev/null | head -n1 | cut -d' ' -f1)"

    # Check service status
    CFG_SERVICE_STATUS=$(systemctl --user is-active toshy-config.service)

    if [[ -n "$SESSION_ID" ]]; then
        # check the loginctl show-session metadata to see if it's "Active" (yes/no)
        SESSION_IS_ACTIVE="$(loginctl show-session "$SESSION_ID" -p Active --value 2>/dev/null || echo "no")"
        
        if [[ "$SESSION_IS_ACTIVE" == "yes" ]]; then
            # Session is active, start services if they were stopped by us
            if [[ "$CFG_SERVICE_STATUS" == "inactive" ]]; then
                start_toshy_services
            fi
        else
            # Session exists but is not active
            if [[ "$CFG_SERVICE_STATUS" == "active" ]]; then
                stop_toshy_services "session is inactive"
            fi
        fi
    else
        # No valid session ID (likely at login screen)
        if [[ "$CFG_SERVICE_STATUS" == "active" ]]; then
            stop_toshy_services "no valid session found (login screen?)"
        fi
    fi
done
