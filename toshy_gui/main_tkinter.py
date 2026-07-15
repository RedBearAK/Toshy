#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__version__ = '20250717'

# Preferences app for Toshy, using tkinter GUI and "Sun Valley" theme
TOSHY_PART      = 'gui'   # CUSTOMIZE TO SPECIFIC TOSHY COMPONENT! (gui, tray, config)
TOSHY_PART_NAME = 'Toshy Preferences app'  # pretty name to print out
APP_VERSION     = __version__

# -------- COMMON COMPONENTS --------------------------------------------------

import os
import queue
import shutil
import subprocess

from subprocess import DEVNULL

# Initialize Toshy runtime before other imports
from toshy_common.runtime_utils import initialize_toshy_runtime
runtime = initialize_toshy_runtime()

# Local imports
from toshy_common import logger
from toshy_common.logger import *
from toshy_common.settings_class import Settings
from toshy_common.modifier_modes import (
    CAPSLOCK_MODES,
    CAPSLOCK_MODE_DEFAULT,
    CAPSLOCK_MODE_LABELS,
)
from toshy_common.process_manager import ProcessManager
from toshy_common.service_manager import ServiceManager
from toshy_common.monitoring import SettingsMonitor, ServiceMonitor

# Make process manager global
process_mgr = None

logger.FLUSH        = True
logger.VERBOSE      = False



###############################################################################
# -------- TOSHY PREFERENCES GUI SPECIFIC COMPONENTS --------------------------
###############################################################################


# Define some globals for the commands run by menu items

# assets_path         = os.path.join(current_folder_path, 'assets')
# icon_file_active    = os.path.join(assets_path, "toshy_app_icon_rainbow.svg")
# icon_file_grayscale = os.path.join(assets_path, "toshy_app_icon_rainbow_inverse_grayscale.svg")
# icon_file_inverse   = os.path.join(assets_path, "toshy_app_icon_rainbow_inverse.svg")

# Fix for Solus Budgie failing to show proper icons when using full path. Use base file name string.
# Icon files will all be copied into the local-share-icons location to make this work. 
icon_file_active                = "toshy_app_icon_rainbow"
icon_file_grayscale             = "toshy_app_icon_rainbow_inverse_grayscale"
icon_file_inverse               = "toshy_app_icon_rainbow_inverse"


config_dir_path = runtime.config_dir
cnfg = Settings(config_dir_path)
cnfg.watch_database()
debug("")
debug(cnfg)   # prints out the __str__ method of Settings class

# Notification handler object setup
from toshy_common.notification_manager import NotificationManager
ntfy = NotificationManager(icon_file_active, title='Toshy Alert (GUI)')

# Service manager instance
service_manager = ServiceManager(ntfy, icon_file_active, icon_file_inverse)

# Prepare a queue for updates of the GUI (switches, radio buttons, labels)
gui_update_queue = queue.Queue()


# Process queue from main thread
def process_gui_queue():
    """Check for pending GUI updates"""
    try:
        while True:
            item = gui_update_queue.get_nowait()

            if item == "update_settings":
                debug("!!! Processing settings update from queue !!!")
                load_radio_btn_settings(cnfg, optspec_var, "optspec_layout")
                load_radio_btn_settings(cnfg, capslock_mode_var, "capslock_mode")
                load_switch_settings(cnfg)

            elif isinstance(item, tuple) and item[0] == "service_status":
                _, config_status, sessmon_status = item
                debug("!!! Processing service status update from queue !!!")
                try:
                    svc_status_lbl_config.config(text=f'Toshy Config: {config_status}')
                    svc_status_lbl_sessmon.config(text=f'Session Monitor: {sessmon_status} ')
                except NameError:
                    pass  # Labels might not exist yet

    except queue.Empty:
        pass
    finally:
        # Schedule next check
        root.after(100, process_gui_queue)


sysctl_cmd      = f"{shutil.which('systemctl')}"
user_sysctl     = f'{sysctl_cmd} --user'

svc_status_sessmon          = 'Unknown '              # 'Undefined'
svc_status_config           = 'Unknown '              # 'Undefined'


####################################################
# Start setting up the tkinter GUI window

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import sv_ttk   # "Sun Valley" tkinter theme module

