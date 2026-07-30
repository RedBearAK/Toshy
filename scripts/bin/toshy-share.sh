#!/usr/bin/env bash

# Share command output or a file, for getting logs out of machines where
# the clipboard is unavailable (fresh VMs, broken desktops, SSH-less boxes).
#
# Two modes:
#
#   PRIVATE (preferred, e.g. VM guest to host; no tools needed, uses bash's
#   built-in /dev/tcp; start a listener on the receiver first, such as
#   'nc -l 9999 > received.log'):
#       some-command 2>&1 | toshy-share --to 192.168.122.1:9999
#       toshy-share --to 192.168.122.1:9999 /path/to/logfile
#
#   PUBLIC paste services (prints a short URL to transcribe; tries several
#   services in order, since these come and go):
#       some-command 2>&1 | toshy-share
#       toshy-share /path/to/logfile
#
# NOTE: Public uploads can be read by anyone with the URL and are hosted by
# third parties with retention limits. Do not share secrets.

# shellcheck disable=SC2034
SCRIPT_VERSION='20260729'

print_help() {
    echo "Usage:"
    echo "  <command> 2>&1 | toshy-share                  (public paste URL)"
    echo "  toshy-share <file>                            (public paste URL)"
    echo "  <command> 2>&1 | toshy-share --to HOST:PORT   (private, to a listener)"
    echo "  toshy-share --to HOST:PORT <file>             (private, to a listener)"
    echo
    echo "For the private mode, start a listener on the receiving machine first:"
    echo "    nc -l PORT > received.log"
    echo "Public uploads are PUBLIC. Do not share secrets."
}

to_target=''
input_file=''

while [[ -n "${1:-}" ]]; do
    case "$1" in
        -h|--help)
            print_help
            exit 0
            ;;
        -t|--to)
            to_target="${2:-}"
            if [[ ! "$to_target" =~ ^[^:]+:[0-9]+$ ]]; then
                echo "ERROR: '--to' needs HOST:PORT (e.g. 192.168.122.1:9999)" >&2
                exit 1
            fi
            shift 2
            ;;
        *)
            if [[ ! -r "$1" ]]; then
                echo "ERROR: File not found or not readable: $1" >&2
                exit 1
            fi
            input_file="$1"
            shift
            ;;
    esac
done

if [[ -z "$input_file" && -t 0 ]]; then
    echo "ERROR: No file argument and no piped input." >&2
    echo >&2
    print_help >&2
    exit 1
fi

# ---------------- PRIVATE mode: bash /dev/tcp, zero dependencies ----------------
if [[ -n "$to_target" ]]; then
    to_host="${to_target%%:*}"
    to_port="${to_target##*:}"
    if [[ -n "$input_file" ]]; then
        if cat "$input_file" > "/dev/tcp/${to_host}/${to_port}"; then
            echo "Sent ${input_file} to ${to_target}" >&2
            exit 0
        fi
    else
        if cat > "/dev/tcp/${to_host}/${to_port}"; then
            echo "Sent piped input to ${to_target}" >&2
            exit 0
        fi
    fi
    echo "ERROR: Could not connect to ${to_target}." >&2
    echo "Is a listener running there? ('nc -l ${to_port} > received.log')" >&2
    exit 1
fi

# ---------------- PUBLIC mode: try paste services in order ----------------
echo "NOTE: Uploads are PUBLIC. Do not share secrets." >&2

# Stdin can only be consumed once, so buffer piped input to a temp file.
cleanup_tmp=''
if [[ -z "$input_file" ]]; then
    input_file="$(mktemp /tmp/toshy-share-XXXXXX)"
    cleanup_tmp="$input_file"
    cat > "$input_file"
fi

finish() {
    [[ -n "$cleanup_tmp" ]] && rm -f "$cleanup_tmp"
    exit "$1"
}

looks_like_url() {
    [[ "$1" =~ ^https?:// ]]
}

if command -v curl >/dev/null 2>&1; then
    for svc in "envs.sh:curl -sfF file=@FILE https://envs.sh" \
               "0x0.st:curl -sfF file=@FILE https://0x0.st" \
               "paste.rs:curl -sf --data-binary @FILE https://paste.rs" \
               "dpaste.org:curl -sfF content=<FILE https://dpaste.org/api/"; do
        svc_name="${svc%%:*}"
        svc_cmd="${svc#*:}"
        svc_cmd="${svc_cmd//FILE/$input_file}"
        result="$($svc_cmd 2>/dev/null)"
        result="${result//\"/}"     # dpaste wraps the URL in quotes
        if looks_like_url "$result"; then
            echo "$result"
            finish 0
        fi
        echo "(${svc_name} did not accept the upload; trying next...)" >&2
    done
fi

if command -v nc >/dev/null 2>&1; then
    result="$(nc termbin.com 9999 < "$input_file" 2>/dev/null | tr -d '\0')"
    if looks_like_url "$result"; then
        echo "$result"
        finish 0
    fi
fi

echo "ERROR: No paste service accepted the upload (or curl/nc are missing)." >&2
echo "Consider the private mode instead (works VM-to-host with no tools):" >&2
echo "    toshy-share --to <receiver-ip>:9999 ${cleanup_tmp:+$input_file}" >&2
echo "with 'nc -l 9999 > received.log' running on the receiver." >&2
[[ -n "$cleanup_tmp" ]] && echo "(Piped input was saved at: $input_file)" >&2
cleanup_tmp=''      # keep the buffered input for a retry
exit 1

# End of file #
