#!/usr/bin/env bash

# Set up the Toshy systemd services (session monitor and config).
# Enhanced version with comprehensive error checking and debugging output.

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Error counter
ERROR_COUNT=0
WARNING_COUNT=0

# Function to print colored messages
print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    ((ERROR_COUNT++))
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    ((WARNING_COUNT++))
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to check command success
check_cmd() {
    local cmd_status=$?
    local cmd_desc="$1"
    
    if [ $cmd_status -ne 0 ]; then
        print_error "$cmd_desc failed with exit code: $cmd_status"
        return 1
    else
        print_success "$cmd_desc"
        return 0
    fi
}

# Check if the script is being run as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script must not be run as root"
    exit 1
fi

# Check if $USER and $HOME environment variables are not empty
if [[ -z $USER ]] || [[ -z $HOME ]]; then
    print_error "\$USER and/or \$HOME environment variables are not set. We need them."
    exit 1
fi

print_info "Running as user: $USER"
print_info "Home directory: $HOME"

# Get out of here if systemctl is not available
if command -v systemctl >/dev/null 2>&1; then
    print_success "systemctl command found"
else
    print_error "There is no 'systemctl' on this system. Nothing to do."
    exit 0
fi

# Check systemctl version for debugging
SYSTEMCTL_VERSION=$(systemctl --version | head -n1)
print_info "Systemd version: $SYSTEMCTL_VERSION"

# This script is pointless if the system doesn't support "user" systemd services (e.g., CentOS 7)
print_info "Checking if systemd user services are supported..."
if systemctl --user list-unit-files &>/dev/null; then
    print_success "Systemd user services are supported"
else
    print_error "Systemd user services are probably not supported here."
    print_info "This may be due to:"
    print_info "  - System using old systemd version without user service support"
    print_info "  - XDG_RUNTIME_DIR not set properly"
    print_info "  - D-Bus session not available"
    echo
    exit 1
fi

# Check XDG_RUNTIME_DIR
if [[ -n "$XDG_RUNTIME_DIR" ]]; then
    print_info "XDG_RUNTIME_DIR is set to: $XDG_RUNTIME_DIR"
    if [[ -d "$XDG_RUNTIME_DIR" ]]; then
        print_success "XDG_RUNTIME_DIR exists and is accessible"
    else
        print_warning "XDG_RUNTIME_DIR is set but directory doesn't exist!"
    fi
else
    print_warning "XDG_RUNTIME_DIR is not set (this may cause issues)"
fi

# Set up paths
LOCAL_BIN_PATH="$HOME/.local/bin"
USER_SYSD_PATH="$HOME/.config/systemd/user"
TOSHY_CFG_PATH="$HOME/.config/toshy"
SYSD_UNIT_PATH="$TOSHY_CFG_PATH/systemd-user-service-units"

DELAY=0.5

print_info "Configuration paths:"
print_info "  LOCAL_BIN_PATH: $LOCAL_BIN_PATH"
print_info "  USER_SYSD_PATH: $USER_SYSD_PATH"
print_info "  TOSHY_CFG_PATH: $TOSHY_CFG_PATH"
print_info "  SYSD_UNIT_PATH: $SYSD_UNIT_PATH"

export PATH="$LOCAL_BIN_PATH:$PATH"

echo
echo "================================================================================"
print_info "Setting up Toshy service unit files in '$USER_SYSD_PATH'..."
echo "================================================================================"
echo

# Create necessary directories
print_info "Creating necessary directories..."
mkdir -p "$USER_SYSD_PATH"
check_cmd "Creating systemd user directory"

mkdir -p "$HOME/.config/autostart"
check_cmd "Creating autostart directory"

# Check if source directory exists
if [[ ! -d "$SYSD_UNIT_PATH" ]]; then
    print_error "Source directory '$SYSD_UNIT_PATH' does not exist!"
    print_info "Toshy may not be properly installed."
    exit 1
fi
print_success "Source directory exists: $SYSD_UNIT_PATH"

# List source files for verification
print_info "Checking for source service files..."
SERVICE_FILES=(
    "toshy-cosmic-dbus.service"
    "toshy-kwin-dbus.service"
    "toshy-wlroots-dbus.service"
    "toshy-config.service"
    "toshy-session-monitor.service"
)

for service_file in "${SERVICE_FILES[@]}"; do
    if [[ -f "$SYSD_UNIT_PATH/$service_file" ]]; then
        print_success "  Found: $service_file"
    else
        print_error "  Missing: $service_file"
    fi
