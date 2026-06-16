#!/usr/bin/env python3

import os
import re
import sys
import shutil
import signal
import asyncio
import datetime
import platform
import subprocess

from typing import List
from xkbcommon import xkb
from subprocess import DEVNULL

from xwaykeyz.models.key import Key

# This Python module/script is meant to monitor the user's currently _active_ 
# XKB keyboard layout, to be used as a source to update the keymapper's key 
# definitions in memory, to overcome the issue of the keymapper having no 
# understanding of the change in keyboard layouts. Without this the keymapper 
# will press keys as if it is typing on a standard US keyboard layout, even
# if the keys it should be pressing are in a different location on the user's 
# current layout and should be different key codes (or even key code combos). 

VERBOSE = True
FLUSH = True

XKB_LEVEL_MEANINGS = {
    0: "Base",     # Unmodified keys
    1: "Shift",    # Shift modifier
    2: "AltGr",    # Right Alt/AltGr
    3: "Shift+AltGr",
    4: "Caps",     # Some layouts use additional levels
    5: "Shift+Caps",
    6: "Ctrl",     # Less common but possible
}

LEVEL_MODIFIER_MAP = {
    0: [],  # Base level - no modifiers
    1: ['Shift'], 
    2: ['AltGr'],
    3: ['Shift', 'AltGr']
}


def debug(*args, ctx="DD"):
    if not VERBOSE:
        return

    # allow blank lines without context
    if len(args) == 0 or (len(args) == 1 and args[0] == ""):
        print("", flush=FLUSH)
        return
    print(f"({ctx})", *args, flush=FLUSH)

def warn(*args, ctx="WW"):
    print(f"({ctx})", *args, flush=FLUSH)

def error(*args, ctx="EE"):
    print(f"({ctx})", *args, flush=FLUSH)

def log(*args, ctx="--"):
    print(f"({ctx})", *args, flush=FLUSH)

def info(*args, ctx="--"):
    log(*args, ctx=ctx)


def signal_handler(sig, frame):
    """Handle signals like Ctrl+C"""
    if sig in (signal.SIGINT, signal.SIGQUIT):
        # Perform any cleanup code here before exiting
        # traceback.print_stack(frame)
        print('\n')
        debug(f'SIGINT or SIGQUIT received. Exiting.\n')
        sys.exit(1)

if platform.system() != 'Windows':
    signal.signal(signal.SIGINT,    signal_handler)
    signal.signal(signal.SIGQUIT,   signal_handler)
    signal.signal(signal.SIGHUP,    signal_handler)
    signal.signal(signal.SIGUSR1,   signal_handler)
    signal.signal(signal.SIGUSR2,   signal_handler)
else:
    signal.signal(signal.SIGINT,    signal_handler)
    error(f'This is only meant to run on Linux. Exiting.')
    sys.exit(1)


# Create an XKB context
# contains the keymap include paths, the log level and functions, and 
# other general customizable administrativia.
# Ref: https://github.com/xkbcommon/libxkbcommon/blob/master/doc/quick-guide.md
xkb_context = xkb.Context()


