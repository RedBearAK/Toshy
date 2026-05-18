#!/usr/bin/env bash

# scripts/set-mac-startup-sound-volume.sh

# shellcheck disable=SC2034
VERSION='20260515'


# This script is intended to be run with elevated privileges (root/superuser) on
# Apple Intel Mac models. It uses 'efivar' to modify the volume or mute/unmute the
# Mac startup sound (aka, the "boot chime").

# Author: https://github.com/RedBearAK/
# Email:  64876997+RedBearAK@users.noreply.github.com


echo    # blank line to start things off

# Function to exit with a blank line for cleaner output
clean_exit() {
    echo
    exit "${1:-0}"  # Default to exit code 0 if not specified
}

# Allow the version to print out without running as root/superuser
if [ $# -eq 1 ]; then
    case "${1,,}" in  # Convert to lowercase for case-insensitive matching

        "--version"|"version")
            echo "Script version: ${VERSION}"
            echo
            echo "All other options/commands require elevated privileges (root/superuser)"
            clean_exit 0
            ;;

    esac
fi

# Ensure that we are root/superuser so later commands will succeed
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root/superuser"
    echo
    exit 1
fi

# Check if this is an Apple system
if [ -f /sys/class/dmi/id/sys_vendor ]; then
    VENDOR=$(cat /sys/class/dmi/id/sys_vendor)
    if [[ "$VENDOR" != *"Apple"* ]]; then
        echo "Warning: This does not appear to be an Apple system."
        echo "System vendor: $VENDOR"
        echo "This script is designed for Apple computers and will have no effect on other systems."
        echo
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            clean_exit 0
        fi
    fi
fi

# Check if this is an Intel Mac (not Apple Silicon or something unknown)
if [ -f /proc/cpuinfo ] && grep -q "GenuineIntel" /proc/cpuinfo; then
    : # Intel Mac, proceed
elif [[ "$(uname -m)" == "arm64" ]] || [[ "$(uname -m)" == "aarch64" ]]; then
    echo "Warning: This appears to be an Apple Silicon Mac."
    echo "This script was designed for Intel-based Macs and likely won't work on Apple Silicon."
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        clean_exit 0
    fi
else
    echo "Warning: Unknown processor architecture: $(uname -m)"
    echo "This script was designed for Intel-based Macs and may not work on this system."
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        clean_exit 0
    fi
fi

# Function to display usage
usage() {
    SCRIPT_NAME=$(basename "$0")
    cat << EOF
Usage:
    $SCRIPT_NAME [-b|-d|-p|-x] <volume>
    $SCRIPT_NAME info
    $SCRIPT_NAME mute
    $SCRIPT_NAME reset
    $SCRIPT_NAME unmute
    $SCRIPT_NAME --version | version

Special commands:
    info:    Display current startup volume setting
    mute:    Set the startup volume to muted
    reset:   Delete the EFI variable (simulate NVRAM/PRAM reset)
    unmute:  Restore previous startup volume (if preserved)

Format options:
    -b:  Binary       (e.g., "-b 01000000" or "01000000")
    -d:  Decimal      (e.g., "-d 64" or just "64")
    -p:  Percentage   (e.g., "-p 50" or "50%")
    -x:  Hexadecimal  (e.g., "-x 40" or "0x40")

Percent suffix:
    Any volume input ending with '%' is treated as a percentage
    regardless of the format flag (e.g., '60%' = 60 percent of max).
    Percentages map 0-100% onto the 0-127 volume byte range.
    Percentage input cannot set the chime to muted with an encoded
    volume level; use the 'mute' command for that.

Volume ranges:
    Binary:      00000000-01111111 (volume), 10000000-11111111 to mute^
    Decimal:     0-127       (volume level), 128-255 to mute^
    Hex:         00-7F       (volume level), 80-FF to mute^
    Percentage:  0-100       (volume only; use 'mute' command to mute)

^ Values of 129-255 preserve a volume level that 'unmute' will restore
EOF
    clean_exit 1
}

# Notify user if 'bc' command is not available
if ! command -v bc >/dev/null 2>&1; then
    echo "There is no 'bc' (basic calculator) command on this system. Cannot continue."
    echo
    echo "Try installing 'bc' package. Exiting..."
    clean_exit 0
