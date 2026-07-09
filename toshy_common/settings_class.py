"""
Toshy user-preferences store.

toshy_common/settings_class.py

A single `Settings` object holds every user preference (booleans, a few
strings, the overlay bitmask, and the most-recently-used keyboard layout) and
persists them in a small SQLite database, `toshy_user_preferences.sqlite`, kept
in the config directory. That database is the only bridge between Toshy's
processes: the config/keymapper process, the tray icon, and the preferences GUI
each build their own `Settings` instance, and a change written by one is picked
up live by the others.

Interacting with it:
  - Construct once with `cnfg = Settings(config_dir_path)`. Construction creates
    the DB and tables if missing (`ensure_database_setup`) and loads the current
    values (`load_settings`).
  - Read and write preferences as plain attributes (e.g. `cnfg.forced_numpad`,
    `cnfg.mru_layout = ('us', 'default')`).
  - Call `cnfg.save_settings()` to write the current attribute values back to
    the database.
  - Call `cnfg.watch_database()` once to start a watchdog observer on the DB
    file. When any process writes the DB, `on_database_modified` fires and
    `_safe_reload` re-reads the values into this instance, so edits apply live
    without a restart. `_safe_reload` is deliberately crash-proof: it retries a
    transient "database is locked" (heavy-I/O contention) a few times and
    otherwise logs and swallows, because an exception escaping the observer
    thread would silently kill live reload for the rest of the session.
  - `watch_shared_devices()` (server side only) tracks KVM / screen-sharing
    focus and is independent of the preference storage described above.

Adding a new preference attribute means updating four places, all keyed by the
same setting-name string:
  1. `__init__` — declare the attribute with its default value, in the
     "settings defaults" block.
  2. `_save_config_preferences` — add a `(name, str(value))` row to the
     `settings` list so it is written to the DB. Store enums/ints as a plain
     string (see the `overlay_mask` `int()` wrapper for the pattern).
  3. `load_settings` — add an `elif row[0] == 'name'` branch to read it back.
     Use `setting_value` for booleans, `row[1]` for plain strings, or a custom
     conversion for anything else (see `overlay_mask`).
  4. `__str__` — add a line to the settings dump so the value appears in debug
     output.

The `mru_layouts` table is handled separately (`_save_mru_layouts` plus its own
query in `load_settings`) and does not follow the four-step pattern above.
"""

__version__ = '20260707'

import os
import time
import inspect
import sqlite3
import textwrap
import traceback

import xwaykeyz.lib.logger

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from xwaykeyz.lib.logger import debug, error, warn

from toshy_common.shared_device_context import SharedDeviceContext
from toshy_common.overlay_context import (
    OverlayFlag,
    DEFAULT_OVERLAY_MASK,
    OVL_DEPENDENCIES,
    active_flags,
)