# CentOS 7 can't handle the PNG icon file, so use Pillow to open it
from PIL import Image, ImageTk

TOSHY_GUI_APP_CLASSNAME = 'Toshy-Prefs'


# className is what appears in task switcher (only first letter will be capitalized)
root = tk.Tk(className=f'{TOSHY_GUI_APP_CLASSNAME}') # tkinter window object instantiated, now put stuff in it

# Set what displays in the window title bar (not in task switcher)
root.title("Toshy Preferences")

# Set WM_CLASS for additional Toplevel windows
root.option_add("*Toplevel.className", f'{TOSHY_GUI_APP_CLASSNAME}')

root.config(padx=20, pady=20)

# screen_width = root.winfo_screenwidth()
# screen_height = root.winfo_screenheight()

# offset_x = screen_width     // 5    if screen_width     > 1900      else screen_width // 10
# offset_y = screen_height    // 10   if screen_height    > 1000      else screen_height // 20

# root.geometry(f'-{offset_x}+{offset_y}')

# Give tkinter window a nice icon 
# (desktop entry file shows nice icon in launcher but doesn't set icon in task switcher)
# icon_file = os.path.join(TOSHY_CONFIG_DIR, 'assets', 'toshy_app_icon_rainbow_512px.png')
resources_dir = os.path.join(os.path.dirname(__file__), 'resources')
icon_file = os.path.join(resources_dir, 'toshy_app_icon_rainbow_512px.png')

# app_icon_image_path = tk.PhotoImage(file = icon_file)
# root.wm_iconphoto(False, app_icon_image_path)

# Use Pillow to open the image, to make it work on CentOS 7
image                           = Image.open(icon_file)
app_icon_image                  = ImageTk.PhotoImage(image)
root.wm_iconphoto(False, app_icon_image)

# Set a font style to use for switch text
switch_text_font_dict           = {"family": "Helvetica", "size": 13}
sw_txt_font                     = tkfont.Font(**switch_text_font_dict)

# Set a font style to use for switch description labels
switch_label_font_dict          = {"family": "Helvetica", "size": 12, "slant": "italic"}
sw_lbl_font                     = tkfont.Font(**switch_label_font_dict)
sw_lbl_font_color               = 'gray'

# adjustments for switch description labels
sw_lbl_indent                   = 50
btn_lbl_pady                    = (0, 10)
sw_padx                         = 0
btn_pady                        = 0
wrap_len                        = 380


# Monkey patch the Sun Valley theme to work with Tk 9.0
tk_version = root.tk.eval('info patchlevel')
if tk_version.startswith('9.'):
    original_load_theme = sv_ttk._load_theme
    
    def patched_load_theme(style):
        if not isinstance(style.master, tk.Tk):
            raise TypeError("root must be a `tkinter.Tk` instance!")
        
        if not hasattr(style.master, "_sv_ttk_loaded"):
            sv_ttk_dir = os.path.dirname(sv_ttk.__file__)
            tcl_path = os.path.join(sv_ttk_dir, "sv.tcl")
            
            with open(tcl_path, 'r') as f:
                tcl_content = f.read()
            
            # If already patched, skip the monkey patch entirely
            if 'package require Tk 8.6-' in tcl_content:
                return original_load_theme(style)
            
            tcl_content = tcl_content.replace('package require Tk 8.6', 'package require Tk 8.6-')
            
            # Fix relative paths
            tcl_content = tcl_content.replace(
                '[file dirname [info script]]',
                f'"{sv_ttk_dir}"'
            )
            
            style.tk.eval(tcl_content)
            style.master._sv_ttk_loaded = True
    
    # This line does the "magic" - replaces the function
    sv_ttk._load_theme = patched_load_theme
    debug("Monkey-patched sv_ttk for Tk 9.0 compatibility")


####################################################
# Define functions for widgets actions to engage


def save_radio_settings(cnfg: Settings, var: tk.StringVar, key: str):
    setattr(cnfg, key, var.get())
    cnfg.save_settings()


def save_switch_settings(cnfg: Settings, var: tk.BooleanVar, key: str):
    setattr(cnfg, key, var.get())
    cnfg.save_settings()


