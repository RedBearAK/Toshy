#!/bin/bash

# scripts/bootstrap.sh
# Toshy Installation Bootstrap Script
# https://github.com/RedBearAK/toshy

# shellcheck disable=SC2034
VERSION='20260708'

set -e  # Exit on error

# Force unbuffered output
exec > >(cat) 2>&1

# Store the original directory
ORIGINAL_DIR="$(pwd)"

# Toshy repo URL (cloned with git so any branch/tag/commit can be checked out)
TOSHY_URL="https://github.com/RedBearAK/toshy.git"

# Default ref (the common case is still a branch name)
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
    echo_unbuffered "  --dev-keymapper[=REF]     Install dev keymapper (branch, tag, or commit SHA)"
    echo_unbuffered "  --fancy-pants             See README for more info on this option"
    echo_unbuffered
}

# Confirm the system is updated BEFORE any other prompts, but only for a FRESH
# install. On a reinstall (existing ~/.config/toshy) this is skipped, and the
# main setup script self-skips on the same folder check.
#
# Keep this prompt's wording in sync with ask_is_distro_updated() in setup_toshy.py.
# Path mirrors cnfg.toshy_dir_path in setup_toshy.py: ~/.config/toshy
check_system_updated() {
    if [ -d "$HOME/.config/toshy" ]; then
        return 0    # reinstall: not pertinent, leave SKIP_UPDATE_CHECK_ARG empty
    fi

    echo_unbuffered
    echo_unbuffered "!! NOTICE: It is ESSENTIAL to have your system completely updated."
    echo_unbuffered

    read_interactive -p "Have you updated your system recently? [y/N]: " update_response

    # shellcheck disable=SC2154
    case "$update_response" in
        y|Y)
            # Fresh install, user confirmed: tell setup_toshy.py not to ask again.
            SKIP_UPDATE_CHECK_ARG="--skip-update-check"
            ;;
        *)
            echo_unbuffered
            echo_unbuffered "Try the installer again after you've done a full system update. Exiting."
            exit 1
            ;;
    esac
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

# Get ref (branch/tag/commit) from user input
get_branch() {
    local branch

    echo_unbuffered
    echo_unbuffered "Which Toshy branch would you like to install?"
    echo_unbuffered "1) $DEFAULT_BRANCH (default/stable)"
    echo_unbuffered "2) $SUGGESTED_BRANCH (development/beta)"
    echo_unbuffered "3) Enter custom ref (branch, tag, or commit SHA)"
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
            read_interactive -p "Enter custom ref (branch/tag/commit): " custom_branch
            branch="${custom_branch:-$DEFAULT_BRANCH}"
            ;;
        *)
            echo_unbuffered "Invalid choice, using default ($DEFAULT_BRANCH)"
            branch="$DEFAULT_BRANCH"
            ;;
    esac

    echo_unbuffered
    echo_unbuffered "Selected ref: $branch"
    echo "$branch"
}

# Confirm git is present before anything else (clone needs it)
if ! command -v git >/dev/null 2>&1; then
    echo_unbuffered "ERROR: 'git' is required to fetch Toshy but was not found."
    echo_unbuffered "       Please install git and run this script again."
    exit 1
fi

# Create a unique folder name with timestamp
FILE_NAME="toshy_$(date +%Y%m%d_%H%M)"
DOWNLOAD_DIR="$HOME/Downloads"

# Initialize install args
INSTALL_ARGS="install"

# Set by check_system_updated() only when a FRESH install is confirmed updated,
# so setup_toshy.py won't re-ask the same question. Empty on reinstalls.
SKIP_UPDATE_CHECK_ARG=""


echo_unbuffered
echo_unbuffered
echo_unbuffered "=== Toshy Bootstrap Installer ==="


# STEP 0: Confirm system is updated (fresh installs only), before any other prompts
check_system_updated

# STEP 1: Get install options FIRST
get_install_options

# Append the update-check latch (empty unless a fresh install was confirmed)
INSTALL_ARGS="$INSTALL_ARGS $SKIP_UPDATE_CHECK_ARG"

# STEP 2: Get ref selection
echo_unbuffered
BRANCH=$(get_branch)

# Set up paths. The clone target is a fixed, known directory name (no archive
# folder-name guessing), so the checked-out ref does not affect the path.
CLONE_PARENT="$DOWNLOAD_DIR/$FILE_NAME"
TOSHY_DIR="$CLONE_PARENT/toshy"

echo_unbuffered
echo_unbuffered "Starting fetch..."
echo_unbuffered "Ref: $BRANCH"

# Create the parent directory if it doesn't exist
mkdir -p "$CLONE_PARENT"
cd "$CLONE_PARENT"

# Clone the full repo (full history so any commit/tag/branch can be checked
# out, including for git-bisect-style installs).
echo_unbuffered
echo_unbuffered "Cloning Toshy from GitHub..."
echo_unbuffered
if ! git clone "$TOSHY_URL" "$TOSHY_DIR"; then
    echo_unbuffered "Clone failed. Please check your internet connection or repo access."
    exit 1
fi

# Check out the requested ref. Passed as a single argument so a ref containing
# spaces (e.g. an oddly named tag) survives intact.
echo_unbuffered
echo_unbuffered "Checking out ref: $BRANCH"
if ! git -C "$TOSHY_DIR" checkout "$BRANCH"; then
    echo_unbuffered "Checkout failed. Verify the branch, tag, or commit exists: $BRANCH"
    exit 1
fi
echo_unbuffered "Done."

# Navigate to the setup directory
cd "$TOSHY_DIR"

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
echo_unbuffered "Clone complete. Toshy checked out to:"
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