class Settings:
    def __init__(self, config_dir_path: str = '..') -> None:
        self.config_dir_path        = config_dir_path
        self.prefs_db_file_name     = 'toshy_user_preferences.sqlite'
        self.prefs_db_file_path     = os.path.join(self.config_dir_path, self.prefs_db_file_name)
        self.first_run              = True
        self.last_settings          = None
        self.current_settings       = None
        # Get the name of the module that instantiated the class
        calling_frame               = inspect.stack()[1]
        calling_file_path           = calling_frame.filename
        calling_module              = os.path.split(calling_file_path)[1]
        self.calling_module         = calling_module

        # settings defaults
        self.autoload_tray_icon     = True                      # Default: True
        self.gui_dark_theme         = True                      # Default: True     # Older tkinter GUI
        self.gui_theme_mode         = 'auto'                    # Default: True     # Newer GTK-4 GUI
        self.override_kbtype        = 'Auto-Adapt'              # Default: 'Auto-Adapt'

        # Overlay system — bitmask of OverlayFlag values controlling which
        # groups of keymaps and modmaps are active. See toshy_common/overlay_context.py.
        self._overlay_mask          = DEFAULT_OVERLAY_MASK

        ###  Disable optspec_layout by default for performance, and international keyboard users
        self.optspec_layout         = 'Disabled'                # Default: 'Disabled'
        self.mru_layout             = ('us', 'default')         # Default: ('us', 'default')

        self.forced_numpad          = True                      # Default: True
        self.altgr_on_menu_key      = True                      # Default: True
        self.media_arrows_fix       = False                     # Default: False
        self.multi_lang             = False                     # Default: False
        self.Caps2Cmd               = False                     # Default: False
        self.Caps2Esc_Cmd           = False                     # Default: False
        self.Enter2Ent_Cmd          = False                     # Default: False
        self.ST3_in_VSCode          = False                     # Default: False

        # Super tap passthrough
        self.l_cmd_is_sup_and_cmd   = False                     # Default: False
        self.l_opt_is_sup_and_opt   = False                     # Default: False

        # Shared device context
        self.screen_has_focus       = True  # True if focus is on the screen, False otherwise
        self.shared_device_context  = None  # Will be initialized later if needed

        # Make sure the database and tables are actually existing before trying to load settings
        self.ensure_database_setup()
        # Load user's custom settings from database (defaults will be saved if no DB)
        self.load_settings()

    @property
    def overlay_mask(self):
        """Current overlay flag bitmask. Returns OverlayFlag value."""
        return self._overlay_mask

    @overlay_mask.setter
    def overlay_mask(self, value):
        """Set overlay mask, automatically enforcing flag dependencies.

        Accepts OverlayFlag values or plain ints. Converts to OverlayFlag
        and applies dependency rules:
        - When a parent flag transitions off → on, its child is auto-enabled
        - When a parent flag is off, its child is forced off
        - Otherwise, the child's state is left alone (allowing manual disable
            while parent stays on)
        """
        if not isinstance(value, OverlayFlag):
            value = OverlayFlag(int(value))

        old_mask = self._overlay_mask
        new_mask = value

        for child, parent in OVL_DEPENDENCIES.items():
            parent_was_on = bool(old_mask & parent)
            parent_is_on = bool(new_mask & parent)
            if parent_is_on and not parent_was_on:
                new_mask |= child           # parent just turned on, restore child
            elif not parent_is_on:
                new_mask &= ~child          # parent off, child must be off too

        self._overlay_mask = new_mask

    def ensure_database_setup(self):
        # This will create the database file if it doesn't exist yet
        with sqlite3.connect(self.prefs_db_file_path) as db_connection:
            db_cursor = db_connection.cursor()

            # Function to check if a table exists
            def table_exists(table_name):
                """Utility function to check if a database table exists"""
                query = '''
                    SELECT name FROM sqlite_master WHERE type='table' AND name=?
                '''
                db_cursor.execute(query, (table_name,))
                return db_cursor.fetchone() is not None

            def table_is_empty(table_name):
                """Check if a database table is empty."""
                db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                return db_cursor.fetchone()[0] == 0

            # Create the table for user preferences if it does not exist
            if not table_exists("config_preferences"):
                db_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config_preferences
                    (
                        name TEXT PRIMARY KEY, 
                        value TEXT
                    )
                    ''')

            if table_is_empty("config_preferences"):
                # Save the default values, only if the table is empty
                self._save_config_preferences(db_cursor)

            # Create the table for Most Recently Used Layouts if it does not exist
            if not table_exists("mru_layouts"):
                db_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mru_layouts
                    (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        layout_code TEXT,
                        variant_code TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    ''')
                # Create a trigger to keep only the 12 most recent records
                db_cursor.execute('''
                    CREATE TRIGGER IF NOT EXISTS trg_afterInsert_trim_MRU_Rows 
                        AFTER INSERT ON mru_layouts
                    BEGIN
                        DELETE FROM mru_layouts 
                        WHERE id IN (
                            SELECT id FROM mru_layouts 
                            ORDER BY timestamp DESC
                            LIMIT -1 OFFSET 12  -- Keeps the newest 12 rows
                        );
                    END;
                ''')

            if table_is_empty("mru_layouts"):
                # Save the default values, only if the table is empty
                self._save_mru_layouts(db_cursor)

    def watch_database(self):
        # initialize observer to watch for database changes
        event_handler = FileSystemEventHandler()
        event_handler.on_modified = self.on_database_modified
        observer = Observer()
        observer.schedule(event_handler, path=self.config_dir_path, recursive=False)
        observer.start()

    def on_database_modified(self, event: 'FileSystemEvent | None'):
        # Guard first, so `event` is a concrete FileSystemEvent below.
        if event is None:
            return
        if event.src_path != self.prefs_db_file_path:
            return
        self._safe_reload()

    def _safe_reload(self, max_attempts=4, backoff_secs=0.25):
        """Reload settings without ever letting an exception escape.

        The watchdog observer calls this from its dispatch thread, and ANY
        exception that escapes the handler tears down that thread and silently
        disables live reload for the rest of the session (the failure that
        started this). So this boundary must swallow everything.

        Three tiers, most specific first:
          - OperationalError 'locked'/'busy' is the expected transient: the
            write that triggered this notification can still hold the lock, and
            during a heavy I/O storm a writer stalled on fsync can hold it for
            seconds. A few patient retries clear it (each load_settings() call
            already waits up to sqlite3's default 5s busy timeout, so the sleeps
            just add headroom on top).
          - Any other sqlite3.Error (malformed image, integrity, programming)
            is not retryable -- log it as a database error and move on.
          - Anything else is an unexpected bug: log it loudly with a traceback.
        In every case we return instead of raising, so the observer survives.
        """
        for attempt in range(1, max_attempts + 1):
            try:
                self.load_settings()
                return
            except sqlite3.OperationalError as op_err:
                err_txt = str(op_err).lower()
                db_is_busy = 'locked' in err_txt or 'busy' in err_txt
                if db_is_busy and attempt < max_attempts:
                    time.sleep(backoff_secs * attempt)
                    continue
                warn(f'_safe_reload: settings reload skipped after '
                     f'{attempt} attempt(s) (DB busy): {op_err}')
                return
            except sqlite3.Error as db_err:
                error(f'_safe_reload: settings reload skipped '
                      f'(database error): {db_err}')
                return
            except Exception:
                error(f'_safe_reload: settings reload failed; observer kept '
                      f'alive:\n{traceback.format_exc()}')
                return

    def _save_config_preferences(self, db_cursor: sqlite3.Cursor):
        sql_query = "INSERT OR REPLACE INTO config_preferences (name, value) VALUES (?, ?)"
        settings = [
            ('autoload_tray_icon',          str(self.autoload_tray_icon)),
            ('gui_dark_theme',              str(self.gui_dark_theme)),
            ('gui_theme_mode',              str(self.gui_theme_mode)),
            ('override_kbtype',             str(self.override_kbtype)),
            # int() wrapper on overlay_mask makes sure we store simple number string from enum
            ('overlay_mask',                str(int(self.overlay_mask))),
            ('optspec_layout',              str(self.optspec_layout)),
            ('forced_numpad',               str(self.forced_numpad)),
            ('altgr_on_menu_key',           str(self.altgr_on_menu_key)),
            ('media_arrows_fix',            str(self.media_arrows_fix)),
            ('multi_lang',                  str(self.multi_lang)),
            ('Caps2Cmd',                    str(self.Caps2Cmd)),
            ('Caps2Esc_Cmd',                str(self.Caps2Esc_Cmd)),
            ('Enter2Ent_Cmd',               str(self.Enter2Ent_Cmd)),
            ('l_cmd_is_sup_and_cmd',        str(self.l_cmd_is_sup_and_cmd)),
            ('l_opt_is_sup_and_opt',        str(self.l_opt_is_sup_and_opt)),
            ('ST3_in_VSCode',               str(self.ST3_in_VSCode))
        ]

        for setting_name, setting_value in settings:
            db_cursor.execute(sql_query, (setting_name, setting_value))

    def _save_mru_layouts(self, db_cursor: sqlite3.Cursor):
        sql_query = '''
            INSERT INTO mru_layouts
            (layout_code, variant_code)
            VALUES (?, ?)
        '''
        # self.mru_layout is a tuple, taking care of both fields being inserted
        db_cursor.execute(sql_query, self.mru_layout)

    def save_settings(self):
        with sqlite3.connect(self.prefs_db_file_path) as db_connection:
            db_cursor = db_connection.cursor()
            self._save_config_preferences(db_cursor)
            self._save_mru_layouts(db_cursor)
            debug("Settings saved in database using Settings class method.")

    def load_settings(self):

        with sqlite3.connect(self.prefs_db_file_path) as db_connection:
            db_cursor = db_connection.cursor()

            db_cursor.execute("SELECT * FROM config_preferences")

            rows_prefs = db_cursor.fetchall()
            for row in rows_prefs:
                # Convert the string value to a Python boolean correctly
                setting_value       = row[1].lower() == 'true'

                if True is False: pass  # dummy first `if` line so other rows line up (readability)
                elif row[0] == 'autoload_tray_icon'     : self.autoload_tray_icon   = setting_value
                elif row[0] == 'gui_dark_theme'         : self.gui_dark_theme       = setting_value

                elif row[0] == 'gui_theme_mode'         : self.gui_theme_mode       = row[1]
                elif row[0] == 'override_kbtype'        : self.override_kbtype      = row[1]

                elif row[0] == 'optspec_layout'         : self.optspec_layout       = row[1]

                elif row[0] == 'overlay_mask'           :
                    self.overlay_mask   = OverlayFlag(int(row[1]))

                elif row[0] == 'forced_numpad'          : self.forced_numpad        = setting_value
                elif row[0] == 'altgr_on_menu_key'      : self.altgr_on_menu_key    = setting_value
                elif row[0] == 'media_arrows_fix'       : self.media_arrows_fix     = setting_value
                elif row[0] == 'multi_lang'             : self.multi_lang           = setting_value
                elif row[0] == 'Caps2Cmd'               : self.Caps2Cmd             = setting_value
                elif row[0] == 'Caps2Esc_Cmd'           : self.Caps2Esc_Cmd         = setting_value
                elif row[0] == 'Enter2Ent_Cmd'          : self.Enter2Ent_Cmd        = setting_value
                elif row[0] == 'l_cmd_is_sup_and_cmd'   : self.l_cmd_is_sup_and_cmd = setting_value
                elif row[0] == 'l_opt_is_sup_and_opt'   : self.l_opt_is_sup_and_opt = setting_value
                elif row[0] == 'ST3_in_VSCode'          : self.ST3_in_VSCode        = setting_value

            db_cursor.execute('''
                SELECT layout_code, variant_code from mru_layouts 
                ORDER BY timestamp DESC 
                LIMIT 1;
                ''')

            row_mru_layout = db_cursor.fetchone()     # redundant limit since query limited to one row
            if row_mru_layout:
                # Convert MRU Layouts record columns back to a Python tuple
                self.mru_layout     = (row_mru_layout[0], row_mru_layout[1])
            else:
                self.mru_layout     = ('us', 'default')

        # Compare the current settings with the last settings, and 
        # update last_settings if they are different
        self.current_settings = self.get_settings_list()
        if self.last_settings != self.current_settings:
            self.last_settings = self.current_settings
            if not self.first_run:
                debug(f'User preferences database modified... loading new settings...')
                if xwaykeyz.lib.logger.VERBOSE:
                    debug(self, ctx="CG")   # print out the changed settings when verbose logging
            else:
                self.first_run = False

    def get_settings_list(self):
        # get all attributes from the object
        all_attributes = [  attr for attr in dir(self) 
                            if not callable(getattr(self, attr)) and 
                            not attr.startswith("__") and
                            not attr.startswith("_")                    ]

        # Filter attributes further only if a specific attribute should be ignored.
        # Removed earlier list comprehension that limited data types too much.
        filtered_attributes = all_attributes

        # create a list of tuples with attribute name and value pairs
        settings_list = [(attr, getattr(self, attr)) for attr in filtered_attributes]
        return settings_list

    def watch_shared_devices(self):
        """
        Start monitoring for shared device (network KVM switch) software 
        
        Examples of what the module supports: 
        
        - Synergy
        - Deskflow
        - Input Leap
        - Barrier

        This replaces the old Synergy-specific watching.
        """
        # Initialize the shared device context if it doesn't exist
        if self.shared_device_context is None:
            try:
                self.shared_device_context = SharedDeviceContext()
                # Set up a callback to update the screen_has_focus property
                original_on_focus_change = self.shared_device_context.on_focus_change
                
                def on_focus_change(has_focus: bool):
                    # Call the original callback
                    original_on_focus_change(has_focus)
                    # Update our screen_has_focus property
                    self.screen_has_focus = has_focus
                    # These debugging lines are kind of redundant with the output from the 
                    # shared_device_context module debug lines.
                    # if has_focus:
                    #     debug("Shared device focus returned to this screen")
                    # else:
                    #     debug("Shared device focus left this screen")
                
                # Replace the callback
                self.shared_device_context.on_focus_change = on_focus_change
                
                # Start monitoring
                self.shared_device_context.start_monitoring()
                
                if self.shared_device_context.active_monitors:
                    active_list = ", ".join(self.shared_device_context.active_monitors)
                    debug(f"Monitoring active shared device software: {active_list}")
                else:
                    debug("No shared device software detected to monitor")
            except Exception as e:
                error(f"Failed to initialize shared device context: {e}")
                self.screen_has_focus = True  # Assume focus is on the screen if monitoring fails

    def watch_synergy_log(self):
        """
        Legacy method for backward compatibility.
        Now uses the shared device context.
        """
        self.watch_shared_devices()

    def refresh_shared_device_monitoring(self):
        """
        Refresh the shared device monitoring, checking for newly started/stopped software
        """
        if self.shared_device_context is not None:
            self.shared_device_context.refresh_monitoring()

    def __str__(self):
        active_monitors = (
            ", ".join(self.shared_device_context.active_monitors)
            if self.shared_device_context and self.shared_device_context.active_monitors
            else "None"
        )
        mask_active         = active_flags(self.overlay_mask)
        mask_names_str      = ', '.join(f.name for f in mask_active) if mask_active else '(none)'
        
        # Wrap to fit within the visual budget. The continuation indent matches the
        # value-column position so wrapped lines align under the first chunk.
        wrap_width = 76
        indent = ' ' * 12  # adjust to match desired continuation indent
        wrapped = textwrap.wrap(mask_names_str, width=wrap_width)

        if len(wrapped) <= 1:
            # Fits on one line — keep on the same line as the field name.
            active_overlays_str = mask_names_str
        else:
            # Doesn't fit — break to next line, indent continuation chunks.
            active_overlays_str = '\n' + '\n'.join(indent + chunk for chunk in wrapped)

        return f"""Current settings:
        ------------------------------------------------------------------------------
        calling_module          = '{self.calling_module}'
        prefs_db_file_path      = '{self.prefs_db_file_path}'
        ------------------------------------------------------------------------------
        autoload_tray_icon      = {self.autoload_tray_icon}
        gui_dark_theme          = {self.gui_dark_theme}
        gui_theme_mode          = '{self.gui_theme_mode}'
        ------------------------------------------------------------------------------
        override_kbtype         = '{self.override_kbtype}'
        ------------------------------------------------------------------------------
        overlay_mask            = {self.overlay_mask}
        active_overlays         = {active_overlays_str}
        ------------------------------------------------------------------------------
        optspec_layout          = '{self.optspec_layout}'
        mru_layout              = {self.mru_layout}
        ------------------------------------------------------------------------------
        forced_numpad           = {self.forced_numpad}
        altgr_on_menu_key       = {self.altgr_on_menu_key}
        media_arrows_fix        = {self.media_arrows_fix}
        multi_lang              = {self.multi_lang}
        Caps2Cmd                = {self.Caps2Cmd}
        Caps2Esc_Cmd            = {self.Caps2Esc_Cmd}
        Enter2Ent_Cmd           = {self.Enter2Ent_Cmd}
        l_cmd_is_sup_and_cmd    = {self.l_cmd_is_sup_and_cmd}
        l_opt_is_sup_and_opt    = {self.l_opt_is_sup_and_opt}
        ST3_in_VSCode           = {self.ST3_in_VSCode}
        ------------------------------------------------------------------------------
        screen_has_focus        = {self.screen_has_focus}
        active_monitors         = {active_monitors}
        ------------------------------------------------------------------------------
        """


# End of file #
