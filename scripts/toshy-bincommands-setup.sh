#!/usr/bin/env bash


# "Install" the bin commands as symlinks in user-local bin location.

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


TOSHY_BIN="${HOME}/.config/toshy/scripts/bin"
LOCAL_BIN="${HOME}/.local/bin"

echo -e "\nInstalling Toshy terminal commands..."

mkdir -p "${LOCAL_BIN}"

ln -sf "${TOSHY_BIN}/toshy-systemd-setup.sh"            "${LOCAL_BIN}/toshy-systemd-setup"
ln -sf "${TOSHY_BIN}/toshy-systemd-remove.sh"           "${LOCAL_BIN}/toshy-systemd-remove"
ln -sf "${TOSHY_BIN}/toshy-services-status.sh"          "${LOCAL_BIN}/toshy-services-status"
ln -sf "${TOSHY_BIN}/toshy-services-disable.sh"         "${LOCAL_BIN}/toshy-services-disable"
ln -sf "${TOSHY_BIN}/toshy-services-enable.sh"          "${LOCAL_BIN}/toshy-services-enable"
ln -sf "${TOSHY_BIN}/toshy-services-restart.sh"         "${LOCAL_BIN}/toshy-services-restart"
ln -sf "${TOSHY_BIN}/toshy-services-start.sh"           "${LOCAL_BIN}/toshy-services-start"
ln -sf "${TOSHY_BIN}/toshy-services-stop.sh"            "${LOCAL_BIN}/toshy-services-stop"
ln -sf "${TOSHY_BIN}/toshy-services-log.sh"             "${LOCAL_BIN}/toshy-services-log"
ln -sf "${TOSHY_BIN}/toshy-config-start.sh"             "${LOCAL_BIN}/toshy-config-start"
ln -sf "${TOSHY_BIN}/toshy-config-stop.sh"              "${LOCAL_BIN}/toshy-config-stop"
ln -sf "${TOSHY_BIN}/toshy-config-restart.sh"           "${LOCAL_BIN}/toshy-config-restart"
ln -sf "${TOSHY_BIN}/toshy-config-start-verbose.sh"     "${LOCAL_BIN}/toshy-config-start-verbose"
ln -sf "${TOSHY_BIN}/toshy-config-start-verbose.sh"     "${LOCAL_BIN}/toshy-config-verbose-start"
ln -sf "${TOSHY_BIN}/toshy-config-start-verbose.sh"     "${LOCAL_BIN}/toshy-debug"
ln -sf "${TOSHY_BIN}/toshy-tray.sh"                     "${LOCAL_BIN}/toshy-tray"
ln -sf "${TOSHY_BIN}/toshy-gui.sh"                      "${LOCAL_BIN}/toshy-gui"
ln -sf "${TOSHY_BIN}/toshy-env.sh"                      "${LOCAL_BIN}/toshy-env"
ln -sf "${TOSHY_BIN}/toshy-venv.sh"                     "${LOCAL_BIN}/toshy-venv"
ln -sf "${TOSHY_BIN}/toshy-fnmode.sh"                   "${LOCAL_BIN}/toshy-fnmode"
ln -sf "${TOSHY_BIN}/toshy-devices.sh"                  "${LOCAL_BIN}/toshy-devices"
ln -sf "${TOSHY_BIN}/toshy-versions.sh"                 "${LOCAL_BIN}/toshy-versions"
ln -sf "${TOSHY_BIN}/toshy-reinstall.sh"                "${LOCAL_BIN}/toshy-reinstall"
ln -sf "${TOSHY_BIN}/toshy-machine-id.sh"               "${LOCAL_BIN}/toshy-machine-id"
ln -sf "${TOSHY_BIN}/toshy-kwin-dbus-service.sh"        "${LOCAL_BIN}/toshy-kwin-dbus-service"
ln -sf "${TOSHY_BIN}/toshy-cosmic-dbus-service.sh"      "${LOCAL_BIN}/toshy-cosmic-dbus-service"
ln -sf "${TOSHY_BIN}/toshy-wlroots-dbus-service.sh"     "${LOCAL_BIN}/toshy-wlroots-dbus-service"


