#!/usr/bin/env bash

# scripts/bin/toshy-touchbar.sh
#
# Show, change, or recover the display mode of the Touch Bar on Apple MacBooks
# with a T1 chip (out-of-tree 'apple-touchbar' driver) or a T2 chip (mainline
# 'hid-appletb-kbd' driver). Works whether or not the keymapper is running.
#
# The keymapper briefly changes the Touch Bar mode while the Fn key is held.
# If it is stopped at exactly that moment, the temporary mode can be left
# behind. The keymapper keeps a small "swap record" while Fn is held, and
# this script can use that record to put the original mode back.
#
# Swap record contract (written by the keymapper, read here, never sourced):
#   file:   $XDG_RUNTIME_DIR/xwaykeyz/touchbar_fn_swap
#   line 1: full path of the sysfs attribute that was changed
#   line 2: original mode (single digit)
#   line 3: temporary mode written while Fn is held (single digit)

SCRIPT_VERSION='20261001'


# T1 'fnmode' values. These set a policy for what the Fn key does.
# Mirrors APPLETB_FN_MODE_* in the apple-touchbar driver source.
readonly T1_FNMODE_FKEYS_ONLY=0
readonly T1_FNMODE_MEDIA_FN_FKEYS=1
readonly T1_FNMODE_FKEYS_FN_MEDIA=2
readonly T1_FNMODE_MEDIA_ONLY=3
readonly T1_FNMODE_ESC_ONLY=4
readonly T1_FNMODE_MAX="$T1_FNMODE_ESC_ONLY"

# T2 'mode' values. These set what the Touch Bar is showing right now.
# Mirrors APPLETB_KBD_MODE_* in the hid-appletb-kbd driver source.
readonly T2_MODE_ESC_ONLY=0
readonly T2_MODE_FKEYS=1
readonly T2_MODE_MEDIA=2
readonly T2_MODE_OFF=3
readonly T2_MODE_MAX="$T2_MODE_OFF"

t1_attr_glob="/sys/bus/hid/drivers/apple-touchbar/*/fnmode"
t1_default_file="/sys/module/apple_touchbar/parameters/fnmode"

t2_attr_glob="/sys/bus/hid/drivers/hid-appletb-kbd/*/mode"
t2_default_file="/sys/module/hid_appletb_kbd/parameters/mode"

single_digit_rgx='^[0-9]$'

tb_kind=""
attr_file=""
default_file=""
max_mode=0

rec_state="none"
rec_orig=""
rec_temp=""

used_sudo="false"
action="interactive"
new_mode_arg=""


safe_shutdown() {
    local exit_code="${1:-0}"
    trap - EXIT
    if [[ "$used_sudo" == "true" ]]; then
        sudo -k > /dev/null 2>&1
    fi
    echo ""
    exit "$exit_code"
}

trap 'safe_shutdown 130' SIGINT
trap 'safe_shutdown 143' SIGTERM
trap 'safe_shutdown $?' EXIT


fn_runtime_dir() {
    # When launched through sudo, look in the invoking user's runtime dir,
    # because that is where the keymapper (a user service) keeps the record.
    if [[ $EUID -eq 0 && -n "$SUDO_UID" ]]; then
        echo "/run/user/${SUDO_UID}"
    elif [[ -n "$XDG_RUNTIME_DIR" ]]; then
        echo "$XDG_RUNTIME_DIR"
    else
        echo "/run/user/$(id -u)"
    fi
}

record_file="$(fn_runtime_dir)/xwaykeyz/touchbar_fn_swap"


# shellcheck disable=SC2086
fn_show_help() {
    echo ""
    echo "Usage: $(basename $0) [option] [mode]"
    echo ""
    echo "Shows or changes what the Touch Bar displays on Apple MacBooks with"
    echo "a T1 or T2 chip, and can repair a Touch Bar left in the wrong mode."
    echo "Run it with no options for a guided menu."
    echo ""
    echo "Options:"
    echo "  -s, --status    Show the current state and exit (changes nothing)."
    echo "  -r, --reset     Undo an interrupted Fn-key mode swap, if one is found."
    echo "  -V, --version   Show the version of this script and exit."
    echo "  -h, --help      Show this help message and exit."
    echo ""
    echo "Arguments:"
    echo "  mode            Mode number to set (run with --status to see the list)."
    echo ""
    echo "Changes last until the next reboot or driver reload."
}


fn_detect_driver() {
    local candidate=""
    shopt -s nullglob
    # shellcheck disable=SC2231
    for candidate in $t1_attr_glob; do
        tb_kind="T1"
        attr_file="$candidate"
        default_file="$t1_default_file"
        max_mode="$T1_FNMODE_MAX"
        break
    done
    if [[ -z "$attr_file" ]]; then
        # shellcheck disable=SC2231
        for candidate in $t2_attr_glob; do
            tb_kind="T2"
            attr_file="$candidate"
            default_file="$t2_default_file"
            max_mode="$T2_MODE_MAX"
            break
        done
    fi
    shopt -u nullglob
    [[ -n "$attr_file" ]]
}