done

# Check for desktop entry file
DESKTOP_ENTRY_FILE="$TOSHY_CFG_PATH/desktop/Toshy_Import_Vars.desktop"
if [[ -f "$DESKTOP_ENTRY_FILE" ]]; then
    print_success "Desktop entry file exists: $DESKTOP_ENTRY_FILE"
else
    print_warning "Desktop entry file not found: $DESKTOP_ENTRY_FILE"
fi

echo
print_info "Removing any existing Toshy systemd services..."

# Stop, disable, and remove existing unit files
REMOVE_SCRIPT="$LOCAL_BIN_PATH/toshy-systemd-remove"
if [[ -f "$REMOVE_SCRIPT" ]]; then
    print_info "Running: $REMOVE_SCRIPT"
    "$REMOVE_SCRIPT"
    REMOVE_STATUS=$?
    if [ $REMOVE_STATUS -eq 0 ]; then
        print_success "Removal script completed successfully"
    else
        print_warning "Removal script exited with status: $REMOVE_STATUS"
    fi
else
    print_warning "Removal script not found at: $REMOVE_SCRIPT"
    print_info "Skipping service removal step"
fi

echo
print_info "Copying service files to systemd user directory..."

# Copy service files with error checking
for service_file in "${SERVICE_FILES[@]}"; do
    SRC="$SYSD_UNIT_PATH/$service_file"
    DST="$USER_SYSD_PATH/"
    
    if [[ -f "$SRC" ]]; then
        print_info "  Copying: $service_file"
        cp -f "$SRC" "$DST"
        if check_cmd "    cp $service_file"; then
            # Verify the file was actually copied
            if [[ -f "$DST/$service_file" ]]; then
                print_success "    Verified: file exists at destination"
            else
                print_error "    File copy reported success but file not found at destination!"
            fi
        fi
    else
        print_error "  Source file not found: $SRC"
    fi
done

# Copy desktop entry file
if [[ -f "$DESKTOP_ENTRY_FILE" ]]; then
    print_info "Copying desktop entry file..."
    cp -f "$DESKTOP_ENTRY_FILE" "$HOME/.config/autostart/"
    check_cmd "  cp Toshy_Import_Vars.desktop"
fi

sleep $DELAY

echo
print_info "Importing environment variables for systemd user services..."

# Give systemd user services access to environment variables
vars_to_import="KDE_SESSION_VERSION XDG_SESSION_TYPE XDG_SESSION_DESKTOP XDG_CURRENT_DESKTOP DESKTOP_SESSION DISPLAY WAYLAND_DISPLAY"

# Show current environment variable values
print_info "Current environment values:"
for var in $vars_to_import; do
    if [[ -n "${!var}" ]]; then
        print_info "  $var=${!var}"
    else
        print_warning "  $var is not set"
    fi
done

# Import environment variables (capture any errors this time)
print_info "Running: systemctl --user import-environment..."
# shellcheck disable=SC2086
IMPORT_OUTPUT=$(systemctl --user import-environment $vars_to_import 2>&1)
IMPORT_STATUS=$?

if [ $IMPORT_STATUS -eq 0 ]; then
    print_success "Environment variables imported successfully"
else
    print_warning "import-environment exited with status: $IMPORT_STATUS"
    if [[ -n "$IMPORT_OUTPUT" ]]; then
        print_info "Output: $IMPORT_OUTPUT"
    fi
fi

echo
print_info "Reloading systemd user daemon..."

systemctl --user daemon-reload 2>&1 | while IFS= read -r line; do
    if [[ -n "$line" ]]; then
        print_info "  $line"
    fi
done
check_cmd "systemctl --user daemon-reload"

sleep $DELAY

echo
print_info "Enabling and starting Toshy systemd services..."
echo