echo ""
echo "Finished installing Toshy terminal commands:"
echo ""
echo "- toshy-systemd-setup"
echo "- toshy-systemd-remove"
echo "- toshy-services-status"
echo "- toshy-services-disable"
echo "- toshy-services-enable"
echo "- toshy-services-restart"
echo "- toshy-services-start"
echo "- toshy-services-stop"
echo "- toshy-services-log"
echo "- toshy-config-start"
echo "- toshy-config-stop"
echo "- toshy-config-restart"
echo "- toshy-config-start-verbose"
echo "- toshy-config-verbose-start"
echo "- toshy-config-debug"
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
echo "The commands may not be available until you close the current terminal, or "
echo "run 'hash -r', or source your shell RC file to refresh executable hash table."
echo ""




####################################################################################################
####################################################################################################
####################################################################################################
####################################################################################################

# Current generation of code that tries to make sure ~/.local/bin/ is in the user's PATH


LOCAL_BIN="${HOME}/.local/bin"
RUN_TMP_DIR="${XDG_RUNTIME_DIR:-/tmp}"
GOOD_PATH_TMP="${RUN_TMP_DIR}/toshy_installer_says_path_is_good"
FIX_PATH_TMP="${RUN_TMP_DIR}/toshy_installer_says_fix_path"

# Exit early if path is already confirmed good
[ -f "${GOOD_PATH_TMP}" ] && exit 0

mkdir -p "${LOCAL_BIN}"

# Function to check if a file contains the PATH modification
path_contains_local_bin() {
    local file="$1"
    [ ! -f "${file}" ] && return 1
    
    grep -q "PATH=.*\${HOME}/.local/bin" "${file}" || \
    grep -q "PATH=.*${LOCAL_BIN}" "${file}" || \
    grep -q "fish_add_path.*\.local/bin" "${file}"
}

# Function to check if ~/.local/bin is currently in PATH
is_local_bin_in_current_path() {
    echo "${PATH}" | grep -q -E "(^|:)${LOCAL_BIN}(:|$)"
}

# Function to add path to a specified file
add_path_to_file() {
    local file="$1"
    
    # Create file if it doesn't exist
    [ ! -f "${file}" ] && touch "${file}"

    # Special handling for fish shell
    if [[ "${file}" == *"fish"* ]]; then
        {
            echo ""
            echo "# Add ~/.local/bin to PATH"
            echo "if test -d \"\$HOME/.local/bin\""
            echo "    fish_add_path \$HOME/.local/bin"
            echo "end"
        } >> "${file}"
    else
        {
            echo ""
            echo "# Add ~/.local/bin to PATH"
            echo "if [ -d \"\${HOME}/.local/bin\" ] && [[ \":\${PATH}:\" != *\":\${HOME}/.local/bin:\"* ]]; then"
            echo "    PATH=\"\${HOME}/.local/bin:\${PATH}\""
            echo "fi"
        } >> "${file}"
    fi
}

# Main PATH setup logic
setup_path() {
    # Check if ~/.local/bin is already in current PATH
    if is_local_bin_in_current_path; then
        echo "${HOME}/.local/bin is already in PATH"
        touch "${GOOD_PATH_TMP}"
        return 0
    fi

    # Define all relevant shell files to check
    local shell_files=(
        "${HOME}/.profile"
        "${HOME}/.bash_profile" 
        "${HOME}/.bashrc"
        "${HOME}/.zshrc"
        "${HOME}/.zprofile"
        "${HOME}/.config/fish/config.fish"
    )
    
    # Find files that need the PATH modification
    local files_needing_path=()
    
    for file in "${shell_files[@]}"; do
        # Check all existing files, plus always include .profile for universal compatibility
        if [ -f "${file}" ] || [[ "${file}" == *"profile"* ]]; then
            if ! path_contains_local_bin "${file}"; then
                files_needing_path+=("${file}")
            fi
        fi
    done
    
    # If no files need modification, we're done
    if [ ${#files_needing_path[@]} -eq 0 ]; then
        echo "PATH is already configured in shell files"
        touch "${GOOD_PATH_TMP}"
        return 0
    fi
    
    # Ask once if we should add to PATH
    local response
    if [ -f "${FIX_PATH_TMP}" ]; then
        response="y"
    else
        read -r -p "Add ~/.local/bin to PATH for Toshy commands? [Y/n] " response
    fi
    
    case $response in
        [Nn]* ) 
            echo "Skipped PATH configuration"
            return 0
            ;;
        * )
            # Add to all files that need it
            for file in "${files_needing_path[@]}"; do
                add_path_to_file "${file}"
            done
            echo "Added ~/.local/bin to PATH in ${#files_needing_path[@]} shell file(s)"
            echo "Restart your terminal or source your shell RC file to refresh commands"
            ;;
    esac
}

