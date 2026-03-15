#!/usr/bin/env bash
# scripts/bin/toshy-libinput.sh
#
# Toshy libinput Diagnostic Utility
# ----------------------------------
# Interactive tool for diagnosing libinput DWT (disable-while-typing)
# issues caused by the xwaykeyz keyboard grab (EVIOCGRAB).
#
# When xwaykeyz grabs the physical keyboard, libinput no longer sees
# keypresses from it, so DWT cannot pair the physical keyboard with
# the internal touchpad. The fix is a quirks file that marks the
# xwaykeyz virtual keyboard as "internal" so libinput can pair it
# with the touchpad for DWT.
#
# This tool helps verify whether:
#   - The virtual keyboard exists and is visible to libinput
#   - The quirks file is present and correctly formatted
#   - The quirk is actually being applied to the virtual keyboard
#   - The touchpad is recognized as internal
#   - DWT is enabled and has a valid keyboard to pair with


# ── Guards ────────────────────────────────────────────────────────────────────

if [[ ${EUID} -eq 0 ]]; then
    echo "This script must not be run as root (it uses elevated privileges internally)."
    exit 1
fi

if [[ -z "${USER}" ]] || [[ -z "${HOME}" ]]; then
    echo "\$USER and/or \$HOME environment variables are not set. We need them."
    exit 1
fi


# ── Colors ────────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
BLU='\033[0;34m'
MGN='\033[0;35m'
CYN='\033[0;36m'
BLD='\033[1m'
DIM='\033[2m'
RST='\033[0m'


# ── Constants ─────────────────────────────────────────────────────────────────

QUIRKS_DIR="/etc/libinput"
QUIRKS_FILE="${QUIRKS_DIR}/local-overrides.quirks"
VIRT_KBD_PATTERN="XWayKeyz (virtual)"
# Section name and content that Toshy would install
QUIRKS_SECTION_NAME="XWayKeyz Virtual Keyboard"
QUIRKS_MATCH_NAME="*(virtual) Keyboard"


# ── Privilege elevation detection ─────────────────────────────────────────────
# Matches the preference order in setup_toshy.py: sudo, doas, run0, sudo-rs

ELEV_CMD=""

detect_elev_cmd() {
    local known_cmds=("sudo" "doas" "run0" "sudo-rs")
    for cmd in "${known_cmds[@]}"; do
        if command -v "${cmd}" &>/dev/null; then
            ELEV_CMD="${cmd}"
            return 0
        fi
    done
    echo -e "${RED}ERROR:${RST} No privilege elevation command found."
    echo -e "       Looked for: ${known_cmds[*]}"
    echo -e "       Install one of these to use this tool."
    exit 1
}


# ── Safe exit with ticket invalidation ────────────────────────────────────────

safe_exit() {
    local exit_code="${1:-0}"

    # Only sudo and sudo-rs have a standard way to invalidate cached credentials
    if [[ "${ELEV_CMD}" == "sudo" ]] || [[ "${ELEV_CMD}" == "sudo-rs" ]]; then
        "${ELEV_CMD}" -k &>/dev/null
    fi

    echo
    exit "${exit_code}"
}

trap 'safe_exit 130' SIGINT
trap 'safe_exit 143' SIGTERM


# ── Read wrapper — 'q' quits from any prompt ─────────────────────────────────

read_or_quit() {
    # Usage: read_or_quit "prompt string" varname
    # Sets the named variable in the caller's scope.
    # If user enters 'q' or 'Q', exits the script cleanly.
    local prompt="$1"
    local varname="$2"
    local _input
    read -r -p "${prompt}" _input
    if [[ "${_input}" == "q" ]] || [[ "${_input}" == "Q" ]]; then
        echo
        echo -e "${DIM}Goodbye.${RST}"
        safe_exit 0
    fi
    printf -v "${varname}" '%s' "${_input}"
}


# ── Quirks file helpers ───────────────────────────────────────────────────────
# libinput treats a file containing only comments and blank lines as "empty"
# and raises a parsing error that disables ALL quirks globally. This is worse
# than the file not existing at all.