fi

# Notify user if 'efivar' command is not available
if ! command -v efivar >/dev/null 2>&1; then
    echo "There is no 'efivar' command on this system. Cannot continue."
    echo
    echo "Try installing 'efivar' package. Exiting..."
    clean_exit 0
fi


# Helper: convert a 0-127 volume byte to percentage (rounded to nearest int)
volume_byte_to_percent() {
    local vol=$1
    awk "BEGIN {printf \"%.0f\", ($vol / 127.0) * 100}"
}

# Helper: convert a percentage (0-100, may be fractional) to a 0-127 volume byte
percent_to_volume_byte() {
    local pct=$1
    printf "%.0f" "$(echo "$pct * 127 / 100" | bc -l)"
}

# Helper: print the standard "out of range" error block
print_out_of_range_error() {
    local input_label=$1
    local input_value=$2
    echo "Error: Volume value ($input_label) $input_value out of range."
    echo "   Valid values:"
    echo "        0-127     (volume level, chime not muted)"
    echo "        128       (chime muted, no saved volume level)"
    echo "        129-255   (chime muted + saved volume level)"
    echo "See --help for full ranges."
}


# Helper: read current volume byte (decimal) from EFI; echo empty if unset.
get_current_volume_byte() {
    local raw
    raw=$(efivar -n "7c436110-ab2a-4bbb-a880-fe41995c9f82-SystemAudioVolume" -d 2>/dev/null)
    if [ -z "$raw" ]; then
        return
    fi
    echo "$raw" | awk '{print $NF}'
}

# Helper: return a human-readable state string for a decimal volume byte.
get_chime_state() {
    local vol=$1
    local preserved pct
    if [ "$vol" -eq 128 ]; then
        echo "Muted (no saved volume level)"
    elif [ "$vol" -gt 128 ] && [ "$vol" -le 255 ]; then
        preserved=$((vol & 0x7F))
        pct=$(volume_byte_to_percent "$preserved")
        echo "Muted (saved volume level: $preserved, ~${pct}%)"
    elif [ "$vol" -ge 0 ] && [ "$vol" -le 127 ]; then
        echo "Not muted (chime will play at startup)"
    else
        echo "Unknown / invalid value"
    fi
}

# Helper: return a percentage display string for a decimal volume byte.
get_chime_display_percent() {
    local vol=$1
    local preserved pct
    if [ "$vol" -eq 128 ]; then
        echo "N/A (muted, no saved level)"
    elif [ "$vol" -gt 128 ] && [ "$vol" -le 255 ]; then
        preserved=$((vol & 0x7F))
        pct=$(volume_byte_to_percent "$preserved")
        echo "~${pct}% (muted, preserved level)"
    elif [ "$vol" -ge 0 ] && [ "$vol" -le 127 ]; then
        pct=$(volume_byte_to_percent "$vol")
        echo "~${pct}% of max"
    else
        echo "N/A"
    fi
}

# Render a startup chime info block: title + Input (optional) + State + format
# representations. Used by all action outputs and the 'info' command.
#   $1 = title (e.g., "New startup chime info:")
#   $2 = volume byte as decimal, or empty for "Not set"
#   $3 = optional Input line (e.g., "80% (percent)") -- set actions only
render_chime_info_block() {
    local title=$1
    local vol=$2
    local input_desc=$3
    local state pct bin hex

    echo "$title"

    if [ -z "$vol" ]; then
        echo "  Not set (no EFI variable exists)"
        return
    fi

    state=$(get_chime_state "$vol")
    pct=$(get_chime_display_percent "$vol")
    bin=$(printf "%08d" "$(echo "obase=2; $vol" | bc)")
    hex=$(printf "0x%02x" "$vol")

    if [ -n "$input_desc" ]; then
        printf "  %-14s%s\n" "Input:" "$input_desc"
    fi
    printf "  %-14s%s\n" "State:" "$state"
    printf "  %-14s%s\n" "Binary:" "$bin"
    printf "  %-14s%s\n" "Decimal:" "$vol"
    printf "  %-14s%s\n" "Hex:" "$hex"
    printf "  %-14s%s\n" "Percentage:" "$pct"
}

