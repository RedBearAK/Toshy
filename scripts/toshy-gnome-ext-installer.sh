#!/usr/bin/env bash

# Script tries to programmatically determine which Toshy-compatible
# GNOME extension(s) to install and use the extentions website API to
# download and install the correct version for the detected GNOME release.

# NOTE:
# Avoid defining and assigning local variables at the same time if it
# may hide a return code/error value. (Prevent Shellcheck warning SC2155.)


# Extension information
declare -A EXTENSIONS=(
    [                  "xremap"  ]="5060:xremap@k0kubun.com"
    [    "focused-window-d-bus"  ]="5592:focused-window-d-bus@flexagoon.com"
    [   "window-calls-extended"  ]="4974:window-calls-extended@hseliger.eu"
)


# Check if we're running on Wayland GNOME
check_wayland_gnome() {

    # TODO: This needs to detect some other things like "Ubuntu" or "Anduin" or "Zorin", or
    # scan through other `env` output for "gnome" in other desktop-related variables. 
    # Also should probably be case insensitive.

    # Check if we're on GNOME
    if [[ "$XDG_CURRENT_DESKTOP" != *"GNOME"* ]]; then
        echo "Not running GNOME, skipping extension setup"
        return 1
    fi

    # TODO: Session type can be changed by the user, so if we can determine GNOME is
    # present, the extensions should probably be installed regardless of session 
    # type (X11/Xorg or Wayland). Since they may log out of X11/Xorg and into Wayland.

    # Check if we're on Wayland
    if [[ "$XDG_SESSION_TYPE" != "wayland" ]]; then
        echo "Not running Wayland, skipping extension setup"
        return 1
    fi

    echo "Detected Wayland GNOME session"
    return 0
}


# Check if an extension is installed and enabled
is_extension_active() {
    local uuid=$1

    # Check if extension is installed
    if [[ ! -d "$HOME/.local/share/gnome-shell/extensions/$uuid" ]] && 
        [[ ! -d "/usr/share/gnome-shell/extensions/$uuid" ]]; then
        return 1
    fi

    # Check if extension is enabled
    if gnome-extensions info "$uuid" 2>/dev/null | grep -q "State: ENABLED"; then
        return 0
    fi

    return 1
}


# Check if any of our required extensions are already active
check_existing_extensions() {
    echo "Checking for existing extensions..."

    for ext_name in "${!EXTENSIONS[@]}"; do
        local ext_info="${EXTENSIONS[$ext_name]}"
        local uuid="${ext_info#*:}"

        if is_extension_active "$uuid"; then
            echo "✓ Found active extension: $ext_name ($uuid)"
            return 0
        fi
    done

    echo "No compatible extensions found, installation needed"
    return 1
}


# Get extension info from e.g.o API
get_extension_info() {
    local extension_id=$1
    local gnome_version=$2

    local all_info
    all_info=$(curl -s "https://extensions.gnome.org/extension-info/?pk=${extension_id}")

    if [[ -z "$all_info" ]] || [[ "$all_info" == "null" ]]; then
        return 1
    fi

    local uuid
    uuid=$(echo "$all_info" | jq -r '.uuid')

    local name
    name=$(echo "$all_info" | jq -r '.name')

    local version_map
    version_map=$(echo "$all_info" | jq '.shell_version_map')

    # Find compatible version
    local version_pk=""

    # Try exact match first
    version_pk=$(echo "$version_map" | jq -r ".\"${gnome_version}\".pk // empty")

    # Try major version only
    if [[ -z "$version_pk" ]]; then
        local major_version
        major_version=$(echo "$gnome_version" | cut -d'.' -f1)
        version_pk=$(echo "$version_map" | jq -r ".\"${major_version}\".pk // empty")
    fi

    # Find closest compatible version
    if [[ -z "$version_pk" ]]; then
        local compatible_version
        compatible_version=$(echo "$version_map" | jq -r 'keys[]' 2>/dev/null | sort -V | while read -r v; do
            if [[ $(echo -e "$v\n$gnome_version" | sort -V | head -1) == "$v" ]]; then
                echo "$v"
            fi
        done | tail -1)

        if [[ -n "$compatible_version" ]]; then
            version_pk=$(echo "$version_map" | jq -r ".\"${compatible_version}\".pk")
        fi
    fi

    if [[ -z "$version_pk" || "$version_pk" == "null" ]]; then
        return 1
    fi

    echo "$uuid|$name|$version_pk"
    return 0
}


# Download and install extension
install_extension() {

    local extension_id=$1
    local uuid=$2
    local version_pk=$3
    local name=$4

    echo "Installing $name..."

    # Construct download URL
    local download_url="https://extensions.gnome.org/download-extension/${uuid}.shell-extension.zip?version_tag=${version_pk}"

    # Download extension
    local temp_file="/tmp/${uuid}.shell-extension.zip"
    if ! curl -sL "$download_url" -o "$temp_file"; then
        echo "Failed to download extension"
        return 1
    fi

    # Verify it's a valid zip file
    if ! file "$temp_file" | grep -q "Zip archive"; then
        echo "Downloaded file is not a valid zip"
        rm -f "$temp_file"
        return 1
    fi

    # Install extension
    if ! gnome-extensions install --force "$temp_file" 2>/dev/null; then
        echo "Failed to install extension"
        rm -f "$temp_file"
        return 1
    fi

    # Enable extension
    if ! gnome-extensions enable "$uuid" 2>/dev/null; then
        echo "Failed to enable extension"
        rm -f "$temp_file"
        return 1
    fi

    rm -f "$temp_file"
    echo "✓ Successfully installed and enabled $name"
    return 0

}


# Main installation logic
install_required_extension() {

    local gnome_version
    gnome_version=$(gnome-shell --version | awk '{print $3}')
    echo "GNOME Shell version: $gnome_version"

    # Try extensions in order of preference
    local extension_order=("xremap" "focused-window-d-bus" "window-calls-extended")

    for ext_name in "${extension_order[@]}"; do
        local ext_info="${EXTENSIONS[$ext_name]}"
        local ext_id="${ext_info%:*}"

        # local ext_uuid
        # ext_uuid="${ext_info#*:}"

        echo -e "\nTrying to install $ext_name (ID: $ext_id)..."

        # Get extension info from API
        local info
        info=$(get_extension_info "$ext_id" "$gnome_version")

        if [[ $? -ne 0 ]]; then
            echo "Extension $ext_name not compatible with GNOME $gnome_version"
            continue
        fi

        # Parse info
        IFS='|' read -r uuid name version_pk <<< "$info"

        # Try to install
        if install_extension "$ext_id" "$uuid" "$version_pk" "$name"; then
            echo -e "\n✓ Successfully set up $name for your keymapper"
            return 0
        else
            echo "Failed to install $ext_name, trying next option..."
        fi
    done

    echo -e "\n✗ Error: Could not install any compatible extension"
    echo "You may need to manually install one of these extensions:"
    echo "  - https://extensions.gnome.org/extension/5060/xremap/"
    echo "  - https://extensions.gnome.org/extension/5592/focused-window-d-bus/"
    echo "  - https://extensions.gnome.org/extension/4974/window-calls-extended/"
    return 1

}


# Main execution
main() {

    echo "GNOME Extension Setup for Keymapper"
    echo "===================================="

    # Check if we're on Wayland GNOME
    if ! check_wayland_gnome; then
        exit 0
    fi

    # Check if we already have a compatible extension
    if check_existing_extensions; then
        echo -e "\n✓ Compatible extension already installed and active"
        echo "No further action needed"
        exit 0
    fi

    # Install required extension
    install_required_extension

}


# Run main function
main