fn_is_valid_mode() {
    [[ "$1" =~ $single_digit_rgx ]] && (( $1 <= max_mode ))
}


fn_read_mode_file() {
    # Echo the mode held in file $1; fail if unreadable or not a valid mode.
    local value=""
    [[ -r "$1" ]] || return 1
    IFS= read -r value < "$1" 2>/dev/null
    value="${value//[[:space:]]/}"
    fn_is_valid_mode "$value" || return 1
    echo "$value"
}


fn_mode_desc() {
    case "${tb_kind}:${1}" in
        "T1:${T1_FNMODE_FKEYS_ONLY}")       echo "F-keys always (Fn key does nothing)" ;;
        "T1:${T1_FNMODE_MEDIA_FN_FKEYS}")   echo "Media keys; F-keys while Fn is held" ;;
        "T1:${T1_FNMODE_FKEYS_FN_MEDIA}")   echo "F-keys; media keys while Fn is held" ;;
        "T1:${T1_FNMODE_MEDIA_ONLY}")       echo "Media keys always (Fn key does nothing)" ;;
        "T1:${T1_FNMODE_ESC_ONLY}")         echo "Escape key only" ;;
        "T2:${T2_MODE_ESC_ONLY}")           echo "Escape key only" ;;
        "T2:${T2_MODE_FKEYS}")              echo "F-keys (Fn switches to media keys)" ;;
        "T2:${T2_MODE_MEDIA}")              echo "Media keys (Fn switches to F-keys)" ;;
        "T2:${T2_MODE_OFF}")                echo "Touch Bar off" ;;
        *)                                  echo "unknown" ;;
    esac
}


fn_load_record() {
    local rec_path=""
    rec_state="none"
    rec_orig=""
    rec_temp=""
    [[ -f "$record_file" ]] || return 0
    rec_state="invalid"
    [[ -r "$record_file" ]] || return 0
    {
        IFS= read -r rec_path
        IFS= read -r rec_orig
        IFS= read -r rec_temp
    } < "$record_file"
    # The record must describe exactly the attribute detected on this machine.
    [[ "$rec_path" == "$attr_file" ]] || return 0
    fn_is_valid_mode "$rec_orig" || return 0
    fn_is_valid_mode "$rec_temp" || return 0
    rec_state="valid"
}


fn_clear_record() {
    rm -f "$record_file" 2>/dev/null
}


fn_show_status() {
    local curr_mode=""
    local default_mode=""
    echo ""
    echo "Touch Bar driver found: ${tb_kind} MacBook"
    echo "Settings file:          ${attr_file}"
    echo ""
    if curr_mode="$(fn_read_mode_file "$attr_file")"; then
        echo "Current mode:   ${curr_mode} = $(fn_mode_desc "$curr_mode")"
    else
        echo "Current mode:   could not be read"
    fi
    if default_mode="$(fn_read_mode_file "$default_file")"; then
        echo "Driver default: ${default_mode} = $(fn_mode_desc "$default_mode")"
    fi
    echo ""
    if [[ -w "$attr_file" ]]; then
        echo "You can change the mode without an administrator password."
    else
        echo "Changing the mode will ask for your administrator (sudo) password."
    fi
    case "$rec_state" in
        valid)
            echo ""
            if [[ "$curr_mode" == "$rec_temp" ]]; then
                echo "NOTICE: An Fn-key press was interrupted, leaving a temporary mode behind."
                echo "        The mode before that was: ${rec_orig} = $(fn_mode_desc "$rec_orig")"
            else
                echo "NOTICE: A leftover Fn-key record exists, but the mode has changed"
                echo "        since then, so there is nothing to undo."
            fi
            ;;
        invalid)
            echo ""
            echo "NOTICE: A leftover Fn-key record exists but could not be understood."
            echo "        It will be ignored: ${record_file}"
            ;;
    esac
}


fn_write_mode() {
    local new_mode="$1"
    local post_mode=""
    echo ""
    if [[ -w "$attr_file" ]]; then
        printf '%s\n' "$new_mode" > "$attr_file" 2>/dev/null
    else
        echo "Administrator rights are needed to change this setting."
        used_sudo="true"
        printf '%s\n' "$new_mode" | sudo tee "$attr_file" > /dev/null
    fi
    post_mode="$(fn_read_mode_file "$attr_file")"
    if [[ "$post_mode" == "$new_mode" ]]; then
        echo "Done. Touch Bar mode is now: ${new_mode} = $(fn_mode_desc "$new_mode")"
        echo "(This lasts until the next reboot or driver reload.)"
        return 0
    fi
    echo "ERROR: The mode could not be changed."
    echo "       Current mode is still: ${post_mode:-unreadable}"
    return 1
}


fn_set_mode() {
    # A deliberate choice by the user makes any leftover record obsolete.
    fn_write_mode "$1" || return 1
    fn_clear_record
    return 0
}