# Write a decimal volume byte to the EFI variable, handling the immutable flag.
write_volume_byte() {
    local vol=$1
    local hex
    hex=$(printf "%02x" "$vol")
    chattr -i "/sys/firmware/efi/efivars/SystemAudioVolume-7c436110-ab2a-4bbb-a880-fe41995c9f82" 2>/dev/null
    # The '%b' format prevents shellcheck SC2059 (variable in printf string)
    printf '%b' "\x07\x00\x00\x00\x${hex}" > "/sys/firmware/efi/efivars/SystemAudioVolume-7c436110-ab2a-4bbb-a880-fe41995c9f82"
    chattr +i "/sys/firmware/efi/efivars/SystemAudioVolume-7c436110-ab2a-4bbb-a880-fe41995c9f82"
}

# Function to display info about current volume setting
show_info() {
    echo "SystemAudioVolume EFI Variable Information"
    echo "=========================================="

    # Check if the EFI variable exists
    if ! efivar -n "7c436110-ab2a-4bbb-a880-fe41995c9f82-SystemAudioVolume" -p >/dev/null 2>&1; then
        echo "Status: Not found"
        echo ""
        echo "The SystemAudioVolume EFI variable is not set."
        echo "This could mean:"
        echo "  - The system is using default volume settings"
        echo "  - This is not an Apple system"
        echo "  - NVRAM/PRAM has been reset"
        clean_exit 0
    fi

    echo "Status: Found and readable"
    echo ""

    # Display value via the central block helper
    local vol
    vol=$(get_current_volume_byte)
    render_chime_info_block "Current startup chime info:" "$vol"
    echo ""

    # Show metadata
    echo "EFI Variable Location:"
    echo "  /sys/firmware/efi/efivars/SystemAudioVolume-7c436110-ab2a-4bbb-a880-fe41995c9f82"
    if lsattr "/sys/firmware/efi/efivars/SystemAudioVolume-7c436110-ab2a-4bbb-a880-fe41995c9f82" 2>/dev/null | grep -q "i"; then
        echo "  Immutable flag: Set (protected from accidental modification)"
    else
        echo "  Immutable flag: Not set"
    fi
}


print_notice_of_low_volume_level() {
    local LOW_VOL=$1
    local LOW_PCT
    LOW_PCT=$(volume_byte_to_percent "$LOW_VOL")
    echo ""
    echo "================================================================"
    echo "                        ⚠️  NOTICE  ⚠️"
    echo "================================================================"
    echo ""
    echo "  The restored volume level ($LOW_VOL, ~${LOW_PCT}%) is below 40!"
    echo ""
    echo "  Depending on your Mac model, volume levels below 40 may be"
    echo "  INAUDIBLE or VERY QUIET during startup."
    echo ""
    echo "================================================================"
}