def load_radio_btn_settings(cnfg: Settings, var: tk.StringVar, key: str):
    value = getattr(cnfg, key)
    var.set(value)


def load_switch_settings(cnfg: Settings):
    forced_numpad_switch_var.set(       cnfg.forced_numpad)
    media_arrows_fix_switch_var.set(    cnfg.media_arrows_fix)
    multi_lang_switch_var.set(          cnfg.multi_lang)
    ST3_in_VSCode_switch_var.set(       cnfg.ST3_in_VSCode)
    Enter2Ent_Cmd_switch_var.set(       cnfg.Enter2Ent_Cmd)
    theme_switch_var.set(               cnfg.gui_dark_theme)
    update_theme()


def update_theme():
    # set "Sun Valley" theme variant (not really sure about the best place to do this)
    if cnfg.gui_dark_theme:
        sv_ttk.set_theme('dark')
    else:
        sv_ttk.set_theme('light')


##########################
# Define columns/frames

top_frame = tk.Frame(root) #, width=900, highlightbackground='dim gray', highlightthickness=1)
top_frame.pack(anchor=tk.N, side=tk.TOP, expand=True, fill=tk.BOTH, pady=(0, 20), ipady=4, ipadx=4)

top_frame_left_column = tk.Frame(top_frame, width=400) #, highlightbackground='dim gray', highlightthickness=1)
top_frame_left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=4, ipadx=4) #, expand=False)
# top_frame_left_column.pack_propagate(False)

top_frame_middle_column = tk.Frame(top_frame) #, highlightbackground='dim gray', highlightthickness=1)
top_frame_middle_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=20, ipadx=20)
# top_frame_middle_column.pack_propagate(False)

top_frame_right_column = tk.Frame(top_frame, width=400) #, highlightbackground='dim gray', highlightthickness=1)
top_frame_right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, ipady=4, ipadx=4) #, expand=False)
# top_frame_right_column.pack_propagate(False)

# Create a new frame to hold all the other frames
middle_frame = tk.Frame(root)
middle_frame.pack(side=tk.TOP, fill=tk.BOTH)

left_column = tk.Frame(middle_frame) #, highlightbackground='dim gray', highlightthickness=1)#, bg='red', bd=5)
left_column.pack(side=tk.LEFT, fill=tk.BOTH)

left_column_low_spacer = tk.Frame(left_column) #, highlightbackground='gray', highlightthickness=1)
# push elements in left column up, leaving "space" below
left_column_low_spacer.pack(side=tk.BOTTOM, fill=tk.BOTH, ipady=30)

mid_center_column = tk.Frame(middle_frame) #, highlightbackground='dim gray', highlightthickness=1)
mid_center_column.pack(side=tk.LEFT, fill=tk.BOTH, ipadx=1)

mid_right_column = tk.Frame(middle_frame) #, highlightbackground='gray', highlightthickness=1)
mid_right_column.pack(side=tk.LEFT, fill=tk.BOTH)


###########################
# Widgets

# Top frame stuff

# Set a font style to use for service description labels
svc_lbl_font_dict = {"family": "monospace", "size": 12, "weight": "bold"}
svc_lbl_font_color = 'gray'
svc_lbl_font = tkfont.Font(**svc_lbl_font_dict)

services_label = tk.Label(
    top_frame_left_column,
    justify=tk.CENTER,
    text=('Toshy Services Status:   '),
    font=svc_lbl_font
)
services_label.pack(padx=sw_lbl_indent, pady=btn_lbl_pady)

svc_status_lbl_config = tk.Label(
    top_frame_left_column,
    justify=tk.CENTER,
    text=(  f'Toshy Config: {svc_status_config}' ),
    font=svc_lbl_font,
    fg=svc_lbl_font_color
)
svc_status_lbl_config.pack(anchor=tk.N, padx=sw_lbl_indent, pady=btn_lbl_pady)

svc_status_lbl_sessmon = tk.Label(
    top_frame_left_column,
    justify=tk.CENTER,
    text=(  f'Session Monitor: {svc_status_sessmon} ' ),
    font=svc_lbl_font,
    fg=svc_lbl_font_color
)
svc_status_lbl_sessmon.pack(anchor=tk.N, padx=sw_lbl_indent, pady=btn_lbl_pady)

