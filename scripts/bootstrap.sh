#!/bin/bash

# scripts/bootstrap.sh
# Toshy Installation Bootstrap Script
# https://github.com/RedBearAK/toshy

# shellcheck disable=SC2034
VERSION='20260714'

# NOTE: deliberately no 'set -e'. Every command that matters is checked
# explicitly below. And 'set -e' is silently disabled inside if/&&/||/!
# conditions anyway, so it provides partial coverage while looking like
# total coverage.

# Force unbuffered output
exec > >(cat) 2>&1

# Store the original directory
ORIGINAL_DIR="$(pwd)"

# Source archives come from codeload, which serves a tarball for ANY ref: a
# branch name, a tag, or a commit SHA (full or abbreviated). Fetching an archive
# means 'git' is NOT required to install Toshy. That matters, because 'git' is
# not preinstalled on many desktop distros, and it is Toshy's own native package
# install that puts it there. Requiring it just to bootstrap was backwards.
TOSHY_ARCHIVE_BASE="https://codeload.github.com/RedBearAK/toshy/tar.gz"

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

# Download a URL to a local path, using whichever tool was found at startup.
# The '-f' flag on curl is load-bearing: without it, a 404 error page is written
# to the destination file and curl still exits 0.
download_file() {
    local source_url="$1"
    local dest_path="$2"

    if [ "$DOWNLOAD_TOOL" = "curl" ]; then
        curl -fL --retry 5 --retry-delay 2 --connect-timeout 20 \
                -o "$dest_path" "$source_url"
        return $?
    fi

    wget --tries=5 --waitretry=2 --timeout=20 -O "$dest_path" "$source_url"
    return $?
}

# Confirm this is real Linux before anything else happens. Toshy depends on the
# kernel's evdev/uinput interfaces, which exist nowhere else. Doing this first
# means a wrong OS fails in the first second, instead of after several prompts
# and a few megabytes of download.
KERNEL_NAME="$(uname -s 2>/dev/null)"

# Fall back to a Linux-only kernel artifact if 'uname' somehow is not present.
if [ -z "$KERNEL_NAME" ] && [ -r /proc/version ]; then
    KERNEL_NAME="Linux"
fi

case "$KERNEL_NAME" in
    Linux)
        : # Carry on. This is the only supported kernel.
        ;;
    Darwin)
        echo_unbuffered
        echo_unbuffered "ERROR: This is macOS. Toshy only runs on Linux."
        echo_unbuffered
        echo_unbuffered "       Toshy exists to bring macOS-style keyboard shortcuts TO Linux."
        echo_unbuffered "       On macOS you already have them, natively."
        echo_unbuffered
        exit 1
        ;;
    *)
        echo_unbuffered
        echo_unbuffered "ERROR: Toshy only runs on Linux. Detected kernel: '${KERNEL_NAME:-unknown}'"
        echo_unbuffered
        echo_unbuffered "       Toshy depends on the Linux kernel's 'evdev' and 'uinput'"
        echo_unbuffered "       interfaces, which do not exist on other systems."
        echo_unbuffered
        exit 1
        ;;
esac

# WSL reports itself as Linux, so it sails past the check above. But it has no
# real input devices, no uinput, and no desktop session, so Toshy cannot work
# there under any configuration. Hard stop.
if [ -n "$WSL_DISTRO_NAME" ] || \
        grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease 2>/dev/null; then
    echo_unbuffered
    echo_unbuffered "ERROR: This looks like WSL (Windows Subsystem for Linux)."
    echo_unbuffered
    echo_unbuffered "       Toshy needs the kernel's 'evdev' and 'uinput' interfaces, real"
    echo_unbuffered "       input devices, and a desktop session. WSL provides none of"
    echo_unbuffered "       these, so Toshy cannot work here."
    echo_unbuffered
    exit 1
fi

# Confirm a download tool is present. One of these is almost certainly here
# already: the quick-install one-liner uses curl or wget to fetch this script.
DOWNLOAD_TOOL=""
if command -v curl >/dev/null 2>&1; then
    DOWNLOAD_TOOL="curl"
elif command -v wget >/dev/null 2>&1; then
    DOWNLOAD_TOOL="wget"
else
    echo_unbuffered "ERROR: Either 'curl' or 'wget' is required to fetch Toshy."
    echo_unbuffered "       Please install one of them and run this script again."
    exit 1
fi

# Confirm 'tar' is present (used to unpack the source archive).
if ! command -v tar >/dev/null 2>&1; then
    echo_unbuffered "ERROR: 'tar' is required to unpack Toshy but was not found."
    echo_unbuffered "       Please install tar and run this script again."
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

# Set up paths. The archive is unpacked into a fixed, known directory, and the
# archive's own top-level folder is stripped on extraction. That folder's name
# varies by ref type ('toshy-main', 'toshy-Toshy_v26.06.0', 'toshy-34bd0ec...'),
# and having to guess it is what drove the earlier move to a git clone. Stripping
# it means the requested ref never affects the resulting path, and nothing has to
# guess anything.
DOWNLOAD_PARENT="$DOWNLOAD_DIR/$FILE_NAME"
TOSHY_DIR="$DOWNLOAD_PARENT/toshy"
TARBALL_PATH="$DOWNLOAD_PARENT/toshy_source.tar.gz"

ARCHIVE_URL="$TOSHY_ARCHIVE_BASE/$BRANCH"

echo_unbuffered
echo_unbuffered "Starting fetch..."
echo_unbuffered "Ref: $BRANCH"

if ! mkdir -p "$TOSHY_DIR"; then
    echo_unbuffered "ERROR: Could not create download folder: $TOSHY_DIR"
    exit 1
fi

echo_unbuffered
echo_unbuffered "Downloading Toshy source archive..."
echo_unbuffered
if ! download_file "$ARCHIVE_URL" "$TARBALL_PATH"; then
    echo_unbuffered
    echo_unbuffered "ERROR: Download failed: $ARCHIVE_URL"
    echo_unbuffered "       Verify the branch, tag, or commit exists: $BRANCH"
    echo_unbuffered "       (And check your internet connection.)"
    exit 1
fi

# A truncated download or a served error page will not list as a gzip tarball.
if ! tar -tzf "$TARBALL_PATH" >/dev/null 2>&1; then
    echo_unbuffered "ERROR: Downloaded file is not a valid archive: $TARBALL_PATH"
    exit 1
fi

echo_unbuffered
echo_unbuffered "Unpacking archive..."
if ! tar -xzf "$TARBALL_PATH" -C "$TOSHY_DIR" --strip-components=1; then
    echo_unbuffered "ERROR: Could not unpack archive: $TARBALL_PATH"
    exit 1
fi

rm -f "$TARBALL_PATH"

# Sanity check: the setup script must exist, or the archive was not what we think.
if [ ! -f "$TOSHY_DIR/setup_toshy.py" ]; then
    echo_unbuffered "ERROR: Setup script not found after unpacking: $TOSHY_DIR/setup_toshy.py"
    echo_unbuffered "       The archive did not contain the expected Toshy source tree."
    exit 1
fi

# GitHub archives preserve the executable bit, but do not rely on it.
chmod +x "$TOSHY_DIR/setup_toshy.py" 2>/dev/null

echo_unbuffered "Done."

# Navigate to the setup directory
if ! cd "$TOSHY_DIR"; then
    echo_unbuffered "ERROR: Could not enter the Toshy folder: $TOSHY_DIR"
    exit 1
fi

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
echo_unbuffered "Download complete. Toshy source unpacked to:"
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
cd "$ORIGINAL_DIR" || exit 1

# End of file #