# Function to create a timestamped filename in a specific folder
def generate_timestamped_filename(base_name: str, extension: str, folder: str = ".") -> str:
    """Generate a filename with a timestamp in the specified folder."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(folder, f"{base_name}_{timestamp}.{extension}")


def interpret_modifiers(mod_arrays):
    """
    Take the array of modifier index arrays and interpret them as bit flags
    Example input: [0] [1] [128] [129] [] [] []
    
    0 = Base (no modifiers)
    1 = Shift/Lock 
    128 = AltGr (Mod5/ISO Level3)
    129 = AltGr+Shift
    """
    level_flags = {}
    
    for i, indices in enumerate(mod_arrays):
        if not indices:  # Skip empty arrays
            continue
            
        # Look at actual index values, not array positions
        for flag in indices:
            if flag == 0:
                level_flags[0] = "Base"
            elif flag == 1:
                level_flags[1] = "Shift" 
            elif flag == 128:
                level_flags[2] = "AltGr"
            elif flag == 129:
                level_flags[3] = "AltGr+Shift"
            # Could add other flags as needed

    return level_flags


#####################################################################################################


async def show_keymap_obj_info(keymap: xkb.Keymap):

    # Get the entire keymap from the keymap object as a string
    keymap_str = keymap.get_as_string()

    # This will print out the whole active keymap (too much text, dozens of KBs)
    # print("Keymap data as string:\n", keymap_str)

    # Path to save keymap string files for debugging
    folder_path = os.path.expanduser('~/Documents/Dev-Projects/xkb_layouts')

    # Generate a timestamped filename and path (seems to want a strict string type)
    file_path = generate_timestamped_filename("keymap", "txt", str(folder_path))

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Write the entire keymap string to a file for debugging purposes
    with open(file_path, "w") as f:
        f.write(keymap_str)

    debug(f"Keymap data saved to file: {file_path}")

    # Get the dir() output
    dir_output = dir(keymap)
    # Filter out items that start with "__"
    cleaned_output = [item for item in dir_output if not item.startswith("__")]
    # Debug the cleaned output
    # debug(f"Filtered output for keymap object: \n{cleaned_output}\n")

    # Make a keyboard state object (needed for dynamic access to current values?)
    xkb_state = keymap.state_new()
    if xkb_state:
        # Get the dir() output
        dir_output = dir(xkb_state)
        # Filter out items that start with "__"
        cleaned_output = [item for item in dir_output if not item.startswith("__")]
        # Debug the cleaned output
        # debug(f"Filtered output for keyboard state object: \n{cleaned_output}\n")


    # Get a list of valid keycodes 
    # (still has to be cleaned by catching XKBInvalidKeycode when doing key_get_name)
    # XKB key codes are offset from kernel key codes by +8.
    keycodes = list(keymap)
    # print("Keycodes:", keycodes)        # prints all key codes in the layout


    # Get the name of a specific key (example is first key on layout)
    key_name                    = keymap.key_get_name(keycodes[0])
    print("First key name:", key_name)  # prints "ESC" for US layout

    keycodes_key_names_map = {}

    invalid_keycodes_cnt = 0
    for keycode in keycodes:
        try:
            key_name = keymap.key_get_name(keycode)  # Get the key name (evdev alphanumeric names)
            # Get the keysyms for the specified keycode
            layout_index        = 0  # Default layout index
            shift_level         = 0  # Default shift level (no modifiers)

            # print(keymap.num_levels_for_key(keycode, layout_index))
            print()
            print(key_name, keycode, end=' ')

            all_keysyms = []
            # could be up to a total of 8 levels in some layouts?
            for shift_level in range(7):
                keysyms             = keymap.key_get_syms_by_level(
                                        keycode, 
                                        layout_index, 
                                        shift_level
                                        )
                if keysyms and keysyms[0] not in all_keysyms:
                    all_keysyms.extend(keysyms)

                print(keymap.key_get_mods_for_level(keycode, layout_index, shift_level), end=' ')

            # Convert keysyms to their corresponding symbol names
            # symbol_names = [xkb.keysym_get_name(ks) for ks in keysyms]
            symbol_names = [xkb.keysym_get_name(ks) for ks in all_keysyms]

            keycodes_key_names_map[keycode] = {
                "key_name": key_name, 
                "symbol_names": symbol_names
            }

        except xkb.XKBInvalidKeycode:
            # Invalid key codes return no corresponding XKB "name" like AD01
            # print(f"Invalid key code: {keycode}")
            invalid_keycodes_cnt += 1
    print(f"\nTotal invalid keycodes: {invalid_keycodes_cnt}")

    # # Print the dictionary mapping keycodes to key names
    # print("Keycodes to key names mapping:")
    # for keycode, key_name in keycodes_key_names_map.items():
    #     print(f"{keycode}: {key_name}")



    # Initialize a dictionary to collect data
    keycode_info = {}

    # Iterate over keycodes in the keymap
    for keycode in keycodes:

        # Stop processing early to limit debugging output
        leaving_key_code = 38
        if keycode > leaving_key_code:
            if keycode == leaving_key_code + 1:
                debug(f'\nLeaving loop after key code {leaving_key_code}...')
            break

        kernel_key_code = keycode - 8
        try:
            keymapper_symbol = Key(kernel_key_code)
        except ValueError:
            keymapper_symbol = None

        print(f'Keymapper defined symbol for XKB key code {keycode}: {keymapper_symbol} (kernel key code: {kernel_key_code})')

        try:
            key_name = keymap.key_get_name(keycode)
        except xkb.XKBInvalidKeycode as key_err:
            continue    # skip to next iteration of loop? 

        # debug(f'{keymap.num_mods() = }')    # = 16 (for English US layouts)
        # debug(f'{keymap.num_layouts_for_key(keycode) = }')    # = 1
        # debug(f'{keymap.num_levels_for_key(keycode, layout=0) = }')     # = 1
        # debug(f'{keymap.layout_get_name(0) = }')    # the layout name string, like "English (Macintosh)"

        # debug(f'{xkb_state.key_get_string(keycode) = }')     # Example: '\x1b' (ESC)
        # debug(f'{xkb_state.key_get_syms(keycode) = }')     # shows list with one integer
        # debug(f'{xkb_state.key_get_level(keycode, 0) = }')

        # sys.exit(1)     # BREAKPOINT FOR DEBUGGING

        # debug(f'{keymap.num_layouts_for_key(keycode)}')     # always 1

        # Define range based on how many levels each key has in current layout
        symbol_data = []


        for shift_level in range(keymap.num_levels_for_key(keycode, 0)):
            try:
                keysyms = keymap.key_get_syms_by_level(keycode, 0, shift_level)
                debug(f'{keysyms = }')
                symbol_names = [xkb.keysym_get_name(ks) for ks in keysyms]
                debug(f'{symbol_names = }')

                if symbol_names:  # If we have symbols at this level
                    mod_flags = keymap.key_get_mods_for_level(keycode, 0, shift_level)
                    debug(f'{mod_flags = }')
                    level_modifiers = interpret_modifiers([mod_flags])  # Pass as single array
                    
                    symbol_data.append({
                        "level": shift_level,
                        "symbols": symbol_names,
                        "modifiers": level_modifiers.get(shift_level, []),
                        "raw_flags": mod_flags  # Keep for debugging
                    })

            except Exception as e:
                print(f"Error processing keycode {keycode} at level {shift_level}: {str(e)}")


        keycode_info[keycode] = {
            "key_name": key_name,
            "levels": symbol_data,
        }

        # Output the structured information

        for keycode, info in keycode_info.items():
            print(f"\nKeycode {keycode} ({info['key_name']}):", end='')
            for level_info in info["levels"]:
                print(f"   Lvl{level_info['level']}: S: {level_info['symbols']} "
                    f"M: {level_info['modifiers']} "
                    f"(reported: {level_info['reported_modifiers']})", end='   ')

    print() # new line after all the end=''


#####################################################################################################


async def handle_new_output(line: bytes):
    """Function to handle new output from the monitoring command"""
    decoded_line = line.decode("utf-8").strip()  # Decode the binary output to text
    layout_tuples: List[str] = re.findall(r"\('xkb', '([^']+)'\)", decoded_line)
    if layout_tuples:
        debug(f'Layout Tuples: {layout_tuples = }')

        # Get the first tuple to represent the current active layout
        current_layout_tuple = layout_tuples[0]

        layout_parts = current_layout_tuple.split('+')
        layout = layout_parts[0]
        variant = layout_parts[1] if len(layout_parts) > 1 else None

        debug(f"Current Layout: '{layout}', Variant: '{variant}'")

        # Create a keymap using the layout and variant values
        xkb_keymap = xkb_context.keymap_new_from_names(
            layout=layout,variant=variant
        )

        # # Get the number of layouts (this isn't useful to print if only one layout)
        # num_layouts = keymap.num_layouts()
        # print(f'{range(num_layouts) = }')
        # if num_layouts > 1:
        #     print("Number of layouts:", num_layouts)

        # Get layout names
        # layout_names = [keymap.layout_get_name(i) for i in range(num_layouts)]
        layout_names = [xkb_keymap.layout_get_name(0)]
        debug(f"Active layout name: '{layout_names[0]}'")

        # Get the keymap information
        if xkb_keymap:
            await show_keymap_obj_info(xkb_keymap)



async def watch_dconf():
    """Watch the changes in dconf key that shows most recently used layout"""

    # intitial check for current layout ('watch' will not show output until key value changes)
    # Command we need for GNOME: gsettings get org.gnome.desktop.input-sources mru-sources
    gs_schema                   = 'org.gnome.desktop.input-sources'
    gs_key                      = 'mru-sources'
    gs_cmd_lst                  = ["gsettings", "get", gs_schema, gs_key]

    # Here we need to do a try/except to perform the initial check for current layout values
    # and handle the output similarly to the loop that will "watch" the dconf key later. 

    # Perform the initial check for the current layout
    try:
        result = subprocess.run(gs_cmd_lst, capture_output=True)
        if result.returncode == 0:
            await handle_new_output(result.stdout)
        else:
            print("Error fetching the initial layout:", result.stderr)
    except subprocess.CalledProcessError as proc_err:
        print("Subprocess error during initial check:", proc_err)


    # Command we need for GNOME: dconf watch /org/gnome/desktop/input-sources/mru-sources
    dconf_key = "/org/gnome/desktop/input-sources/mru-sources"
    dconf_cmd_lst               = ["dconf", "watch", dconf_key]

    # Start the subprocess without `text=True`
    process                     = await asyncio.create_subprocess_exec(
        *dconf_cmd_lst, stdout=asyncio.subprocess.PIPE
    )

    try:
        while True:
            output_line = await process.stdout.readline()
            if output_line:
                await handle_new_output(output_line)
            else:
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        # Clean up if the coroutine is canceled
        process.terminate()  # Terminate the subprocess
        await process.wait()  # Wait for it to exit
        print("Script terminated, cleaning up.")


def main():
    if shutil.which('dconf'):
        asyncio.run(watch_dconf())  # Start watching DConf
    else:
        debug('No handler available to monitor active keyboard layout for this environment.')
        debug('Exiting...')
        sys.exit(1)

# Ensure that the script runs correctly
if __name__ == "__main__":
    main()
