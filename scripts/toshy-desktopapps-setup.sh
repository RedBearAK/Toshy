#!/usr/bin/env bash


# "Install" the Toshy desktop entry files and icon files, so that app launchers, 
# notification dialogs and menus can "see" them and use them. This means copying 
# the ".desktop" files into '~/.local/share/applications/' folder and copying the 
# icon files correctly into the "hicolor" theme folder in '~/.local/share/icons/'.


exit_w_error() {
    local msg="$1"
    echo -e "\n(EE) ERROR: ${msg} Exiting...\n"
    exit 1
}


# Check if the script is being run as root
if [[ ${EUID} -eq 0 ]]; then
    exit_w_error "This script must not be run as root"
fi

# Check if $USER and $HOME environment variables are not empty
if [[ -z ${USER} ]] || [[ -z ${HOME} ]]; then
    exit_w_error "\$USER and/or \$HOME environment variables are not set. We need them."
fi

# Source locations
TOSHY_CFG_DIR="${HOME}/.config/toshy"
DESKTOP_DIR="${TOSHY_CFG_DIR}/desktop"
ASSETS_DIR="${TOSHY_CFG_DIR}/assets"

# Target locations
LOCAL_SHARE="${HOME}/.local/share"
LOCAL_SHARE_APPS="${LOCAL_SHARE}/applications"
LOCAL_SHARE_ICONS="${LOCAL_SHARE}/icons/hicolor/scalable/apps"

echo -e "\nInstalling Toshy Preferences and Tray Icon app launchers..."

err_creating_apps_folder="Failed to create \"${LOCAL_SHARE_APPS}\" folder."
mkdir -p "${LOCAL_SHARE_APPS}" || exit_w_error "$err_creating_apps_folder"

err_creating_icons_folder="Failed to create \"${LOCAL_SHARE_ICONS}\" folder."
mkdir -p "${LOCAL_SHARE_ICONS}" || exit_w_error "$err_creating_icons_folder"


# Clean up any existing installations before installing new (possibly changed) files
removal_script_paths=(
    "./toshy-desktopapps-remove.sh"
    "${TOSHY_CFG_DIR}/scripts/toshy-desktopapps-remove.sh"
)


for script_path in "${removal_script_paths[@]}"; do

    if [[ -f "$script_path" && -x "$script_path" ]]; then

        echo "Cleaning up existing installation..."
        "$script_path" || {
            echo "Warning: Cleanup script failed, but continuing with installation..."
        }
        break

    fi

done


# Desktop files to install
desktop_files=(
    # "Toshy_GUI.desktop"               # DEPRECATED (name caused generic "Wayland" icon in Plasma)
    "app.toshy.preferences.desktop"     # New (matches app_id, makes GUI app icon work in Plasma)
    "Toshy_Tray.desktop"
)

# Icon files to install  
icon_files=(
    "toshy_app_icon_rainbow_inverse_grayscale.svg"
    "toshy_app_icon_rainbow_inverse.svg"
    "toshy_app_icon_rainbow.svg"
)


# Copy desktop files and replace "$HOME" placeholder with user's actual home path
for file in "${desktop_files[@]}"; do

    cp -f "${DESKTOP_DIR}/${file}" "${LOCAL_SHARE_APPS}" || \
        exit_w_error "Problem copying ${file}."

    # Replace $HOME placeholder with actual user home directory path
    err_sed_home_path="Problem updating ${file} with home directory path."

    # This usage of "-i" on Chimera (BSD sed) caused an error
    # sed -i "s|\$HOME|${HOME}|g" "${LOCAL_SHARE_APPS}/${file}" || exit_w_error "$err_sed_home_path"

    sed -i.toshybak "s|\$HOME|${HOME}|g" "${LOCAL_SHARE_APPS}/${file}" \
        || exit_w_error "$err_sed_home_path"
    rm -f "${LOCAL_SHARE_APPS}/${file}.toshybak"

done


# Copy icon files to proper hicolor theme location
for file in "${icon_files[@]}"; do

    err_copying_icon_file="Problem copying ${file}."
    cp -f "${ASSETS_DIR}/${file}" "${LOCAL_SHARE_ICONS}/" || exit_w_error "$err_copying_icon_file"

done


echo -e "\nFinished installing Toshy Preferences and Tray Icon app launchers:"
echo ""
echo "- Toshy Preferences"
echo "- Toshy Tray Icon"
echo ""
echo "The applications should appear quickly in most app launchers."
echo ""