svc_btn_pady = 12
# svc_btn_padx = 10

svc_status_config_btn = ttk.Button(
    top_frame_right_column,
    width=25,
    text='(Re)Start Toshy Services',
    # command=fn_restart_toshy_services
    command=service_manager.restart_services
)
svc_status_config_btn.pack(anchor=tk.W, padx=sw_lbl_indent, pady=svc_btn_pady)

svc_status_sessmon_btn = ttk.Button(
    top_frame_right_column,
    width=25,
    text='Stop Toshy Services',
    # command=fn_stop_toshy_services
    command=service_manager.stop_services
)
svc_status_sessmon_btn.pack(anchor=tk.W, padx=sw_lbl_indent, pady=svc_btn_pady)


###############################################################################
# START of Switches and description labels for options

###############################################################################
# Left column stuff

multi_lang_switch_var   = tk.BooleanVar(value=False)
multi_lang_switch       = ttk.Checkbutton(
    left_column,
    text='Alt_Gr on Right Cmd key',
    style='Switch.TCheckbutton',
    variable=multi_lang_switch_var
)

multi_lang_label = tk.Label(
    left_column,
    justify=tk.LEFT,
    text='Restores access to the Level3/4 additional\
        \ncharacters on non-US keyboards/layouts',
    font=sw_lbl_font,
    wraplength=wrap_len,
    fg=sw_lbl_font_color
)

ST3_in_VSCode_switch_var = tk.BooleanVar(value=False)
ST3_in_VSCode_switch     = ttk.Checkbutton(
    left_column, 
    text='ST3 shortcuts in VSCode(s)', 
    style='Switch.TCheckbutton', 
    variable=ST3_in_VSCode_switch_var
)

ST3_in_VSCode_label = tk.Label(
    left_column,
    justify=tk.LEFT,
    text=f'Use shortcuts from Sublime Text 3 in\
        \nVisual Studio Code (and variants)',
    font=sw_lbl_font,
    wraplength=wrap_len,
    fg=sw_lbl_font_color
)

# CapsLock mode radio button group (replaces legacy Caps2Cmd/Caps2Esc_Cmd toggles).
# Buttons built from the canonical mode tuple; shared StringVar provides exclusivity.
capslock_mode_var = tk.StringVar(value=CAPSLOCK_MODE_DEFAULT)

capslock_mode_radio_btns_lst = [
    ttk.Radiobutton(
        left_column,
        text=f'  {CAPSLOCK_MODE_LABELS.get(caps_mode, caps_mode)}',
        style='Switch.TRadiobutton',
        variable=capslock_mode_var,
        value=caps_mode
    )
    for caps_mode in CAPSLOCK_MODES
]

capslock_mode_label = tk.Label(
    left_column,
    justify=tk.LEFT,
    text=(  'What the CapsLock key does. "Swap roles" modes also turn the physical '
            'Left Ctrl key into a literal CapsLock key, with CapsLock taking over '
            'Left Ctrl\'s usual role (Super in GUI apps, Ctrl in terminals).' ),
    font=sw_lbl_font,
    wraplength=wrap_len,
    fg=sw_lbl_font_color
)

Enter2Ent_Cmd_switch_var = tk.BooleanVar(value=False)
Enter2Enter_Cmd_switch = ttk.Checkbutton(
    left_column,
    text='Multipurpose Enter: Enter, Cmd',
    style='Switch.TCheckbutton',
    variable=Enter2Ent_Cmd_switch_var
)

Enter2Ent_Cmd_label = tk.Label(
    left_column,
    justify=tk.LEFT,
    text=f'Modmap Enter key to be:\
        \n  • Enter when tapped\
        \n  • Command key for hold/combo',
    font=sw_lbl_font,
    wraplength=wrap_len,
    fg=sw_lbl_font_color
)