quirks_file_is_effectively_empty() {
    # Returns 0 (true) if file exists but has no uncommented non-blank lines.
    # Returns 1 (false) if file has active content or does not exist.
    [[ ! -f "${QUIRKS_FILE}" ]] && return 1
    # Strip comments and blank lines; if nothing remains, it's effectively empty
    if ! grep -qE '^[^#[:space:]]' "${QUIRKS_FILE}" 2>/dev/null; then
        return 0
    fi
    return 1
}

print_effectively_empty_warning() {
    echo -e "   ${RED}✗${RST} ${RED}${BLD}File is effectively EMPTY${RST} (only comments and/or blank lines)"
    echo -e "     ${RED}libinput treats this as a parse error that disables ALL quirks!${RST}"
    echo -e "     Either uncomment the entries or delete the file entirely."
}


# ── Dependency check ──────────────────────────────────────────────────────────

check_libinput_tools() {
    if ! command -v libinput &>/dev/null; then
        echo -e "${RED}ERROR:${RST} The 'libinput' command was not found."
        echo -e "       Install the ${BLD}libinput-tools${RST} package for your distro."
        echo
        echo -e "  Debian/Ubuntu:  sudo apt install libinput-tools"
        echo -e "  Fedora/RHEL:    sudo dnf install libinput-utils"
        echo -e "  Arch:           sudo pacman -S libinput"
        echo -e "  openSUSE:       sudo zypper install libinput-tools"
        echo
        exit 1
    fi
}


# ── Elevated privileges helper ────────────────────────────────────────────────
# Prompt for credentials up front. The first elevated command will trigger the
# password prompt from the elevation command itself — we just explain what's
# about to happen so the user isn't surprised.

ensure_elevated() {
    echo -e "${DIM}Some libinput commands require elevated privileges (via '${ELEV_CMD}').${RST}"
    echo -e "${DIM}You may be prompted for your password.${RST}"
    echo

    # Probe whether credentials are already cached (non-interactive check)
    local already_cached=false
    case "${ELEV_CMD}" in
        sudo|doas|sudo-rs)
            if "${ELEV_CMD}" -n true &>/dev/null; then
                already_cached=true
            fi
            ;;
        run0)
            if "${ELEV_CMD}" --no-ask-password true &>/dev/null; then
                already_cached=true
            fi
            ;;
    esac

    if ${already_cached}; then
        echo -e "${DIM}Credentials already cached. Proceeding.${RST}"
        echo
        return 0
    fi

    # Credentials not cached — alert the user, then do a real elevation to trigger the prompt
    echo -e "${BLD}${MGN}  ── PASSWORD REQUIRED TO CONTINUE ──${RST}"
    echo

    if ! "${ELEV_CMD}" true; then
        echo -e "${RED}ERROR:${RST} Could not obtain elevated privileges via '${ELEV_CMD}'."
        safe_exit 1
    fi
}


# ── Device listing ────────────────────────────────────────────────────────────
# Parse `libinput list-devices` into parallel arrays for interactive selection.
# We collect keyboards AND touchpads since both sides of the pairing matter.

# Global arrays populated by collect_devices()
declare -a DEV_NAMES=()
declare -a DEV_KERNELS=()
declare -a DEV_CAPS=()
declare -a DEV_DWT=()
declare -a DEV_GROUPS=()