# Run the setup
setup_path



####################################################################################################
####################################################################################################
####################################################################################################
####################################################################################################

# Last generation of code that tries to make sure ~/.local/bin/ is in PATH (was failing sometimes)

PROFILE="${HOME}/.profile"
BASH_PROFILE="${HOME}/.bash_profile"
LOCAL_BIN="${HOME}/.local/bin"
PATH_LINE="PATH=\"\${HOME}/.local/bin:\${PATH}\""
RUN_TMP_DIR="${XDG_RUNTIME_DIR:-/tmp}"
GOOD_PATH_TMP="${RUN_TMP_DIR}/toshy_installer_says_path_is_good"
FIX_PATH_TMP="${RUN_TMP_DIR}/toshy_installer_says_fix_path"

[ -f "${GOOD_PATH_TMP}" ] && exit 0

mkdir -p "${LOCAL_BIN}"
[ ! -f "${PROFILE}" ] && touch "${PROFILE}"
[ ! -f "${BASH_PROFILE}" ] && touch "${BASH_PROFILE}"

path_contains_local_bin() {
    local file="$1"
    grep -q "PATH=.*\${HOME}/.local/bin" "${file}" || \
    grep -q "PATH=.*${LOCAL_BIN}" "${file}"
}

check_rc_files() {
    local rc_files=(".bashrc" ".zshrc" ".config/fish/config.fish")
    for rc in "${rc_files[@]}"; do
        if [ -f "${HOME}/${rc}" ] && grep -q "PATH.*/.local/bin" "${HOME}/${rc}"; then
            echo "Note: Found ~/.local/bin PATH modification in ~/${rc}"
            echo "      Consider removing it to avoid duplicate PATH entries"
        fi
    done
}

# Function to add path to a specified file
add_path_to_file() {
    local file="$1"
    local file_name
    file_name="$(basename "$file")"

    {
        echo -e "\n# Add ~/.local/bin to PATH if not already present"
        echo "if [ -d \"\${HOME}/.local/bin\" ] && [[ \":\${PATH}:\" != *\":\${HOME}/.local/bin:\"* ]]; then"
        echo "    ${PATH_LINE}"
        echo "fi"
    } >> "${file}"
    echo "Added PATH modification to ~/${file_name}"
}

# Handle .profile
if ! path_contains_local_bin "${PROFILE}"; then
    if [ -f "${FIX_PATH_TMP}" ]; then
        response="y"
    else
        read -r -p "Add ~/.local/bin to PATH in ~/.profile? [Y/n] " response
    fi
    
    case $response in
        [Nn]* ) 
            echo "Skipped modifying ~/.profile"
            ;;
        * )
            add_path_to_file "${PROFILE}"
            ;;
    esac
fi

# Handle .bash_profile
if ! path_contains_local_bin "${BASH_PROFILE}"; then
    if [ -f "${FIX_PATH_TMP}" ]; then
        response="y"
    else
        read -r -p "Add ~/.local/bin to PATH in ~/.bash_profile? [Y/n] " response
    fi
    
    case $response in
        [Nn]* ) 
            echo "Skipped modifying ~/.bash_profile"
            ;;
        * )
            add_path_to_file "${BASH_PROFILE}"
            ;;
    esac
fi

check_rc_files

exit 0