# Do not pack these items into left column if using "barebones" config file
if not runtime.barebones_config:
    multi_lang_switch.pack(         anchor=tk.W,    padx=sw_padx,          pady=btn_pady)
    multi_lang_label.pack(          anchor=tk.W,    padx=sw_lbl_indent,    pady=btn_lbl_pady)
    ST3_in_VSCode_switch.pack(      anchor=tk.W,    padx=sw_padx,          pady=btn_pady)
    ST3_in_VSCode_label.pack(       anchor=tk.W,    padx=sw_lbl_indent,    pady=btn_lbl_pady)
    for capslock_mode_radio_btn in capslock_mode_radio_btns_lst:
        capslock_mode_radio_btn.pack(anchor=tk.W,   padx=sw_padx + 10,     pady=btn_pady)
    capslock_mode_label.pack(       anchor=tk.W,    padx=sw_lbl_indent,    pady=btn_lbl_pady)
    Enter2Enter_Cmd_switch.pack(    anchor=tk.W,    padx=sw_padx,          pady=btn_pady)
    Enter2Ent_Cmd_label.pack(       anchor=tk.W,    padx=sw_lbl_indent,    pady=btn_lbl_pady)


###############################################################################
# Left colum low spacer stuff


def show_popup_dialog(text = None):
    popup_root = tk.Toplevel(root)
    popup_root.title("Information")
    # popup_root.config(padx=10, pady=10)
    popup_root.bind("<Control-w>", lambda event: popup_root.destroy())
    popup_root.bind("<Escape>", lambda event: popup_root.destroy())
    # Make the popup window modal (does not work)
    popup_root.grab_set()

    text = f"""About (Work in Progress): 
    
Version: {APP_VERSION}

GUI for changing Toshy preferences, a keymapper config file, \
intended to make the keyboard in Linux work like a Mac.
"""

    main_popup_frame = tk.Frame(popup_root, highlightbackground='gray', highlightthickness=1)
    main_popup_frame.pack(anchor=tk.N, side=tk.TOP, ipadx=10, ipady=10, fill=tk.X, expand=True)
    
    label = tk.Label(main_popup_frame, justify=tk.LEFT, text=text, wraplength=350)
    label.pack(padx=10, pady=10, ipadx=10, ipady=10, expand=True)

    version_label = tk.Label(
        main_popup_frame,
        justify=tk.LEFT,
        text=f'Version {APP_VERSION}',
        # font=("bold", 14),
        font=sw_lbl_font,
        fg=sw_lbl_font_color
    )
    version_label.pack(anchor=tk.SW, padx=10, pady=10)

    ok_button = ttk.Button(main_popup_frame, text="OK", command=popup_root.destroy)
    ok_button.pack(padx=10, pady=10, expand=True)

    # Center the popup over the parent window (do this after packing widgets)
    popup_root.update_idletasks()
    width = popup_root.winfo_width()
    height = popup_root.winfo_height()
    if width < 450:
        width = 450
    # if height < 400:
    #     height = 400
    parent_x = root.winfo_rootx()
    parent_y = root.winfo_rooty()
    parent_width = root.winfo_width()
    parent_height = root.winfo_height()
    x = parent_x + (parent_width    // 2) - (width // 2)
    y = parent_y + (parent_height   // 3) - (height // 2)
    popup_root.geometry(f"{width}x{height}+{x}+{y}")
    # Wait for the popup window to close before resuming interaction with the main window
    popup_root.wait_window(popup_root)


help_about_btn = ttk.Button(
    left_column_low_spacer,
    width=25,
    text='Help / About',
    command=show_popup_dialog
)
help_about_btn.pack(anchor=tk.SW, side=tk.BOTTOM, padx=10, pady=6)

# Pack this after the help button, to get it to appear ABOVE the help button.
left_column_low_spacer_label = tk.Label(
    left_column_low_spacer,
    justify=tk.LEFT,
    text=f'Settings changes take effect immediately.',
    font=sw_lbl_font,
    fg=sw_lbl_font_color
)
left_column_low_spacer_label.pack(side=tk.BOTTOM, anchor=tk.SW, padx=10, pady=20, expand=True) #padx=10, pady=10)


###############################################################################
# Right column stuff

forced_numpad_switch_var   = tk.BooleanVar(value=True)
forced_numpad_switch       = ttk.Checkbutton(
    mid_right_column,
    text='Forced Numpad',
    style='Switch.TCheckbutton',
    variable=forced_numpad_switch_var
)

forced_numpad_label = tk.Label(
    mid_right_column,
    justify=tk.LEFT,
    text='Makes the numeric keypad always act like a Numpad, ignoring actual NumLock LED state.\
        \n   • NumLock key becomes "Clear" key (Escape)\
        \n   • Option+NumLock toggles NumLock OFF/ON\
        \n(Fn+NumLock will also toggle NumLock state, but only on real Apple keyboards)',
    font=sw_lbl_font,
    wraplength=wrap_len,
    fg=sw_lbl_font_color
)

media_arrows_fix_switch_var = tk.BooleanVar(value=False)
media_arrows_fix_switch     = ttk.Checkbutton(
    mid_right_column,
    text='Media Arrows Fix',
    style='Switch.TCheckbutton',
    variable=media_arrows_fix_switch_var
)

media_arrows_fix_label = tk.Label(
    mid_right_column,
    justify=tk.LEFT,
    text=(  'Converts arrow keys that have "media" functions when used with '
            'Fn key, into PgUp/PgDn/Home/End keys'),
    font=sw_lbl_font,
    wraplength=wrap_len,
    fg=sw_lbl_font_color
)

# Option-key special character radio button group
optspec_var = tk.StringVar(value="US") # default value
rad_btn_padx = sw_padx + 10

optspec_US_radio_btn = ttk.Radiobutton(
    mid_right_column,
    text='  Option-key Special Characters (US)*',
    style='Switch.TRadiobutton',
    variable=optspec_var, 
    value="US"
)

optspec_ABC_radio_btn = ttk.Radiobutton(
    mid_right_column,
    text='  Option-key Special Characters (ABC Extended)',
    style='Switch.TRadiobutton',
    variable=optspec_var, 
    value="ABC"
)

optspec_Disabled_radio_btn = ttk.Radiobutton(
    mid_right_column,
    text='  Disable Option-key Special Characters',
    style='Switch.TRadiobutton',
    variable=optspec_var, 
    value="Disabled"
)

optspec_label = tk.Label(
    mid_right_column,
    justify=tk.LEFT,
    text=(  'Option-key special characters are available on all regular keys and '
            'punctuation keys when holding Option or Shift+Option. Choices are '
            'standard US layout, ABC Extended layout, or disabled. Default is US '
            'layout.' ),
    font=sw_lbl_font,
    wraplength=wrap_len,
    fg=sw_lbl_font_color
)

# Do not pack these items into right column if using "barebones" config file
if not runtime.barebones_config:
    forced_numpad_switch.pack(anchor=tk.W, padx=sw_padx, pady=btn_pady)
    forced_numpad_label.pack(anchor=tk.W, padx=sw_lbl_indent, pady=btn_lbl_pady)
    media_arrows_fix_switch.pack(anchor=tk.W, padx=sw_padx, pady=btn_pady)
    media_arrows_fix_label.pack(anchor=tk.W, padx=sw_lbl_indent, pady=btn_lbl_pady)
    optspec_US_radio_btn.pack(anchor=tk.W, padx=rad_btn_padx, pady=btn_pady)
    optspec_ABC_radio_btn.pack(anchor=tk.W, padx=rad_btn_padx, pady=btn_pady)
    optspec_Disabled_radio_btn.pack(anchor=tk.W, padx=rad_btn_padx, pady=btn_pady)
    optspec_label.pack(anchor=tk.W, padx=sw_lbl_indent, pady=btn_lbl_pady)

# left column stuff commands
multi_lang_switch.config(
    command=lambda: save_switch_settings(
        cnfg, multi_lang_switch_var, 'multi_lang'))
ST3_in_VSCode_switch.config(
    command=lambda: save_switch_settings(
        cnfg, ST3_in_VSCode_switch_var, 'ST3_in_VSCode'))
for capslock_mode_radio_btn in capslock_mode_radio_btns_lst:
    capslock_mode_radio_btn.config(
        command=lambda: save_radio_settings(
            cnfg, capslock_mode_var, 'capslock_mode'))
Enter2Enter_Cmd_switch.config(
    command=lambda: save_switch_settings(
        cnfg, Enter2Ent_Cmd_switch_var, 'Enter2Ent_Cmd'))

# right column stuff commands
forced_numpad_switch.config(
    command=lambda: save_switch_settings(
        cnfg, forced_numpad_switch_var, 'forced_numpad'))
media_arrows_fix_switch.config(
    command=lambda: save_switch_settings(
        cnfg, media_arrows_fix_switch_var, 'media_arrows_fix'))
optspec_US_radio_btn.config(command=lambda: save_radio_settings(cnfg, optspec_var, "optspec_layout"))
optspec_ABC_radio_btn.config(command=lambda: save_radio_settings(cnfg, optspec_var, "optspec_layout"))
optspec_Disabled_radio_btn.config(command=lambda: save_radio_settings(cnfg, optspec_var, "optspec_layout"))


# END of Switches and description labels for options
###############################################################################

theme_switch_var = tk.BooleanVar(value=True)
theme_switch = ttk.Checkbutton(
    mid_right_column, 
    text='Dark Theme', 
    style='Switch.TCheckbutton',
    variable=theme_switch_var, 
    # command=sv_ttk.toggle_theme
)
theme_switch.pack(side=tk.BOTTOM, anchor=tk.SE, padx=10, pady=10)

theme_switch.config(
    command=lambda: (
        save_switch_settings(cnfg, theme_switch_var, 'gui_dark_theme'),
        sv_ttk.toggle_theme(),
    )
)

load_switch_settings(cnfg)
load_radio_btn_settings(cnfg, optspec_var, "optspec_layout")
load_radio_btn_settings(cnfg, capslock_mode_var, "capslock_mode")


def update_minsize():
    # update the layout and size of the window, or root.minsize will not work
    root.update_idletasks()
    # set the minimum resizable size to the initially created size of the window
    root.minsize(root.winfo_width(), root.winfo_height())
# root.after(100, update_minsize())

# No need to let the user resize the window - makes minsize setting kind of redundant
root.resizable(False, False)

# Make the window respond properly to Ctrl+W (Cmd+W when keymapper config is active)
root.bind("<Control-w>", lambda event: root.destroy())


def main():
    global process_mgr
    process_mgr = ProcessManager(TOSHY_PART, TOSHY_PART_NAME)
    process_mgr.initialize()

    def on_settings_changed():
        """Callback for when settings change - queue GUI update."""
        gui_update_queue.put("update_settings")

    def on_service_status_changed(config_status, session_monitor_status):
        """Callback for when service status changes - queue GUI update."""
        gui_update_queue.put(("service_status", config_status, session_monitor_status))

    settings_monitor = SettingsMonitor(cnfg, on_settings_changed)
    service_monitor = ServiceMonitor(on_service_status_changed)

    if shutil.which('systemctl') and runtime.is_systemd:
        # Help out the config file user service - only import existing env vars
        env_vars_to_check = [
            "KDE_SESSION_VERSION",
            # "PATH",               # Might be causing problem with venv injection in PATH everywhere
            "XDG_SESSION_TYPE",
            "XDG_SESSION_DESKTOP",
            "XDG_CURRENT_DESKTOP", 
            "DESKTOP_SESSION",
            "DISPLAY",
            "WAYLAND_DISPLAY",
        ]
        
        existing_vars = [var for var in env_vars_to_check if var in os.environ]
        
        if existing_vars:
            cmd_lst = ["systemctl", "--user", "import-environment"] + existing_vars
            subprocess.run(cmd_lst)
        
        service_monitor.start_monitoring()

    settings_monitor.start_monitoring()

    # Force the window to process pending tasks and calculate its dimensions
    root.update_idletasks()

    # Get the window size
    window_width = root.winfo_width()
    window_height = root.winfo_height()

    # Get the screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate the offsets to center the window
    offset_x = (screen_width - window_width) // 2
    offset_y = (screen_height - window_height) // 3

    # Apply the offsets
    root.geometry(f"+{offset_x}+{offset_y}")

    # For thread safety, update GUI only from main thread
    # Place before root.mainloop():
    root.after(100, process_gui_queue)

    # This actually creates the tkinter GUI window, runs until window is closed
    # Nothing below this should be able to run until root window is closed
    root.mainloop()

# debug(f'###  Exiting Toshy Preferences app.  ###')


if __name__ == "__main__":
    main()