# Enable and start services with detailed error checking
for service_name in "${SERVICE_FILES[@]}"; do
    echo "--------------------------------------------------------------------------------"
    print_info "Processing: $service_name"
    
    # Check if service file exists
    if [[ ! -f "$USER_SYSD_PATH/$service_name" ]]; then
        print_error "  Service file not found: $USER_SYSD_PATH/$service_name"
        continue
    fi
    
    # Try to reenable the service
    print_info "  Running: systemctl --user reenable $service_name"
    REENABLE_OUTPUT=$(systemctl --user reenable "$service_name" 2>&1)
    REENABLE_STATUS=$?
    
    if [ $REENABLE_STATUS -eq 0 ]; then
        print_success "  Service re-enabled successfully"
    else
        print_error "  reenable failed with exit code: $REENABLE_STATUS"
        if [[ -n "$REENABLE_OUTPUT" ]]; then
            echo "$REENABLE_OUTPUT" | while IFS= read -r line; do
                print_info "    $line"
            done
        fi
    fi
    
    # Try to start the service
    print_info "  Running: systemctl --user start $service_name"
    START_OUTPUT=$(systemctl --user start "$service_name" 2>&1)
    START_STATUS=$?
    
    if [ $START_STATUS -eq 0 ]; then
        print_success "  Service started successfully"
    else
        print_error "  start failed with exit code: $START_STATUS"
        if [[ -n "$START_OUTPUT" ]]; then
            echo "$START_OUTPUT" | while IFS= read -r line; do
                print_info "    $line"
            done
        fi
    fi
    
    # Verify the service is actually enabled
    if systemctl --user is-enabled "$service_name" &>/dev/null; then
        print_success "  Verified: service is enabled"
    else
        print_error "  Verification failed: service is NOT enabled"
    fi
    
    # Check if service is active/running
    if systemctl --user is-active "$service_name" &>/dev/null; then
        print_success "  Verified: service is active/running"
    else
        print_warning "  Service is not active/running"
        # Get failure reason if available
        FAILED_OUTPUT=$(systemctl --user status "$service_name" 2>&1 | grep -A 3 "Active:")
        if [[ -n "$FAILED_OUTPUT" ]]; then
            echo "$FAILED_OUTPUT" | while IFS= read -r line; do
                print_info "    $line"
            done
        fi
    fi
    
    sleep "$DELAY"
done

export SYSTEMD_PAGER=""

echo
echo "================================================================================"
print_info "Displaying status of Toshy systemd services"
echo "================================================================================"
echo

for service_name in "${SERVICE_FILES[@]}"; do
    echo "--------------------------------------------------------------------------------"
    print_info "Status of: $service_name"
    echo "--------------------------------------------------------------------------------"
    systemctl --user status "$service_name" --no-pager -l
    echo
    sleep "$DELAY"
done

echo
echo "================================================================================"
print_info "Installation Summary"
echo "================================================================================"
echo

# Count enabled and running services
ENABLED_COUNT=0
RUNNING_COUNT=0

for service_name in "${SERVICE_FILES[@]}"; do
    if systemctl --user is-enabled "$service_name" &>/dev/null; then
        ((ENABLED_COUNT++))
    fi
    if systemctl --user is-active "$service_name" &>/dev/null; then
        ((RUNNING_COUNT++))
    fi
done

