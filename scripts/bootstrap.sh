#!/bin/bash

# scripts/bootstrap.sh
# Toshy Installation Bootstrap Script
# https://github.com/RedBearAK/toshy

set -e  # Exit on error

# Force unbuffered output
exec > >(cat) 2>&1

# Store the original directory
ORIGINAL_DIR="$(pwd)"

# Default branch
DEFAULT_BRANCH="main"
SUGGESTED_BRANCH="dev_beta"

# Function to ensure echoes are visible
echo_unbuffered() {
    echo "$@" >&2
}

# Helper for interactive reads (handles piped input)
read_interactive() {
    if [ -t 0 ]; then
        read -r "$@"
    else
        read -r "$@" </dev/tty
    fi
}

show_install_options() {
    echo_unbuffered
    echo_unbuffered "Available install options:"
    echo_unbuffered "  --override-distro=DISTRO  Override auto-detection of distro"
    echo_unbuffered "  --barebones-config        Install with mostly empty/blank keymapper config file"
    echo_unbuffered "  --skip-native             Skip the install of native packages"
    echo_unbuffered "  --no-dbus-python          Avoid installing dbus-python pip package"
    echo_unbuffered "  --dev-keymapper[=BRANCH]  Install the development branch of the keymapper"
    echo_unbuffered "  --fancy-pants             See README for more info on this option"
    echo_unbuffered
}

# Get install options from user with immediate confirmation
get_install_options() {
    show_install_options
    echo_unbuffered "Most users don't need any options."
    echo_unbuffered
    sleep 0.1
    
    read_interactive -p "Options (or Enter for none): " USER_OPTIONS
    
    if [ -n "$USER_OPTIONS" ]; then
        INSTALL_ARGS="install $USER_OPTIONS"
    else
        INSTALL_ARGS="install"
    fi
    
    # Immediate confirmation/edit loop
    echo_unbuffered
    echo_unbuffered "Install command:  ./setup_toshy.py $INSTALL_ARGS"
    echo_unbuffered
    echo_unbuffered "  Y - Continue (default)"
    echo_unbuffered "  e - Edit options"
    echo_unbuffered "  q - Quit"
    echo_unbuffered
    
    while true; do
        read_interactive -p "Continue? [Y/e/q]: " confirm
        
        # Convert to lowercase
        confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]')
        
        # Default to yes if empty
        if [ -z "$confirm" ] || [ "$confirm" = "y" ]; then
            break
        elif [ "$confirm" = "e" ]; then
            show_install_options
            
            read_interactive -p "Options (or Enter for none): " USER_OPTIONS
            
            if [ -n "$USER_OPTIONS" ]; then
                INSTALL_ARGS="install $USER_OPTIONS"
            else
                INSTALL_ARGS="install"
            fi
            
            echo_unbuffered
            echo_unbuffered "Install command:  ./setup_toshy.py $INSTALL_ARGS"
            echo_unbuffered
        elif [ "$confirm" = "q" ]; then
            echo_unbuffered
            echo_unbuffered "Installation cancelled."
            echo_unbuffered
            exit 0
        else
            echo_unbuffered "Invalid option. Please enter Y, e, or q."
        fi
    done
}

# Get branch from user input
get_branch() {
    local branch
    
    echo_unbuffered
    echo_unbuffered "Which Toshy branch would you like to install?"
    echo_unbuffered "1) $DEFAULT_BRANCH (default/stable)"
    echo_unbuffered "2) $SUGGESTED_BRANCH (development/beta)"
    echo_unbuffered "3) Enter custom branch name"
    echo_unbuffered
    
    sleep 0.1
    
    read_interactive -p "Branch [1-3, default=1]: " choice
    
    # shellcheck disable=SC2154
    case "$choice" in
        "" | "1")
            branch="$DEFAULT_BRANCH"
            ;;
        "2")
            branch="$SUGGESTED_BRANCH"
            ;;
        "3")
            read_interactive -p "Enter custom branch name: " custom_branch
            branch="${custom_branch:-$DEFAULT_BRANCH}"
            ;;
        *)
            echo_unbuffered "Invalid choice, using default ($DEFAULT_BRANCH)"
            branch="$DEFAULT_BRANCH"
            ;;
    esac
    
    echo_unbuffered
    echo_unbuffered "Selected branch: $branch"
    echo "$branch"
}

# Create a unique folder name with timestamp
FILE_NAME="toshy_$(date +%Y%m%d_%H%M)"
DOWNLOAD_DIR="$HOME/Downloads"

# Initialize install args
INSTALL_ARGS="install"

echo_unbuffered
echo_unbuffered
echo_unbuffered "=== Toshy Bootstrap Installer ==="

# STEP 1: Get install options FIRST
get_install_options

# STEP 2: Get branch selection
echo_unbuffered
BRANCH=$(get_branch)

# Set up paths
URL="https://github.com/RedBearAK/toshy/archive/refs/heads/$BRANCH.zip"
TOSHY_DIR="$DOWNLOAD_DIR/$FILE_NAME/Toshy-$BRANCH"

echo_unbuffered
echo_unbuffered "Starting download..."
echo_unbuffered "Branch: $BRANCH"

# Create the Downloads directory if it doesn't exist
mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

# Download the zip file using curl or wget
echo_unbuffered
echo_unbuffered "Downloading Toshy from GitHub..."
echo_unbuffered
if ! (curl -L "$URL" -o "$FILE_NAME.zip" || wget "$URL" -O "$FILE_NAME.zip"); then
    echo_unbuffered "Download failed. Please check your internet connection or verify the branch name exists."
    exit 1
fi

# Create directory and extract the zip file
echo_unbuffered
echo_unbuffered "Extracting files..."
mkdir -p "$FILE_NAME"
if ! unzip -q -o "$FILE_NAME.zip" -d "$FILE_NAME"; then
    echo_unbuffered "Extraction failed. Please make sure 'unzip' is installed."
    exit 1
fi
echo_unbuffered "Done."

# Navigate to the setup directory
cd "$FILE_NAME/Toshy-$BRANCH"

# Define the Ctrl+C trap function
ctrl_c() {
    echo_unbuffered
    echo_unbuffered "Installation paused."
    echo_unbuffered
    echo_unbuffered "To navigate to the Toshy directory and run the setup manually, use:"
    echo_unbuffered "  cd \"$TOSHY_DIR\""
    echo_unbuffered
    exit 0
}

# Set up the trap before setup launches
trap ctrl_c INT

echo_unbuffered
echo_unbuffered "Download complete. Toshy extracted to:"
echo_unbuffered "  $TOSHY_DIR"

# Strong visual separation before setup launches
echo_unbuffered
echo_unbuffered
echo_unbuffered "================================================================================"
echo_unbuffered "================================================================================"
echo_unbuffered "===                                                                          ==="
echo_unbuffered "===                     LAUNCHING TOSHY SETUP SCRIPT                         ==="
echo_unbuffered "===                                                                          ==="
echo_unbuffered "================================================================================"
echo_unbuffered "================================================================================"
echo_unbuffered
echo_unbuffered

# Run the setup script with collected arguments
# shellcheck disable=SC2086
if ! ./setup_toshy.py $INSTALL_ARGS; then
    echo_unbuffered "Setup script execution failed."
    exit 1
fi

echo_unbuffered
echo_unbuffered "Toshy bootstrap installation completed successfully!"
echo_unbuffered

# Return to original directory
cd "$ORIGINAL_DIR"

# End of file #
