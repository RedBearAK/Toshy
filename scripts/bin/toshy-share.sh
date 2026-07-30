#!/usr/bin/env bash

# Share command output or a file via a public paste service, for getting
# logs out of machines where the clipboard is unavailable (fresh VMs,
# broken desktops, SSH-less boxes). Prints a short URL to transcribe.
#
#   some-command 2>&1 | toshy-share
#   toshy-share /path/to/logfile
#
# NOTE: Uploads are PUBLIC (anyone with the URL can read them) and are
# hosted by third parties with retention limits. Do not share secrets.

# shellcheck disable=SC2034
SCRIPT_VERSION='20260729'

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: <command> 2>&1 | toshy-share"
    echo "       toshy-share <file>"
    echo
    echo "Uploads to a public paste service and prints the URL."
    echo "Uploads are PUBLIC. Do not share secrets."
    exit 0
fi

input_file=''
if [[ -n "${1:-}" ]]; then
    if [[ ! -r "$1" ]]; then
        echo "ERROR: File not found or not readable: $1" >&2
        exit 1
    fi
    input_file="$1"
elif [[ -t 0 ]]; then
    echo "ERROR: No file argument and no piped input." >&2
    echo "Usage: <command> 2>&1 | toshy-share   (or: toshy-share <file>)" >&2
    exit 1
fi

echo "NOTE: Uploads are PUBLIC. Do not share secrets." >&2

# Preferred: curl to 0x0.st (returns a short URL, generous size limits).
if command -v curl >/dev/null 2>&1; then
    if [[ -n "$input_file" ]]; then
        curl -sF "file=@${input_file}" https://0x0.st && exit 0
    else
        curl -sF 'file=@-' https://0x0.st && exit 0
    fi
    echo "WARNING: Upload via curl to 0x0.st failed. Trying termbin..." >&2
fi

# Fallback: netcat to termbin.com.
if command -v nc >/dev/null 2>&1; then
    if [[ -n "$input_file" ]]; then
        nc termbin.com 9999 < "$input_file" && exit 0
    else
        nc termbin.com 9999 && exit 0
    fi
    echo "ERROR: Upload via nc to termbin.com also failed." >&2
    exit 1
fi

echo "ERROR: Neither 'curl' nor 'nc' is available." >&2
echo "On NixOS, the equivalent without installing anything is:" >&2
echo "    <command> 2>&1 | nix run nixpkgs#curl -- -F'file=@-' https://0x0.st" >&2
exit 1

# End of file #