fn_reset_from_record() {
    local curr_mode=""
    case "$rec_state" in
        none)
            echo ""
            echo "No interrupted Fn-key swap was found. Nothing was changed."
            echo "To pick a mode yourself, run this command again with no options."
            return 0
            ;;
        invalid)
            echo ""
            echo "The leftover Fn-key record could not be understood. Nothing was changed."
            echo "To pick a mode yourself, run this command again with no options."
            return 1
            ;;
    esac
    curr_mode="$(fn_read_mode_file "$attr_file")"
    if [[ "$curr_mode" != "$rec_temp" ]]; then
        echo ""
        echo "The mode has changed since the Fn-key press was interrupted,"
        echo "so there is nothing to undo. Removing the leftover record."
        fn_clear_record
        return 0
    fi
    fn_write_mode "$rec_orig" || return 1
    fn_clear_record
    return 0
}


fn_show_menu() {
    local curr_mode="$1"
    local default_mode=""
    local mode_num=0
    local marker=""
    default_mode="$(fn_read_mode_file "$default_file")"
    echo ""
    echo "What should the Touch Bar show?"
    echo ""
    for (( mode_num = 0; mode_num <= max_mode; mode_num++ )); do
        marker=""
        [[ "$mode_num" == "$default_mode" ]] && marker+="  [driver default]"
        [[ "$mode_num" == "$curr_mode" ]] && marker+="  <-- current"
        echo "  ${mode_num} = $(fn_mode_desc "$mode_num")${marker}"
    done
    if [[ "$rec_state" == "valid" && "$curr_mode" == "$rec_temp" ]]; then
        echo "  r = Repair: go back to mode ${rec_orig}, from before the interrupted Fn press"
    fi
    echo "  q = Quit without changing anything"
    echo ""
}


fn_interactive() {
    local curr_mode=""
    local answer=""
    local can_repair="false"
    curr_mode="$(fn_read_mode_file "$attr_file")"
    if [[ "$rec_state" == "valid" && "$curr_mode" == "$rec_temp" ]]; then
        can_repair="true"
    fi
    fn_show_menu "$curr_mode"
    while true; do
        if ! read -rp "Type a choice and press Enter (or just Enter to quit): " answer; then
            echo ""
            echo "No input received. Nothing was changed."
            return 0
        fi
        answer="${answer//[[:space:]]/}"
        case "$answer" in
            ""|q|Q|quit|exit)
                echo ""
                echo "Nothing was changed."
                return 0
                ;;
            r|R)
                if [[ "$can_repair" == "true" ]]; then
                    fn_reset_from_record
                    return $?
                fi
                ;;
        esac
        if fn_is_valid_mode "$answer"; then
            if [[ "$answer" == "$curr_mode" ]]; then
                echo ""
                echo "The Touch Bar is already in mode ${answer}. Nothing was changed."
                return 0
            fi
            fn_set_mode "$answer"
            return $?
        fi
        echo "  Sorry, '${answer}' is not one of the choices. Please try again."
    done
}


while (( $# )); do
    case "$1" in
        -h|--help)
            fn_show_help
            safe_shutdown 0
            ;;
        -V|--version)
            echo ""
            echo "toshy-touchbar version ${SCRIPT_VERSION}"
            safe_shutdown 0
            ;;
        -s|--status|-i|--info)
            action="status"
            shift
            ;;
        -r|--reset)
            action="reset"
            shift
            ;;
        [0-9])
            action="set"
            new_mode_arg="$1"
            shift
            ;;
        *)
            echo ""
            echo "Unknown option: '$1'"
            fn_show_help
            safe_shutdown 1
            ;;
    esac
done

if ! fn_detect_driver; then
    echo ""
    echo "No supported Touch Bar driver was found on this computer."
    echo ""
    echo "This tool is only for Apple MacBooks that have a Touch Bar:"
    echo "  T1 models (2016-2017) need the add-on 'apple-touchbar' driver."
    echo "  T2 models (2018-2020) need the 'hid-appletb-kbd' kernel driver."
    echo ""
    echo "If this is such a MacBook, the driver may not be installed or loaded."
    safe_shutdown 1
fi

fn_load_record

case "$action" in
    status)
        fn_show_status
        safe_shutdown 0
        ;;
    reset)
        fn_reset_from_record
        safe_shutdown $?
        ;;
    set)
        if ! fn_is_valid_mode "$new_mode_arg"; then
            echo ""
            echo "'${new_mode_arg}' is not a valid mode for this Touch Bar (0 to ${max_mode})."
            safe_shutdown 1
        fi
        fn_set_mode "$new_mode_arg"
        safe_shutdown $?
        ;;
esac

fn_show_status

# Without a terminal to type into, showing the status is all that can be done.
if [[ ! -t 0 ]]; then
    safe_shutdown 0
fi

fn_interactive
safe_shutdown $?

# End of file #
