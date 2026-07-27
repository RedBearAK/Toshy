#!/usr/bin/env bash
#
# This script uses a custom bash alias in the shebang to show something
# other than a generic "bash" program name in process list apps like `btop`. 
# The alias(es) just point to /usr/bin/bash.
#
# Show the journalctl output of the Toshy systemd services (session monitor and config).

# Check if the script is being run as root
if [[ $EUID -eq 0 ]]; then
    echo "This script must not be run as root"
    exit 1
fi

# Check if systemd is actually the init system
if [[ $(ps -p 1 -o comm=) == "systemd" ]]; then
    # systemd is the init system, proceed
    :
else
    # systemd is NOT the init system, exit with message
    echo "Init system is not 'systemd'..."
    exit 0
fi

# Get out of here if systemctl is not available
if command -v systemctl >/dev/null 2>&1; then
    # systemctl is installed, proceed
    :
else
    # no systemctl found, exit silently
    exit 0
fi

clean_exit() {
    echo "Caught Interrupt signal. Exiting..."
    # Add your clean-up commands here

    # Exit the script
    exit 0
}

# Trap the interrupt signal
trap 'clean_exit' SIGINT

echo "Showing systemd journal messages for Toshy services (since last boot):"

# REMOVING IN FAVOR OF SWITCHING TO USING 'EXEC' TO LAUNCH THE FINAL COMMAND
# # Set the process name for the Toshy services log process.
# # We can do this here because this is just a direct launcher script.
# # This trick seems to confuse systemd as it tries to track "child" processes. 
# echo "toshy-svcs-log" > /proc/$$/comm

# First get all the Toshy service names into an array
if systemctl --user list-unit-files &>/dev/null; then
    mapfile -t toshy_services < <(
        systemctl --user list-unit-files |
        grep -i toshy |
        grep -v generated |
        awk '{print $1}'
    )
else
    # Handle systems without user service support (e.g., CentOS 7)
    echo "ERROR: Systemd user services are probably not supported here."
    echo
    exit 1
fi

# Check if any services were found
if [ ${#toshy_services[@]} -eq 0 ]; then
    echo "No Toshy services found. Exiting."
    exit 0
fi

# Check if stdbuf is available and set the appropriate command
if command -v stdbuf >/dev/null 2>&1; then
    STDBUF_CMD="stdbuf -oL"
else
    STDBUF_CMD=""
fi

# Start building the command with the basic parameters
cmd_base="${STDBUF_CMD} journalctl -n200 -b -f"

# Add each service to the base command
cmd_units=""
for service in "${toshy_services[@]}"; do
    cmd_units+=" --user-unit $service"
done

# Combine and execute the command (switched from 'eval' to 'exec' for memory efficiency)
full_cmd="${cmd_base}${cmd_units}"

# DEPRECATED
# # eval "$full_cmd"
# # Can't use quotes on the full command with 'exec' because it will treat as single "command"
# # exec $full_cmd

# Put a 'trap' right in the command being execed.
# Prevents a process crash when launched inside new terminal window with 
# "-e" or "--" (from tray or GUI app) and we use Ctrl+C (SIGINT) to quit
exec bash -c "trap 'exit 0' SIGINT SIGTERM; $full_cmd"
