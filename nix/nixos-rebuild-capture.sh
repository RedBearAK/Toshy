#!/usr/bin/env bash
# Repo location: toshy/nix/nixos-rebuild-capture.sh

# EXPERIMENTAL. Convenience wrapper for the (first) flake-based NixOS
# rebuild: runs 'nixos-rebuild switch' with the experimental features
# enabled on the command line (required until one rebuild has succeeded,
# harmless afterward), shows the output live, keeps a full log, and on
# failure offers to upload the log to a public paste service and print
# the short URL, for machines where the clipboard is not available.
#
# Run from anywhere (typically the extracted Toshy zip/clone):
#     bash ./nix/nixos-rebuild-capture.sh

# shellcheck disable=SC2034
SCRIPT_VERSION='20260729'

if [[ $EUID -eq 0 ]]; then
    echo "ERROR: Run this as your normal user; it uses sudo where needed."
    exit 1
fi

os_release_id=''
if [[ -r /etc/os-release ]]; then
    os_release_id="$(. /etc/os-release && echo "${ID:-}")"
fi
if [[ "$os_release_id" != "nixos" ]]; then
    echo "ERROR: This script only works on NixOS."
    exit 1
fi

if [[ ! -e /etc/nixos/flake.nix ]]; then
    echo "ERROR: No system flake at /etc/nixos/flake.nix."
    echo "Generate one first (see nix/nixos-scaffold.sh) or create it manually."
    exit 1
fi

host_name="$(hostname 2>/dev/null || cat /proc/sys/kernel/hostname)"
log_file="$(mktemp /tmp/nixos-rebuild-toshy-XXXXXX.log)"

echo
echo "Rebuilding NixOS (flake: /etc/nixos#${host_name})"
echo "Full log: ${log_file}"
echo

sudo NIX_CONFIG='experimental-features = nix-command flakes' \
        nixos-rebuild switch --flake "/etc/nixos#${host_name}" 2>&1 \
        | tee "$log_file"
# The pipeline's status is tee's (always 0); the rebuild's own status is
# what matters, so it is taken from PIPESTATUS explicitly.
if [[ "${PIPESTATUS[0]}" -eq 0 ]]; then
    rebuild_ok=true
else
    rebuild_ok=false
fi

echo
if [[ "$rebuild_ok" == "true" ]]; then
    echo "Rebuild SUCCEEDED. Experimental features are now baked into the"
    echo "system; the special command prefixes are no longer needed."
    echo "Log kept at: ${log_file}"
    exit 0
fi

echo "Rebuild FAILED. Log kept at: ${log_file}"
echo
echo "The log can be sent out for inspection two ways:"
echo "  h) PRIVATE: straight to a listener on another machine (e.g. the VM"
echo "     host), using bash's built-in networking; no tools, no third party."
echo "     Start 'nc -l 9999 > received.log' on the receiver first."
echo "  y) PUBLIC paste services (a short URL to transcribe; anyone with"
echo "     the URL can read it, and these services come and go)."
read -r -p "Send the log? [h/y/N]: " response

# The share helper lives in the same source tree this script runs from.
share_script="$(dirname "$0")/../scripts/bin/toshy-share.sh"

case "$response" in
    h|H)
        default_gw="$(ip route 2>/dev/null | awk '/^default/ {print $3; exit}')"
        read -r -p "Send to HOST:PORT [${default_gw:-192.168.122.1}:9999]: " target
        target="${target:-${default_gw:-192.168.122.1}:9999}"
        if [[ -f "$share_script" ]]; then
            bash "$share_script" --to "$target" "$log_file" || exit 1
        else
            to_host="${target%%:*}"; to_port="${target##*:}"
            if ! cat "$log_file" > "/dev/tcp/${to_host}/${to_port}"; then
                echo "ERROR: Could not connect to ${target}. Listener running?"
                exit 1
            fi
            echo "Sent ${log_file} to ${target}"
        fi
        ;;
    y|Y)
        echo
        if [[ -f "$share_script" ]]; then
            bash "$share_script" "$log_file" || exit 1
        else
            echo "ERROR: toshy-share.sh not found next to this script; run from"
            echo "the extracted Toshy source tree, or use the private mode."
            exit 1
        fi
        ;;
    *)
        echo
        echo "Not sent. The log remains at: ${log_file}"
        exit 1
        ;;
esac

# End of file #
