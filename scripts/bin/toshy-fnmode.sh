#!/usr/bin/env bash

# Script to change the function keys mode of keyboards that use `hid_apple` device driver

SCRIPT_VERSION='20261001'


safe_shutdown() {
    local exit_code=0
    if [[ -n $1 ]]; then
        exit_code=$1
    fi
    # invalidate sudo ticket on the way out
    sudo -k > /dev/null
    # give the shell prompt some room after script is done
    echo ""
    # shellcheck disable=SC2086
    exit "$exit_code"
}

trap 'safe_shutdown 130' SIGINT
trap 'safe_shutdown 143' SIGTERM
trap 'safe_shutdown $?' EXIT

sudo_cmd="sudo"

# Check if the script is being run as root, avoid unnecessary use of 'sudo'
if [[ $EUID -eq 0 ]]; then
    # echo "Running script as root"
    sudo_cmd=""
fi

modprobe_dir="/etc/modprobe.d"
conf_file="$modprobe_dir/hid_apple.conf"
fnmode_file="/sys/module/hid_apple/parameters/fnmode"

if [[ -f "$fnmode_file" ]]; then
    curr_fnmode=$(<${fnmode_file})
else
    curr_fnmode="N/A"
    echo ""
    echo "ERROR: Unable to read current function keys mode:"
    echo "        '$fnmode_file' is not a valid file."
fi

curr_mode_str="Current function keys mode for the 'hid_apple' driver:"
var_make_persistent="false"
new_fnmode=""

# echo valid choices text block to terminal
fn_show_valid_choices() {
    echo "Valid choices for function keys mode are (default mode marked with '*'):"
    echo "  0 = disabled   [F-keys are _ONLY_ F-keys, no media/hardware functions]"
    echo "  1 = fkeyslast  [Media/hardware keys first, F-keys when Fn key is held]"
    echo "  2 = fkeysfirst [F-keys first, media/hardware keys when Fn key is held]"
    echo "  3 = auto*      [Usually defaults to acting like mode: '1' (fkeyslast)]"
    echo ""
}

# shellcheck disable=SC2086
fn_show_help() {
    echo ""
    echo "Usage: $(basename $0) [--option] [mode]"
    echo ""
    echo "Changes the function keys mode of Apple keyboards that use the"
    echo "'hid_apple' device driver. Interactive prompts will be shown"
    echo "if no options or arguments are provided."
    echo ""
    echo "Requires superuser privileges to modify the mode."
    echo ""
    echo "Options:"
    echo "  -P, --persistent    Make the mode change persistent across reboots."
    echo "  -i, --info          Show current live and persistent state, and exit."
    echo "  -V, --version       Show the version of this script and exit."
    echo "  -h, --help          Show this help message and exit."
    echo ""
    echo "Arguments:"
    echo "  mode     Desired function keys mode (see below for valid modes)."
    echo ""
    fn_show_valid_choices
}

fn_fnmode_str() {
    case "$1" in
        0) echo "disabled" ;;
        1) echo "fkeyslast" ;;
        2) echo "fkeysfirst" ;;
        3) echo "auto" ;;
    esac
}

fn_show_info() {
    local mode_str=""
    mode_str=$(fn_fnmode_str "${curr_fnmode}")
    if [[ -n "${mode_str}" ]]; then
        echo -e "\n${curr_mode_str}\n  '${curr_fnmode}' (${mode_str})"
    else
        echo -e "\n${curr_mode_str} '${curr_fnmode}'"
    fi
    if [[ -s "$conf_file" ]]; then
        conf_file_txt="$(nl -n ln ${conf_file} | awk '{$1=sprintf("  Line %02d:", $1); print $0}')"
    elif [[ -f "$conf_file" ]]; then
        conf_file_txt="  File is empty."
    else
        conf_file_txt="  File does not exist."
    fi
    echo ""
    echo -e "Current contents of '${conf_file}':\n${conf_file_txt}"
}

fn_msg_distro_type() {
    echo "Trying initramfs update command(s) for distro type: '$1'."
}