TOTAL_SERVICES=${#SERVICE_FILES[@]}

echo "Services enabled: $ENABLED_COUNT / $TOTAL_SERVICES"
echo "Services running: $RUNNING_COUNT / $TOTAL_SERVICES"
echo
echo "Errors encountered: $ERROR_COUNT"
echo "Warnings encountered: $WARNING_COUNT"
echo

if [ $ERROR_COUNT -eq 0 ] && [ $ENABLED_COUNT -eq $TOTAL_SERVICES ] && [ $RUNNING_COUNT -eq $TOTAL_SERVICES ]; then
    print_success "All Toshy systemd services installed successfully!"
    EXIT_CODE=0
elif [ $ENABLED_COUNT -eq $TOTAL_SERVICES ] && [ $RUNNING_COUNT -lt $TOTAL_SERVICES ]; then
    print_warning "Services are enabled but some are not running. Check status output above."
    EXIT_CODE=1
elif [ $ENABLED_COUNT -lt $TOTAL_SERVICES ]; then
    print_error "Some services failed to enable. Check error messages above."
    EXIT_CODE=1
else
    print_warning "Installation completed with issues. Review output above."
    EXIT_CODE=1
fi

echo
print_info "For more details, you can run:"
print_info "  toshy-services-status"
print_info "  journalctl --user -xeu <service-name>"
echo

exit $EXIT_CODE

# End of file #




# #!/usr/bin/env bash


# # Set up the Toshy systemd services (session monitor and config).

# # Check if the script is being run as root
# if [[ $EUID -eq 0 ]]; then
#     echo "This script must not be run as root"
#     exit 1
# fi

# # Check if $USER and $HOME environment variables are not empty
# if [[ -z $USER ]] || [[ -z $HOME ]]; then
#     echo "\$USER and/or \$HOME environment variables are not set. We need them."
#     exit 1
# fi

# # Get out of here if systemctl is not available
# if command -v systemctl >/dev/null 2>&1; then
#     # systemd is installed, proceed
#     :
# else
#     # no systemd found, exit (but with message for this script)
#     echo "There is no 'systemctl' on this system. Nothing to do."
#     exit 0
# fi


# # This script is pointless if the system doesn't support "user" systemd services (e.g., CentOS 7)
# if ! systemctl --user list-unit-files &>/dev/null; then
#     echo "ERROR: Systemd user services are probably not supported here."
#     echo
#     exit 1
# fi


# LOCAL_BIN_PATH="$HOME/.local/bin"
# USER_SYSD_PATH="$HOME/.config/systemd/user"
# TOSHY_CFG_PATH="$HOME/.config/toshy"
# SYSD_UNIT_PATH="$TOSHY_CFG_PATH/systemd-user-service-units"

# DELAY=0.5

# export PATH="$LOCAL_BIN_PATH:$PATH"

# echo -e "\nSetting up Toshy service unit files in '$USER_SYSD_PATH'..."

# mkdir -p "$USER_SYSD_PATH"
# mkdir -p "$HOME/.config/autostart"

# # Stop, disable, and remove existing unit files
# eval "$LOCAL_BIN_PATH/toshy-systemd-remove"

# cp -f "$SYSD_UNIT_PATH/toshy-cosmic-dbus.service"           "$USER_SYSD_PATH/"
# cp -f "$SYSD_UNIT_PATH/toshy-kwin-dbus.service"              "$USER_SYSD_PATH/"
# cp -f "$SYSD_UNIT_PATH/toshy-wlroots-dbus.service"          "$USER_SYSD_PATH/"
# cp -f "$SYSD_UNIT_PATH/toshy-config.service"                "$USER_SYSD_PATH/"
# cp -f "$SYSD_UNIT_PATH/toshy-session-monitor.service"       "$USER_SYSD_PATH/"

# cp -f "$TOSHY_CFG_PATH/desktop/Toshy_Import_Vars.desktop"   "$HOME/.config/autostart/"


# sleep $DELAY

# # Give systemd user services access to environment variables like:
# # XDG_SESSION_TYPE XDG_SESSION_DESKTOP XDG_CURRENT_DESKTOP
# # Do this BEFORE daemon-reload? Maybe not necessary. 
# # But silence errors (e.g., "XDG_SESSION_DESKTOP not set, ignoring")
# vars_to_import="KDE_SESSION_VERSION XDG_SESSION_TYPE XDG_SESSION_DESKTOP XDG_CURRENT_DESKTOP DESKTOP_SESSION DISPLAY WAYLAND_DISPLAY"
# # shellcheck disable=SC2086
# systemctl --user import-environment $vars_to_import >/dev/null 2>&1

# echo -e "\nIssuing systemctl daemon-reload..."

# systemctl --user daemon-reload

# sleep $DELAY

# echo -e "\nStarting Toshy systemd services..."

# service_names=(
#     "toshy-cosmic-dbus.service"
#     "toshy-kwin-dbus.service"
#     "toshy-wlroots-dbus.service"
#     "toshy-config.service"
#     "toshy-session-monitor.service"
# )

# for service_name in "${service_names[@]}"; do
#     systemctl --user reenable "$service_name"
#     systemctl --user start "$service_name"
#     sleep "$DELAY"
# done

# export SYSTEMD_PAGER=""

# echo -e "\nDisplaying status of Toshy systemd services...\n"

# systemctl --user status toshy-cosmic-dbus.service
# echo ""

# sleep $DELAY

# systemctl --user status toshy-kwin-dbus.service
# echo ""

# sleep $DELAY

# systemctl --user status toshy-wlroots-dbus.service
# echo ""

# sleep $DELAY

# systemctl --user status toshy-session-monitor.service
# echo ""

# sleep $DELAY

# systemctl --user status toshy-config.service

# sleep $DELAY

# echo -e "\nFinished installing Toshy systemd services.\n"

# # The keymapper's problem with ignoring the first modifier key press after startup
# # was fixed in 'xwaykeyz' 1.5.4, so we don't need to have these reminders anymore!
# # echo -e "\nHINT: In X11, tap a modifier key before trying shortcuts.\n"