# Check for special commands first
if [ $# -eq 1 ]; then
    case "${1,,}" in  # Convert to lowercase for case-insensitive matching

        "info")
            show_info
            clean_exit 0
            ;;

        "mute")
            prev_vol=$(get_current_volume_byte)

            # Determine which volume level to preserve in the mute encoding.
            # Default to 64 (~50%) if there's no existing value or it's 0.
            if [ -z "$prev_vol" ]; then
                preserved=64
            else
                preserved=$((prev_vol & 0x7F))
                if [ "$preserved" -eq 0 ]; then
                    preserved=64
                fi
            fi
            new_vol=$((128 + preserved))

            write_volume_byte "$new_vol"

            render_chime_info_block "New startup chime info:" "$new_vol"
            echo "----------------------------------------------------------------"
            render_chime_info_block "Previous startup chime info:" "$prev_vol"
            echo "----------------------------------------------------------------"
            clean_exit 0
            ;;

        "reset")
            echo "Resetting SystemAudioVolume EFI variable."
            echo "----------------------------------------------------------------"

            prev_vol=$(get_current_volume_byte)

            # Remove the immutable flag before deleting
            chattr -i "/sys/firmware/efi/efivars/SystemAudioVolume-7c436110-ab2a-4bbb-a880-fe41995c9f82" 2>/dev/null

            # Delete the EFI variable
            if rm -f "/sys/firmware/efi/efivars/SystemAudioVolume-7c436110-ab2a-4bbb-a880-fe41995c9f82" 2>/dev/null; then
                echo "EFI variable successfully deleted."
            else
                # Alternative method using efivar
                if efivar -n "7c436110-ab2a-4bbb-a880-fe41995c9f82-SystemAudioVolume" -w < /dev/null 2>/dev/null; then
                    echo "EFI variable successfully reset using efivar."
                else
                    echo "Warning: Could not delete EFI variable. It may not exist."
                fi
            fi

            echo "----------------------------------------------------------------"
            render_chime_info_block "Previous startup chime info:" "$prev_vol"
            echo "----------------------------------------------------------------"
            echo "Note: The system will use the default volume on next boot."
            clean_exit 0
            ;;

        "unmute")
            prev_vol=$(get_current_volume_byte)

            if [ -z "$prev_vol" ]; then
                # No EFI variable yet -- create one at the default level
                new_vol=64
            elif [ "$prev_vol" -lt 128 ]; then
                # Already audible -- nothing to do; just show current info
                echo "System is not currently muted -- nothing to do."
                echo "----------------------------------------------------------------"
                render_chime_info_block "Current startup chime info:" "$prev_vol"
                echo "----------------------------------------------------------------"
                clean_exit 0
            else
                # Extract preserved volume from the mute encoding; default if 0
                new_vol=$((prev_vol & 0x7F))
                if [ "$new_vol" -eq 0 ]; then
                    new_vol=64
                fi
            fi

            write_volume_byte "$new_vol"

            render_chime_info_block "New startup chime info:" "$new_vol"
            echo "----------------------------------------------------------------"
            render_chime_info_block "Previous startup chime info:" "$prev_vol"
            echo "----------------------------------------------------------------"

            if [ "$new_vol" -lt 40 ]; then
                print_notice_of_low_volume_level "$new_vol"
            fi

            clean_exit 0
            ;;

    esac
fi

# Default format is decimal; FORMAT_EXPLICIT tracks whether user passed a flag
FORMAT="decimal"
FORMAT_EXPLICIT=""

# Parse options
while getopts "bdpx" opt; do
    case $opt in
        b) FORMAT="binary";  FORMAT_EXPLICIT="-b" ;;
        d) FORMAT="decimal"; FORMAT_EXPLICIT="-d" ;;
        p) FORMAT="percent"; FORMAT_EXPLICIT="-p" ;;
        x) FORMAT="hex";     FORMAT_EXPLICIT="-x" ;;
        *) usage ;;
    esac
done

# Shift to get the volume argument
shift $((OPTIND-1))