fn_update_initramfs() {
    # Get the distribution id
    local dist_id
    # do not forget to strip any quotes around distro ID, or case match will fail
    dist_id=$(awk -F= '/^ID=/ { gsub(/"/, "", $2); print tolower($2)}' /etc/os-release)
    wait_msg="Please WAIT (initramfs update can take some time to complete)..."
    case "$dist_id" in
        debian|ubuntu|peppermint)
            echo -e "\n$(fn_msg_distro_type 'Debian/Ubuntu')"
            echo -e "\n${wait_msg}\n"
            # redirect stdout but not stderr to quiet this down
            ${sudo_cmd} update-initramfs -u > /dev/null
            ;;
        fedora|opensuse*|centos|ultramarine|almalinux|rocky)
            dracut_conf_dir="/etc/dracut.conf.d"
            drct_hidapple_conf_file="${dracut_conf_dir}/hid_apple.conf"
            if [[ ! -d "$dracut_conf_dir" ]]; then
                ${sudo_cmd} mkdir -p "$dracut_conf_dir"
            fi
            # dracut parser wants spaces around the " <value> " given to 'install_items+='
            drct_ins_str='install_items+=" /etc/modprobe.d/hid_apple.conf "'
            echo "${drct_ins_str}" | ${sudo_cmd} tee "$drct_hidapple_conf_file" > /dev/null
            echo -e "\n$(fn_msg_distro_type 'Fedora/RHEL/openSUSE')"
            echo -e "\n${wait_msg}\n"
            # dracut log level 3 = show only warnings or errors/failures
            ${sudo_cmd} dracut -L3 --force
            ;;
        silverblue)
            echo -e "\n$(fn_msg_distro_type 'Fedora Silverblue')"
            echo -e "\n${wait_msg}\n"
            ${sudo_cmd} rpm-ostree initramfs --enable --arg=-I --arg=/etc/modprobe.d/hid_apple.conf
            ;;
        arch*|arcolinux|manjaro|endeavouros)
            echo -e "\n$(fn_msg_distro_type 'Arch')"
            echo -e "\n${wait_msg}\n"
            ${sudo_cmd} mkinitcpio -P
            ;;
        *)
            echo ""
            echo "Unknown distribution ID: '$dist_id'"
            echo "Please manually update your initramfs image."
            return 1
            ;;
    esac
    return 0
}

fn_make_fnmode_persistent() {
    local new_fnmode_arg="$1"
    local options_rgx="^options hid_apple fnmode=[0-3]$"
    local options_sub="options hid_apple fnmode=${new_fnmode_arg}"
    local modprobe_dir="/etc/modprobe.d"
    local conf_file="${modprobe_dir}/hid_apple.conf"
    # If the persistent flag is true, make the change persistent
    if [[ "${var_make_persistent}" == "true" ]]; then
        # Check if the /etc/modprobe.d directory exists
        if [[ -d "${modprobe_dir}" ]]; then
            # Check if the /etc/modprobe.d/hid_apple.conf file exists, create it if not
            if [[ ! -f "${conf_file}" ]]; then
                ${sudo_cmd} touch "${conf_file}"
            fi
            # Look for the options hid_apple fnmode=X line in the file
            if grep -q "${options_rgx}" "${conf_file}"; then
                # If found, modify the X to match the new fnmode
                ${sudo_cmd} sed -ri "s/${options_rgx}/${options_sub}/" "${conf_file}"
            else
                # If not found, append the whole line to the file
                echo "${options_sub}" | ${sudo_cmd} tee -a "${conf_file}" > /dev/null
            fi
            if ! fn_update_initramfs; then
                echo ""
                echo "ERROR: Non-zero return status from attempt to update initramfs. Exiting."
                safe_shutdown 1
            fi
            echo "Success! The fnmode change should now persist across reboots."
        else
            echo ""
            echo "WARNING: Could not make the change persistent."
            echo "The '${modprobe_dir}' directory does not exist."
        fi
    else
        echo ""
        echo "The fnmode change is active, but will not persist across reboots."
        echo ""
    fi
}

