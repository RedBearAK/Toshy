#!/usr/bin/bash


# scripts/toshy-layout-switch-test.sh
#
# Drives keyboard-layout changes through both switch mechanisms on Sway OR
# Hyprland so you can watch what "toshy-kblayout-check" detects. Run the check
# command in one tab/window and this script in another.
#
# The two paths use DIFFERENT layouts so each event is self-identifying in the
# watcher tab, with no timing correlation needed:
#   - PATH A (reconfigure) uses French / AZERTY  -> a FRENCH map = PATH A fired
#   - PATH B (group toggle) uses German / QWERTZ -> a GERMAN map = PATH B fired
#   - if the German map never appears, the group toggle was missed
#
# Prints the compositor's own active layout as ground truth, and always returns
# the keyboard to a plain US layout on exit (including on Ctrl-C).

# shellcheck disable=SC2034
VERSION='20260608'

# Distinct layouts per path so the watcher output identifies which path fired.
# PATH_B_LAYOUT can be set to 'ru' for a much larger, unmistakable map if the
# German map is too subtle to spot at a glance.
PATH_A_LAYOUT='fr'
PATH_B_LAYOUT='de'

# Seconds to pause on each step so you can read the watcher in the other tab.
DELAY=4

# Detect which supported compositor we are in
if [[ -n $SWAYSOCK ]]; then
    COMPOSITOR='sway'
elif [[ -n $HYPRLAND_INSTANCE_SIGNATURE ]]; then
    COMPOSITOR='hyprland'
else
    echo "Error: not in a Sway or Hyprland session"
    echo "(\$SWAYSOCK and \$HYPRLAND_INSTANCE_SIGNATURE are both unset)."
    exit 1
fi

# Verify the control tool for that compositor is present
case "$COMPOSITOR" in
    sway)     command -v swaymsg >/dev/null 2>&1 || { echo "Error: 'swaymsg' not found."; exit 1; } ;;
    hyprland) command -v hyprctl >/dev/null 2>&1 || { echo "Error: 'hyprctl' not found."; exit 1; } ;;
esac


# --- compositor-specific primitives ------------------------------------------

# Reconfigure the keyboard to a given xkb layout spec (recompiles + re-sends)
set_layout() {
    case "$COMPOSITOR" in
        sway)     swaymsg input type:keyboard xkb_layout "$1" >/dev/null ;;
        hyprland) hyprctl keyword input:kb_layout "$1" >/dev/null ;;
    esac
}

# Rotate the active group index without recompiling the keymap
switch_next() {
    case "$COMPOSITOR" in
        sway)     swaymsg input type:keyboard xkb_switch_layout next >/dev/null ;;
        hyprland) hyprctl switchxkblayout all next >/dev/null ;;
    esac
}

# Print the compositor's authoritative active layout for its first keyboard
ground_truth() {
    local name index
    case "$COMPOSITOR" in
        sway)
            name="$(swaymsg -t get_inputs | grep -m1 '"xkb_active_layout_name"' \
                    | sed 's/.*: *"\(.*\)".*/\1/')"
            index="$(swaymsg -t get_inputs | grep -m1 '"xkb_active_layout_index"' \
                    | sed 's/.*: *\([0-9]*\).*/\1/')"
            echo "    Sway active layout: index ${index:-?}  name \"${name:-?}\"" ;;
        hyprland)
            # Read the active keymap of the keyboard marked "main: yes", not the
            # first one listed (which is often a virtual keyboard that lags or
            # carries only a single layout, so first-match would mislead).
            name="$(hyprctl devices | awk '
                /active keymap:/ { sub(/.*active keymap: */, ""); k = $0 }
                /main: yes/      { print k; exit }
            ')"
            echo "    Hyprland active layout: \"${name:-?}\"" ;;
    esac
}

# --- shared orchestration ----------------------------------------------------

# Always leave the keyboard on a plain US layout, even on Ctrl-C or early exit
restore_us() {
    echo
    echo "Restoring plain US layout..."
    set_layout us
    ground_truth
}
trap restore_us EXIT

banner() {
    echo
    echo "=================================================================="
    echo "$1"
    echo "=================================================================="
}

pause() {
    echo "    (watch the other tab for ${DELAY}s...)"
    sleep "$DELAY"
}


banner "Keyboard layout switch test  -  detected compositor: ${COMPOSITOR}"
echo "Make sure 'toshy-kblayout-check' is already running and visible in"
echo "another tab or window."
echo
echo "Watch the LAYOUT it reports, not the timing:"
echo "  - a FRENCH map appearing means PATH A (reconfigure) was detected"
echo "  - a GERMAN map appearing means PATH B (group toggle) was detected"
echo "  - if the GERMAN map never appears, the group toggle was missed"
pause

banner "STEP 0  -  baseline: single US layout"
set_layout us
ground_truth
pause

banner "PATH A  -  reconfigure swap   (EXPECT a FRENCH map in the watcher)"
echo "Switching to single '${PATH_A_LAYOUT}'. This recompiles and re-sends the"
echo "keymap, so the surfaceless detector should see it and report French."
set_layout "$PATH_A_LAYOUT"
ground_truth
pause

echo
echo "Switching back to single 'us' (recompiles + re-sends; watcher clears)."
set_layout us
ground_truth
pause

banner "PATH B  -  group toggle   (a GERMAN map = caught; silence = missed)"
echo "Loading two layouts as groups: 'us,${PATH_B_LAYOUT}' (group 0 = us)."
echo "Active layout stays us here, so the watcher should not change yet."
set_layout "us,${PATH_B_LAYOUT}"
ground_truth
pause

echo
echo "Group toggle to next (us -> ${PATH_B_LAYOUT}). Active GROUP index changes"
echo "but the keymap is not recompiled. A GERMAN map in the watcher means the"
echo "compositor re-sent a rotated keymap (caught); silence means missed."
switch_next
ground_truth
pause

echo
echo "Group toggle to next again (${PATH_B_LAYOUT} -> us)."
switch_next
ground_truth
pause

banner "Done - cleanup (restore single US) runs next"
# The EXIT trap performs the final restore_us


# End of file #
