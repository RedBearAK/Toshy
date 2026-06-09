#!/usr/bin/bash


# scripts/toshy-sway-layout-test.sh
#
# Drives Sway keyboard-layout changes through both switch mechanisms so you
# can watch what "toshy-kblayout-check" detects. Run the check command in one
# tab/window and this script in another. It narrates each step, prints Sway's
# own active layout as ground truth, and always returns the keyboard to a plain
# US layout on exit (including on Ctrl-C).

# shellcheck disable=SC2034
VERSION='20260608'

# Seconds to pause on each step so you can read the watcher in the other tab.
# Bump this up if the changes scroll by too fast to correlate.
DELAY=4

# Fail loudly if this is not a usable Sway session
if ! command -v swaymsg >/dev/null 2>&1; then
    echo "Error: 'swaymsg' not found. This script must run inside a Sway session."
    exit 1
fi

if [[ -z $SWAYSOCK ]]; then
    echo "Error: \$SWAYSOCK is not set. This script must run inside a Sway session."
    exit 1
fi


# Print Sway's authoritative active layout for the first keyboard it reports
ground_truth() {
    local name index
    name="$(swaymsg -t get_inputs | grep -m1 '"xkb_active_layout_name"' \
            | sed 's/.*: *"\(.*\)".*/\1/')"
    index="$(swaymsg -t get_inputs | grep -m1 '"xkb_active_layout_index"' \
            | sed 's/.*: *\([0-9]*\).*/\1/')"
    echo "    Sway reports active layout: index ${index:-?}  name \"${name:-?}\""
}

# Reconfigure the keyboard to a given xkb_layout spec (recompiles + re-sends)
set_layout() {
    swaymsg input type:keyboard xkb_layout "$1" >/dev/null
}

# Rotate the active group index without recompiling the keymap
switch_next() {
    swaymsg input type:keyboard xkb_switch_layout next >/dev/null
}

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


banner "Keyboard layout switch test for Sway"
echo "Make sure 'toshy-kblayout-check' is already running and visible in"
echo "another tab or window. This script narrates each change and shows Sway's"
echo "own active layout. It returns you to US automatically at the end."
pause

banner "STEP 0  -  baseline: single US layout"
set_layout us
ground_truth
pause

banner "PATH A  -  reconfigure swap (EXPECT the watcher to PRINT a change)"
echo "Switching to single 'fr' (AZERTY). This recompiles and re-sends the keymap,"
echo "so the surfaceless detector should see it."
set_layout fr
ground_truth
pause

echo
echo "Switching back to single 'us'. Again recompiles and re-sends the keymap."
set_layout us
ground_truth
pause

banner "PATH B  -  group toggle (EXPECT the watcher to STAY SILENT)"
echo "Loading two layouts as groups: 'us,fr' (group 0 = us, group 1 = fr/AZERTY)."
set_layout "us,fr"
ground_truth
pause

echo
echo "Group toggle to next (us -> fr). The active GROUP index changes but the"
echo "keymap is NOT recompiled, so the surfaceless detector should not see this."
switch_next
ground_truth
pause

echo
echo "Group toggle to next again (fr -> us)."
switch_next
ground_truth
pause

banner "Done - cleanup (restore single US) runs next"
# The EXIT trap performs the final restore_us


# End of file #