collect_devices() {
    local raw
    raw="$("${ELEV_CMD}" libinput list-devices 2>/dev/null)"
    if [[ -z "${raw}" ]]; then
        echo -e "${RED}ERROR:${RST} 'libinput list-devices' returned no output."
        echo -e "       Is the libinput-tools package installed and working?"
        return 1
    fi

    # Reset arrays
    DEV_NAMES=()
    DEV_KERNELS=()
    DEV_CAPS=()
    DEV_DWT=()
    DEV_GROUPS=()

    local name="" kernel="" caps="" dwt="" group=""

    while IFS= read -r line; do
        # Device blocks are separated by blank lines
        if [[ -z "${line}" ]]; then
            # End of a device block — store if it's a keyboard or touchpad/pointer
            if [[ -n "${name}" ]]; then
                if [[ "${caps}" == *keyboard* ]] || [[ "${caps}" == *pointer* ]]; then
                    DEV_NAMES+=("${name}")
                    DEV_KERNELS+=("${kernel}")
                    DEV_CAPS+=("${caps}")
                    DEV_DWT+=("${dwt}")
                    DEV_GROUPS+=("${group}")
                fi
            fi
            name="" kernel="" caps="" dwt="" group=""
            continue
        fi

        # Parse fields (libinput output uses colon-space-aligned values)
        if [[ "${line}" =~ ^Device:\ +(.*) ]]; then
            name="${BASH_REMATCH[1]}"
        elif [[ "${line}" =~ ^Kernel:\ +(.*) ]]; then
            kernel="${BASH_REMATCH[1]}"
        elif [[ "${line}" =~ ^Capabilities:\ +(.*) ]]; then
            caps="${BASH_REMATCH[1]}"
        elif [[ "${line}" =~ ^Disable-w-typing:\ +(.*) ]]; then
            dwt="${BASH_REMATCH[1]}"
        elif [[ "${line}" =~ ^Group:\ +(.*) ]]; then
            group="${BASH_REMATCH[1]}"
        fi
    done <<< "${raw}"

    # Handle final device block (no trailing blank line)
    if [[ -n "${name}" ]]; then
        if [[ "${caps}" == *keyboard* ]] || [[ "${caps}" == *pointer* ]]; then
            DEV_NAMES+=("${name}")
            DEV_KERNELS+=("${kernel}")
            DEV_CAPS+=("${caps}")
            DEV_DWT+=("${dwt}")
            DEV_GROUPS+=("${group}")
        fi
    fi

    if [[ ${#DEV_NAMES[@]} -eq 0 ]]; then
        echo -e "${YLW}No keyboard or pointer/touchpad devices found.${RST}"
        return 1
    fi

    return 0
}


show_device_list() {
    echo
    echo -e "${BLD}Keyboards and pointer/touchpad devices visible to libinput:${RST}"
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────${RST}"
    printf "  ${BLD}%-4s  %-50s  %-22s  %-12s  %-8s${RST}\n" \
        "#" "Device Name" "Kernel Node" "Capabilities" "DWT"
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────${RST}"

    local i
    for i in "${!DEV_NAMES[@]}"; do
        local num=$(( i + 1 ))
        local name="${DEV_NAMES[$i]}"
        local kern="${DEV_KERNELS[$i]}"
        local caps="${DEV_CAPS[$i]}"
        local dwt="${DEV_DWT[$i]}"

        # Highlight the xwaykeyz virtual keyboard
        local color="${RST}"
        if [[ "${name}" == *"${VIRT_KBD_PATTERN}"* ]]; then
            color="${CYN}"
        fi

        # Highlight touchpads
        if [[ "${caps}" == *pointer* ]] && [[ "${dwt}" != "n/a" ]]; then
            color="${GRN}"
        fi

        # Truncate long names
        local display_name="${name}"
        if [[ ${#display_name} -gt 50 ]]; then
            display_name="${display_name:0:47}..."
        fi

        printf "  ${color}%-4s  %-50s  %-22s  %-12s  %-8s${RST}\n" \
            "${num}" "${display_name}" "${kern}" "${caps}" "${dwt}"
    done

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────${RST}"
    echo -e "  ${CYN}Cyan${RST} = XWayKeyz virtual keyboard    ${GRN}Green${RST} = Touchpad with DWT support"
    echo
}


# ── Device selection prompt ───────────────────────────────────────────────────

# Prompt user to pick a device number. Sets SELECTED_IDX on success.
SELECTED_IDX=-1

select_device() {
    local prompt_msg="${1:-Select a device number}"
    local max=${#DEV_NAMES[@]}

    while true; do
        local choice
        read_or_quit "${prompt_msg} (1-${max}, or 'q' to quit, 'b' for back): " choice
        if [[ "${choice}" == "b" ]] || [[ "${choice}" == "B" ]]; then
            SELECTED_IDX=-1
            return 1
        fi
        if [[ "${choice}" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= max )); then
            SELECTED_IDX=$(( choice - 1 ))
            return 0
        fi
        echo -e "${YLW}Invalid choice. Enter a number from 1 to ${max}, 'q' to quit, or 'b' to go back.${RST}"
    done
}


# ── Quirks check for a device ────────────────────────────────────────────────

do_check_quirks() {
    show_device_list
    if ! select_device "Check quirks for device"; then
        return
    fi

    local kern="${DEV_KERNELS[$SELECTED_IDX]}"
    local name="${DEV_NAMES[$SELECTED_IDX]}"

    echo
    echo -e "${BLD}Quirks for: ${CYN}${name}${RST}"
    echo -e "${BLD}Kernel node: ${DIM}${kern}${RST}"
    echo

    if quirks_file_is_effectively_empty; then
        print_effectively_empty_warning
        echo
        echo -e "  ${DIM}The query below will fail because libinput cannot load any quirks.${RST}"
        echo
    fi

    local output
    output="$("${ELEV_CMD}" libinput quirks list "${kern}" 2>&1)"

    if [[ -z "${output}" ]]; then
        echo -e "  ${YLW}(no quirks matched for this device)${RST}"
    else
        echo "${output}" | while IFS= read -r line; do
            # Highlight the key finding
            if [[ "${line}" == *"AttrKeyboardIntegration=internal"* ]]; then
                echo -e "  ${GRN}${BLD}${line}${RST}  ← keyboard marked as internal"
            elif [[ "${line}" == *"AttrKeyboardIntegration=external"* ]]; then
                echo -e "  ${RED}${line}${RST}  ← keyboard marked as EXTERNAL"
            else
                echo "  ${line}"
            fi
        done
    fi
    echo
}


# ── Verbose quirks check ─────────────────────────────────────────────────────

do_check_quirks_verbose() {
    show_device_list
    if ! select_device "Verbose quirks for device"; then
        return
    fi

    local kern="${DEV_KERNELS[$SELECTED_IDX]}"
    local name="${DEV_NAMES[$SELECTED_IDX]}"

    echo
    echo -e "${BLD}Verbose quirks matching for: ${CYN}${name}${RST}"
    echo -e "${BLD}Kernel node: ${DIM}${kern}${RST}"
    echo
    echo -e "${DIM}This shows every quirks file and section libinput tried to match.${RST}"
    echo -e "${DIM}Look for 'is full match' to see which sections applied.${RST}"
    echo

    if quirks_file_is_effectively_empty; then
        print_effectively_empty_warning
        echo
        echo -e "  ${DIM}The query below will fail because libinput cannot load any quirks.${RST}"
        echo
    fi

    "${ELEV_CMD}" libinput quirks list --verbose "${kern}" 2>&1 | while IFS= read -r line; do
        if [[ "${line}" == *"is full match"* ]]; then
            echo -e "  ${GRN}${BLD}${line}${RST}"
        elif [[ "${line}" == *"property added"* ]]; then
            echo -e "  ${CYN}${line}${RST}"
        elif [[ "${line}" == *"wants"*"but we don't have"* ]]; then
            echo -e "  ${DIM}${line}${RST}"
        elif [[ "${line}" == *"matches for"* ]]; then
            echo -e "  ${YLW}${line}${RST}"
        else
            echo "  ${line}"
        fi
    done
    echo
}


# ── Quick DWT diagnosis ──────────────────────────────────────────────────────

do_quick_diagnosis() {
    echo
    echo -e "${BLD}${BLU}═══ Quick DWT Diagnosis ═══${RST}"
    echo

    local found_virt_kbd=false
    local virt_kbd_idx=-1
    local found_touchpad=false
    local touchpad_indices=()

    # Find the virtual keyboard and touchpads
    for i in "${!DEV_NAMES[@]}"; do
        if [[ "${DEV_NAMES[$i]}" == *"${VIRT_KBD_PATTERN}"* ]]; then
            found_virt_kbd=true
            virt_kbd_idx=$i
        fi
        # A touchpad has pointer capability and DWT is not "n/a"
        if [[ "${DEV_CAPS[$i]}" == *pointer* ]] && [[ "${DEV_DWT[$i]}" != "n/a" ]]; then
            found_touchpad=true
            touchpad_indices+=("$i")
        fi
    done

    # ── Step 1: Is xwaykeyz running and virtual keyboard visible? ─────────

    echo -e "${BLD}1. XWayKeyz virtual keyboard${RST}"
    if ${found_virt_kbd}; then
        echo -e "   ${GRN}✓${RST} Found: ${CYN}${DEV_NAMES[$virt_kbd_idx]}${RST}"
        echo -e "     Kernel node: ${DEV_KERNELS[$virt_kbd_idx]}"
    else
        echo -e "   ${RED}✗${RST} NOT FOUND — Is xwaykeyz / Toshy config service running?"
        echo -e "     Try: toshy-services-status"
        echo -e "     The virtual keyboard only exists while xwaykeyz is active."
        echo
        echo -e "   ${YLW}Remaining checks will be limited without the virtual keyboard.${RST}"
    fi
    echo

    # ── Step 2: Is the quirks file present? ───────────────────────────────

    echo -e "${BLD}2. Quirks file${RST}"
    if [[ ! -f "${QUIRKS_FILE}" ]]; then
        echo -e "   ${RED}✗${RST} File NOT found: ${QUIRKS_FILE}"
        echo -e "     DWT will not work for the xwaykeyz virtual keyboard without this file."
    elif quirks_file_is_effectively_empty; then
        echo -e "   ${YLW}~${RST} File exists: ${QUIRKS_FILE}"
        print_effectively_empty_warning
    else
        echo -e "   ${GRN}✓${RST} File exists: ${QUIRKS_FILE}"

        # Check if it contains our section (uncommented)
        if grep -qE "^[^#]*${QUIRKS_SECTION_NAME}" "${QUIRKS_FILE}" 2>/dev/null; then
            echo -e "   ${GRN}✓${RST} Contains active [${QUIRKS_SECTION_NAME}] section"
        elif grep -qE '^[^#]*AttrKeyboardIntegration=internal' "${QUIRKS_FILE}" 2>/dev/null; then
            echo -e "   ${YLW}~${RST} Contains an active internal keyboard quirk (different section name)"
        else
            echo -e "   ${RED}✗${RST} File has content but NO active xwaykeyz quirk entry"
            echo -e "     (Entries may be commented out)"
        fi

        # Validate parsing
        local validate_out
        validate_out="$("${ELEV_CMD}" libinput quirks validate 2>&1)"
        if [[ $? -eq 0 ]] && [[ -z "${validate_out}" ]]; then
            echo -e "   ${GRN}✓${RST} Quirks file validates OK (no parsing errors)"
        else
            echo -e "   ${RED}✗${RST} PARSING ERRORS detected — this disables ALL quirks!"
            echo -e "     ${RED}${validate_out}${RST}"
        fi
    fi
    echo

    # ── Step 3: Is the quirk actually applied to the virtual keyboard? ────

    echo -e "${BLD}3. Quirk applied to virtual keyboard${RST}"
    if ${found_virt_kbd}; then
        local vkbd_kern="${DEV_KERNELS[$virt_kbd_idx]}"
        local quirk_out
        quirk_out="$("${ELEV_CMD}" libinput quirks list "${vkbd_kern}" 2>&1)"

        if [[ "${quirk_out}" == *"AttrKeyboardIntegration=internal"* ]]; then
            echo -e "   ${GRN}✓${RST} Virtual keyboard IS marked as internal"
        elif [[ "${quirk_out}" == *"AttrKeyboardIntegration=external"* ]]; then
            echo -e "   ${RED}✗${RST} Virtual keyboard is marked as EXTERNAL"
        elif [[ -z "${quirk_out}" ]]; then
            echo -e "   ${RED}✗${RST} No quirks matched — virtual keyboard has NO integration tag"
            echo -e "     libinput will treat it as external (default for virtual devices)"
        else
            echo -e "   ${YLW}~${RST} Quirks found but no AttrKeyboardIntegration:"
            echo "     ${quirk_out}"
        fi
    else
        echo -e "   ${DIM}(skipped — virtual keyboard not found)${RST}"
    fi
    echo

    # ── Step 4: Touchpad status ───────────────────────────────────────────

    echo -e "${BLD}4. Touchpad(s) with DWT support${RST}"
    if ${found_touchpad}; then
        for tp_idx in "${touchpad_indices[@]}"; do
            local tp_name="${DEV_NAMES[$tp_idx]}"
            local tp_kern="${DEV_KERNELS[$tp_idx]}"
            local tp_dwt="${DEV_DWT[$tp_idx]}"
            local tp_group="${DEV_GROUPS[$tp_idx]}"

            echo -e "   ${GRN}Found:${RST} ${tp_name}"
            echo -e "     Kernel: ${tp_kern}   DWT setting: ${tp_dwt}   Group: ${tp_group}"

            # Check if the touchpad is recognized as internal
            local tp_quirk_out
            tp_quirk_out="$("${ELEV_CMD}" libinput quirks list "${tp_kern}" 2>&1)"
            if [[ -z "${tp_quirk_out}" ]]; then
                echo -e "     ${DIM}No device-specific quirks (relies on auto-detection for internal/external)${RST}"
            else
                echo -e "     Quirks: ${tp_quirk_out}"
            fi
        done
    else
        echo -e "   ${DIM}No touchpads with DWT support found.${RST}"
        echo -e "   ${DIM}(This is normal for desktops or if no touchpad is present.)${RST}"
    fi
    echo

    # ── Step 5: Count internal keyboards (>3 breaks pairing) ──────────────

    echo -e "${BLD}5. Internal keyboard count${RST}"
    local internal_count=0
    local internal_names=()

    for i in "${!DEV_NAMES[@]}"; do
        if [[ "${DEV_CAPS[$i]}" != *keyboard* ]]; then
            continue
        fi
        local kern="${DEV_KERNELS[$i]}"
        local q_out
        q_out="$("${ELEV_CMD}" libinput quirks list "${kern}" 2>&1)"

        if [[ "${q_out}" == *"AttrKeyboardIntegration=internal"* ]]; then
            internal_count=$(( internal_count + 1 ))
            internal_names+=("${DEV_NAMES[$i]}")
        fi
    done

    # Also check for keyboards whose bus type makes them implicitly internal
    # (PS/2 / serial keyboards are tagged internal by the system quirks)
    # We can't easily detect this without verbose output, so just report what
    # the quirks tool explicitly reports.

    if [[ ${internal_count} -eq 0 ]]; then
        echo -e "   ${YLW}!${RST} No keyboards explicitly marked as internal"
        echo -e "     ${DIM}(Note: PS/2 keyboards are implicitly internal via system quirks,${RST}"
        echo -e "     ${DIM} but may not show up here. Use verbose quirks check to verify.)${RST}"
    elif [[ ${internal_count} -le 3 ]]; then
        echo -e "   ${GRN}✓${RST} ${internal_count} keyboard(s) marked internal (≤3 is OK for DWT pairing)"
        for iname in "${internal_names[@]}"; do
            echo -e "     - ${iname}"
        done
    else
        echo -e "   ${RED}✗${RST} ${internal_count} keyboards marked internal (>3 BREAKS DWT pairing!)"
        for iname in "${internal_names[@]}"; do
            echo -e "     - ${iname}"
        done
        echo -e "     ${RED}libinput gives up on pairing when more than 3 keyboards match.${RST}"
    fi
    echo

    # ── Summary ───────────────────────────────────────────────────────────

    echo -e "${BLD}${BLU}═══ Summary ═══${RST}"
    echo
    if ${found_virt_kbd} && [[ -f "${QUIRKS_FILE}" ]]; then
        local vkbd_kern="${DEV_KERNELS[$virt_kbd_idx]}"
        local vk_quirk
        vk_quirk="$("${ELEV_CMD}" libinput quirks list "${vkbd_kern}" 2>&1)"
        if [[ "${vk_quirk}" == *"AttrKeyboardIntegration=internal"* ]] && ${found_touchpad}; then
            echo -e "  ${GRN}${BLD}DWT pairing looks GOOD.${RST}"
            echo -e "  The virtual keyboard is internal, touchpad is present, and quirks validate."
            echo
            echo -e "  ${DIM}To fully confirm DWT is engaging, use option 7 from the main menu${RST}"
            echo -e "  ${DIM}to run 'libinput debug-events' and watch for touchpad suppression.${RST}"
        else
            echo -e "  ${YLW}${BLD}DWT pairing is INCOMPLETE.${RST}"
            echo -e "  Review the individual checks above for what is missing."
        fi
    elif ! ${found_virt_kbd}; then
        echo -e "  ${YLW}${BLD}Cannot fully diagnose — xwaykeyz virtual keyboard not found.${RST}"
        echo -e "  Start Toshy services first, then re-run this check."
    else
        echo -e "  ${RED}${BLD}DWT quirk is NOT installed.${RST}"
        echo -e "  The quirks file is missing or does not contain the xwaykeyz entry."
    fi
    echo
}


# ── Show quirks file contents ─────────────────────────────────────────────────

do_show_quirks_file() {
    echo
    echo -e "${BLD}Quirks file: ${DIM}${QUIRKS_FILE}${RST}"
    echo

    if [[ ! -f "${QUIRKS_FILE}" ]]; then
        echo -e "  ${YLW}File does not exist.${RST}"
        echo
        echo -e "  Expected location: ${QUIRKS_FILE}"
        echo -e "  The directory ${QUIRKS_DIR}/ may also need to be created."
        echo
        echo -e "  For DWT with xwaykeyz, the file should contain:"
        echo
        echo -e "  ${DIM}[${QUIRKS_SECTION_NAME}]${RST}"
        echo -e "  ${DIM}MatchUdevType=keyboard${RST}"
        echo -e "  ${DIM}MatchName=${QUIRKS_MATCH_NAME}${RST}"
        echo -e "  ${DIM}AttrKeyboardIntegration=internal${RST}"
    else
        echo -e "  ${DIM}─── file contents ───${RST}"
        # Show with line numbers for easy reference
        local lineno=0
        while IFS= read -r line; do
            lineno=$(( lineno + 1 ))
            # Highlight section headers
            if [[ "${line}" =~ ^\[.*\] ]]; then
                printf "  ${BLU}%3d│${RST} ${BLD}%s${RST}\n" "${lineno}" "${line}"
            elif [[ "${line}" == *"AttrKeyboardIntegration"* ]]; then
                printf "  ${BLU}%3d│${RST} ${GRN}%s${RST}\n" "${lineno}" "${line}"
            elif [[ "${line}" =~ ^# ]] || [[ -z "${line}" ]]; then
                printf "  ${BLU}%3d│${RST} ${DIM}%s${RST}\n" "${lineno}" "${line}"
            else
                printf "  ${BLU}%3d│${RST} %s\n" "${lineno}" "${line}"
            fi
        done < "${QUIRKS_FILE}"
        echo -e "  ${DIM}─── end of file ─────${RST}"

        if quirks_file_is_effectively_empty; then
            echo
            echo -e "  ${RED}${BLD}WARNING:${RST} All entries are commented out or the file is blank."
            echo -e "  ${RED}libinput treats this as an EMPTY file — a parsing error that${RST}"
            echo -e "  ${RED}disables ALL quirks globally (including system vendor quirks).${RST}"
            echo -e "  ${RED}Either uncomment the entries or delete the file entirely.${RST}"
        fi
    fi
    echo
}


# ── Validate quirks file ─────────────────────────────────────────────────────

do_validate_quirks() {
    echo
    echo -e "${BLD}Validating all quirks files...${RST}"
    echo

    # Check for the effectively-empty case first, since the libinput error
    # message ("is an empty file") is confusing when the file has comments in it
    if quirks_file_is_effectively_empty; then
        echo -e "  ${RED}✗ ${QUIRKS_FILE}${RST}"
        echo -e "  ${RED}  File exists but contains only comments and/or blank lines.${RST}"
        echo -e "  ${RED}  libinput considers this an empty file — a parsing error that${RST}"
        echo -e "  ${RED}  disables ALL quirks globally (including system vendor quirks).${RST}"
        echo
        echo -e "  ${YLW}Fix: Either uncomment the entries or delete the file entirely.${RST}"
        echo
        return
    fi

    local output
    output="$("${ELEV_CMD}" libinput quirks validate 2>&1)"
    local rc=$?

    if [[ ${rc} -eq 0 ]] && [[ -z "${output}" ]]; then
        echo -e "  ${GRN}✓ All quirks files parsed successfully — no errors.${RST}"
    else
        echo -e "  ${RED}✗ Parsing errors detected!${RST}"
        echo -e "  ${RED}  A parsing error disables ALL quirks (not just the broken one).${RST}"
        echo
        echo "${output}" | while IFS= read -r line; do
            echo -e "  ${RED}${line}${RST}"
        done
    fi
    echo
}


# ── Live DWT test ─────────────────────────────────────────────────────────────

do_live_dwt_test() {
    echo
    echo -e "${BLD}${BLU}═══ Live DWT Test ═══${RST}"
    echo
    echo -e "This will run ${BLD}libinput debug-events${RST} so you can observe DWT in real time."
    echo
    echo -e "What to look for:"
    echo -e "  1. Type on your keyboard — you should see ${CYN}KEYBOARD_KEY${RST} events"
    echo -e "  2. Touch/move on the touchpad — you should see ${CYN}POINTER_MOTION${RST} events"
    echo -e "  3. Type while touching the touchpad — if DWT is working, the"
    echo -e "     pointer events should ${GRN}stop appearing${RST} while you type"
    echo
    echo -e "  ${YLW}Press Ctrl+C to stop and return to the menu.${RST}"
    echo

    local choice
    read_or_quit "Press Enter to start (or 'q' to quit, 'b' for back): " choice
    if [[ "${choice}" == "b" ]] || [[ "${choice}" == "B" ]]; then
        return
    fi

    echo
    echo -e "${DIM}Starting libinput debug-events...${RST}"
    echo

    # Run debug-events, let the user Ctrl+C out of it
    "${ELEV_CMD}" libinput debug-events 2>&1 || true
    echo
}


# ── Main menu ─────────────────────────────────────────────────────────────────

show_menu() {
    echo
    echo -e "${BLD}${BLU}Toshy libinput Diagnostic Utility${RST}"
    echo -e "${DIM}─────────────────────────────────────────────${RST}"
    echo -e "  ${BLD}1${RST}  List keyboards & touchpads"
    echo -e "  ${BLD}2${RST}  Check quirks for a device"
    echo -e "  ${BLD}3${RST}  Check quirks for a device (verbose)"
    echo -e "  ${BLD}4${RST}  Quick DWT diagnosis (recommended)"
    echo -e "  ${BLD}5${RST}  Show quirks file contents"
    echo -e "  ${BLD}6${RST}  Validate quirks files"
    echo -e "  ${BLD}7${RST}  Live DWT test (libinput debug-events)"
    echo -e "${DIM}─────────────────────────────────────────────${RST}"
}


main() {
    check_libinput_tools
    detect_elev_cmd
    ensure_elevated
    collect_devices

    while true; do
        show_menu
        local opt
        read_or_quit "  Choose an option (or 'q' to quit): " opt
        case "${opt}" in
            1)  show_device_list ;;
            2)  do_check_quirks ;;
            3)  do_check_quirks_verbose ;;
            4)  do_quick_diagnosis ;;
            5)  do_show_quirks_file ;;
            6)  do_validate_quirks ;;
            7)  do_live_dwt_test ;;
            *)
                echo -e "  ${YLW}Invalid choice.${RST}"
                ;;
        esac
    done
}


main "$@"

# safe_exit is not reachable here (loop is infinite, 'q' calls safe_exit via
# read_or_quit), but just in case some future change breaks that invariant:
safe_exit 0

# End of file #