fn_update_fnmode() {
    local new_fnmode_arg="$1"
    if [[ $new_fnmode_arg =~ ^[0-3]$ ]]; then
        echo ""
        if echo "${new_fnmode_arg}" | ${sudo_cmd} tee "${fnmode_file}" > /dev/null; then
            # Read back the value from the file
            local post_update_fnmode=""
            post_update_fnmode=$(<$fnmode_file)
            if [[ "$post_update_fnmode" == "$new_fnmode_arg" ]]; then
                update_msg="ACTION: Function keys mode for 'hid_apple' updated to:"
                local mode_str=""
                mode_str=$(fn_fnmode_str "$new_fnmode_arg")
                echo -e "\n${update_msg} '${new_fnmode_arg}' (${mode_str})"
                # Make change persistent if desired
                fn_make_fnmode_persistent "${new_fnmode_arg}"
            else
                echo -e "\nFailed to update function keys mode for 'hid_apple'."
                echo "Current value is: '$post_update_fnmode'"
                safe_shutdown 1
            fi
        else
            echo -e "\nFailed to update function keys mode for 'hid_apple'."
            safe_shutdown 1
        fi
    else
        echo -e "\nInvalid input. Please enter a number from 0 to 3."
        safe_shutdown 1
    fi
}

fn_check_preconditions() {
    # Check if the hid_apple module is loaded
    if ! lsmod | grep -q '^hid_apple'; then
        echo ""
        echo "ERROR: The 'hid_apple' module is not loaded. The script cannot proceed."
        echo "        It is unlikely that any attached keyboard device uses 'hid_apple'."
        safe_shutdown 1
    fi
    # Check if the fnmode file exists (unlikely if 'hid_apple' module is loaded)
    if [[ ! -f "$fnmode_file" ]]; then
        echo ""
        echo "ERROR: The script cannot proceed. Reason:"
        echo "        '$fnmode_file' does not exist."
        safe_shutdown 1
    fi
}

while (( $# )); do
    case "$1" in
        -h|--help)
            fn_show_help
            safe_shutdown
            ;;
        -i|--info)
            fn_show_info
            safe_shutdown
            ;;
        -V|--version)
            echo ""
            echo "toshy-fnmode version ${SCRIPT_VERSION}"
            safe_shutdown
            ;;
        -P|--persistent)
            var_make_persistent="true"
            shift
            ;;
        [0-3])
            new_fnmode="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            fn_show_help
            safe_shutdown 1
            ;;
    esac
done

if [[ -n "${new_fnmode}" ]]; then
    fn_check_preconditions
    new_fnmode_str=$(fn_fnmode_str "${new_fnmode}")
    updating_msg="Updating function keys mode for 'hid_apple' devices to:"
    echo ""
    echo "${updating_msg} '${new_fnmode}' (${new_fnmode_str})"
    fn_update_fnmode "${new_fnmode}"
    safe_shutdown
fi

# Check that a mode argument follows the use of persistent option
if [[ "${var_make_persistent}" == "true" && -z "${new_fnmode}" ]]; then
    echo ""
    echo "ERROR: When the persistent option is used, a mode argument must be provided."
    fn_show_help
    safe_shutdown 1
fi

# Check preconditions here in the case where no arguments were passed and 
# the script is about to start showing the interactive prompts:
fn_check_preconditions

fn_show_info

echo ""
fn_show_valid_choices
read -rp "Enter your desired mode [0/1/2/3]: " resp_to_fnmode_prompt
fn_update_fnmode "$resp_to_fnmode_prompt"
# echo ""
read -rp "Make the mode change persistent (update initramfs)? [y/N]: " resp_to_persist_prompt
if [[ "$resp_to_persist_prompt" =~ ^[yY]$ ]]; then
    var_make_persistent="true"
    fn_make_fnmode_persistent "$resp_to_fnmode_prompt"
elif [[ "$resp_to_persist_prompt" =~ ^[nN]$ ]]; then
    echo ""
    echo "Response was: '${resp_to_persist_prompt}'. Change will NOT be made persistent."
else
    echo ""
    echo "Input invalid: '${resp_to_persist_prompt}'. Change will NOT be made persistent."
fi
safe_shutdown