# Check if volume argument is provided
if [ $# -ne 1 ]; then
    usage
fi

INPUT_VALUE="$1"
VOLUME=0

# When no format flag is given, infer the format from the input's shape:
#   - ends with '%'         -> percent
#   - starts with '0x'/'0X' -> hex
#   - all 0/1, length >= 2, AND
#       length > 3 (4+ digit all-0/1 is outside the 0-255 decimal range), OR
#       starts with 0 (a leading-zero decimal is unusual)
#                           -> binary
#   - otherwise             -> decimal (the default)
# Explicit flags take precedence; '%' suffix combined with a non-'-p'
# flag is an error since it can't mean both things.
if [[ "$INPUT_VALUE" == *% ]]; then
    if [ -n "$FORMAT_EXPLICIT" ] && [ "$FORMAT_EXPLICIT" != "-p" ]; then
        echo "Error: Percent suffix '%' cannot be combined with $FORMAT_EXPLICIT flag."
        echo "       Use either '$INPUT_VALUE' alone, or '-p ${INPUT_VALUE%\%}'."
        clean_exit 1
    fi
    FORMAT="percent"
elif [ -z "$FORMAT_EXPLICIT" ]; then
    if [[ "$INPUT_VALUE" == 0x* ]] || [[ "$INPUT_VALUE" == 0X* ]]; then
        FORMAT="hex"
    elif [[ "$INPUT_VALUE" =~ ^[01]+$ ]] && [ ${#INPUT_VALUE} -ge 2 ]; then
        if [ ${#INPUT_VALUE} -gt 3 ] || [[ "$INPUT_VALUE" == 0* ]]; then
            FORMAT="binary"
        fi
    fi
fi

# Parse and validate based on format
case $FORMAT in

    binary)
        # Check if it's a valid binary number (only 0s and 1s)
        if ! [[ "$INPUT_VALUE" =~ ^[01]+$ ]]; then
            echo "Error: Invalid binary format. Use only 0 and 1 (e.g., 01000000)."
            clean_exit 1
        fi
        # Check if it's not more than 8 bits
        if [ ${#INPUT_VALUE} -gt 8 ]; then
            echo "Error: Binary value must be 8 bits or less."
            clean_exit 1
        fi
        # Convert binary to decimal
        VOLUME=$((2#$INPUT_VALUE))
        ;;

    decimal)
        # A leading zero on a decimal is never useful: if all digits are 0/1
        # it's binary input (use -b or rely on auto-detection), and otherwise
        # it's almost certainly a typo. Accept only '0' or a non-zero leading
        # digit followed by more digits.
        if ! [[ "$INPUT_VALUE" =~ ^(0|[1-9][0-9]*)$ ]]; then
            if [[ "$INPUT_VALUE" =~ ^0[0-9]+$ ]]; then
                echo "Error: Decimal input '$INPUT_VALUE' has a leading zero."
                echo "       For binary input, use -b or rely on auto-detect."
                echo "       For decimal, drop the leading zero (e.g., '${INPUT_VALUE#0}')."
            else
                echo "Error: Invalid decimal format. Use only digits 0-9 (e.g., 64)."
            fi
            clean_exit 1
        fi
        VOLUME=$INPUT_VALUE
        ;;

    hex)
        # Remove optional 0x prefix
        HEX_VALUE="${INPUT_VALUE#0x}"
        HEX_VALUE="${HEX_VALUE#0X}"

        # Check if it's a valid hex number
        if ! [[ "$HEX_VALUE" =~ ^[0-9A-Fa-f]+$ ]]; then
            echo "Error: Invalid hexadecimal format. Use only 0-9, A-F, a-f."
            clean_exit 1
        fi
        # Check if it's not more than 2 hex digits (1 byte)
        if [ ${#HEX_VALUE} -gt 2 ]; then
            echo "Error: Hexadecimal value must be 2 digits or less (one byte)."
            clean_exit 1
        fi
        # Convert hex to decimal
        VOLUME=$((16#$HEX_VALUE))
        ;;

    percent)
        # Strip optional '%' suffix
        PCT_VALUE="${INPUT_VALUE%\%}"

        # Allow integer or fractional values (e.g., 50, 50.5)
        if ! [[ "$PCT_VALUE" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            echo "Error: Invalid percentage format. Use 0-100 (e.g., 60 or 60% or 50.5%)."
            clean_exit 1
        fi

        # Range check (use bc for fractional comparison)
        if [ "$(echo "$PCT_VALUE < 0 || $PCT_VALUE > 100" | bc -l)" -eq 1 ]; then
            echo "Error: Percentage value ${PCT_VALUE}% out of range."
            echo "   Valid range: 0%-100%"
            echo "   Note: to mute the chime, use the 'mute' command instead."
            clean_exit 1
        fi

        # Convert to a 0-127 volume byte (rounded to nearest int)
        VOLUME=$(percent_to_volume_byte "$PCT_VALUE")
        ;;

esac

# Validate volume range
if [ "$VOLUME" -lt 0 ] || [ "$VOLUME" -gt 255 ]; then
    print_out_of_range_error "$FORMAT" "$INPUT_VALUE"
    clean_exit 1
fi

# Capture previous value, write new value, then display both info blocks
prev_vol=$(get_current_volume_byte)
write_volume_byte "$VOLUME"

render_chime_info_block "New startup chime info:" "$VOLUME" "$INPUT_VALUE ($FORMAT)"
echo "----------------------------------------------------------------"
render_chime_info_block "Previous startup chime info:" "$prev_vol"
echo "----------------------------------------------------------------"

# Footer note: explain mute-encoded values and point to 'unmute'
if [ "$VOLUME" -ge 128 ]; then
    echo "Note: Decimal value $VOLUME encodes mute with preserved volume level $((VOLUME & 0x7F))."
    echo "      Use the 'unmute' command to restore the chime to that level."
fi

if [ "$VOLUME" -lt 40 ]; then
    print_notice_of_low_volume_level "$VOLUME"
fi

clean_exit 0

# End of file #
