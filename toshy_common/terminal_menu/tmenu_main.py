"""
Toshy terminal menu ('toshy-terminal-menu' command).

toshy_common/terminal_menu/tmenu_main.py

A terminal-based counterpart to the Toshy tray icon menu, for systems
where the GTK tray/GUI apps are unavailable (no GTK packages) or
misbehaving (compositor menu bugs). Presents the same preferences,
choice groups, overlays, and service controls, with live updates:
settings changed from the tray, GUI app, or another terminal menu
instance appear here within about a second, and service status changes
update the header, via the same SettingsMonitor/ServiceMonitor
machinery the GTK apps use.

Input is keyboard plus SGR mouse reporting (click to activate, wheel
to scroll), so the menu remains fully usable with the pointer when the
keymapper itself is the thing being debugged — mouse events come from
the terminal emulator over the tty, not through evdev.

Event loop: select() on stdin plus a self-pipe. Monitor callbacks and
signal handlers only set flags and write one byte to the pipe; every
redraw and all side effects happen on the main thread. Service actions
run on a short-lived worker thread because ServiceManager methods block
for a few seconds; menu items are dimmed while one is running.

Expects to run inside the Toshy venv (the 'toshy-terminal-menu'
launcher script activates it and sets PYTHONPATH).
"""

import os
import sys
import shutil
import select
import signal
import threading


def _bootstrap_package_on_path():
    """Put the parent of the 'toshy_common' package dir on sys.path.

    The launcher exports PYTHONPATH for the absolute imports below, but
    this also makes the module runnable directly during development.
    """

    package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if not os.path.isdir(os.path.join(package_root, 'toshy_common')):
        return
    if package_root in sys.path:
        return
    sys.path.insert(0, package_root)


_bootstrap_package_on_path()

from toshy_common.runtime_utils import initialize_toshy_runtime

runtime = initialize_toshy_runtime()

import toshy_common.terminal_utils as term_utils

from toshy_common.env_context import EnvironmentInfo
from toshy_common.monitoring import ServiceMonitor, SettingsMonitor
from toshy_common.proc_launcher import launch_detached
from toshy_common.settings_class import Settings
from toshy_common.preference_items import KBTYPE_GROUP, KBTYPE_OVERRIDE_VALUES, KBTYPE_OVERRIDE_WARNING
from toshy_common.service_manager import ServiceManager
from toshy_common.notification_manager import NotificationManager
from toshy_common.terminal_menu.tmenu_term import TerminalController, get_terminal_size
from toshy_common.terminal_menu.tmenu_input import parse_input_bytes
from toshy_common.terminal_menu.tmenu_model import (
    MenuContext,
    KIND_LABEL,
    KIND_HEADING,
    build_visible_items,
    detect_gui_display,
)
from toshy_common.terminal_menu.tmenu_render import MIN_ROWS, render_frame


__version__ = '20260804'

# Icon base names, matching the tray app (files live in local-share-icons).
_ICON_ACTIVE        = 'toshy_app_icon_rainbow'
_ICON_INVERSE       = 'toshy_app_icon_rainbow_inverse'
_ICON_GRAYSCALE     = 'toshy_app_icon_rainbow_inverse_grayscale'

_ACTION_LABELS_DCT = {
    'restart_services':     'starting Toshy services',
    'stop_services':        'stopping Toshy services',
    'restart_config_only':  'starting config-only process',
    'stop_config_only':     'stopping config-only process',
}


class TerminalMenuApp:

    def __init__(self):
        self.terminal           = TerminalController()
        self.cnfg               = Settings(runtime.config_dir)
        self.cnfg.watch_database()

        self.ntfy               = NotificationManager(
            _ICON_ACTIVE, title='Toshy Alert (Terminal Menu)')
        self.service_manager    = ServiceManager(
            self.ntfy, _ICON_ACTIVE, _ICON_INVERSE, _ICON_GRAYSCALE)

        self.menu_ctx           = MenuContext(
            is_systemd=runtime.is_systemd,
            barebones_config=runtime.barebones_config,
            has_gui_display=detect_gui_display())

        self.desktop_env        = 'keymissing'
        self.de_major_version   = 'keymissing'

        self.items_lst          = []
        self.selected_id        = None
        self.viewport_top       = 0
        self.row_to_index_dct   = {}

        self.config_status      = 'Unknown'
        self.sessmon_status     = 'Unknown'

        self.message_text       = ''
        self.message_is_alert   = False
        self.busy_action        = ''

        self.wants_exit         = False
        self.wake_read_fd, self.wake_write_fd = os.pipe()
        os.set_blocking(self.wake_read_fd, False)

    # ---- wiring -------------------------------------------------------------

    def detect_environment(self):
        env_info_dct = EnvironmentInfo().get_env_info()
        self.desktop_env        = str(env_info_dct.get('DESKTOP_ENV', 'keymissing')).casefold()
        self.de_major_version   = str(env_info_dct.get('DE_MAJ_VER', 'keymissing')).casefold()

    def wake_main_loop(self):
        try:
            os.write(self.wake_write_fd, b'w')
        except OSError:
            pass

    def on_settings_changed(self):
        # cnfg has already reloaded via watch_database; just repaint.
        self.wake_main_loop()

    def on_service_status_changed(self, config_status, sessmon_status):
        self.config_status  = config_status
        self.sessmon_status = sessmon_status
        self.wake_main_loop()

    def install_signal_handlers(self):
        signal.signal(signal.SIGWINCH, lambda signum, frame: self.wake_main_loop())
        for exit_signal in (signal.SIGTERM, signal.SIGHUP):
            signal.signal(exit_signal, self._request_exit)

    def _request_exit(self, signum, frame):
        self.wants_exit = True
        self.wake_main_loop()

    # ---- selection helpers --------------------------------------------------

    def rebuild_items(self):
        self.items_lst = build_visible_items(self.cnfg, self.menu_ctx)
        if not self.items_lst:
            self.selected_id = None
            return
        if self.selected_index() is None:
            # Previous selection vanished (section collapsed by another path
            # or item removed); land on the first selectable item.
            self.selected_id = self.items_lst[self._first_selectable()].item_id

    def selected_index(self):
        for index, item in enumerate(self.items_lst):
            if item.item_id == self.selected_id:
                return index
        return None

    def _first_selectable(self):
        for index, item in enumerate(self.items_lst):
            if item.kind != KIND_LABEL:
                return index
        return 0

    def move_selection(self, step):
        if not self.items_lst:
            return
        index = self.selected_index()
        if index is None:
            index = self._first_selectable()
        next_index = index
        while True:
            next_index += 1 if step > 0 else -1
            if next_index < 0 or next_index >= len(self.items_lst):
                return
            if self.items_lst[next_index].kind != KIND_LABEL:
                break
        self.selected_id = self.items_lst[next_index].item_id

    def move_selection_page(self, direction):
        _columns, rows = get_terminal_size()
        page = max(1, rows - 9)
        for _step in range(page):
            self.move_selection(direction)

    def move_selection_edge(self, to_end):
        if not self.items_lst:
            return
        index = len(self.items_lst) - 1 if to_end else self._first_selectable()
        while to_end and index > 0 and self.items_lst[index].kind == KIND_LABEL:
            index -= 1
        self.selected_id = self.items_lst[index].item_id

    # ---- footer -------------------------------------------------------------

    def set_message(self, text, alert=False):
        self.message_text       = text
        self.message_is_alert   = alert

    def clear_message(self):
        self.message_text       = ''
        self.message_is_alert   = False

    def footer_content(self):
        if self.busy_action:
            return f'Working: {self.busy_action}...', False
        if self.message_text:
            return self.message_text, self.message_is_alert
        index = self.selected_index()
        if index is None:
            return '', False
        item = self.items_lst[index]
        if item.help_text:
            return f'{item.help_title}: {item.help_text}', False
        return '', False

    # ---- activation dispatch ------------------------------------------------

    def activate_item(self, item):
        if not item.enabled:
            if item.disabled_reason:
                self.set_message(item.disabled_reason, alert=True)
            return

        action_handlers_dct = {
            'toggle_section':       self._do_toggle_section,
            'toggle_pref':          self._do_toggle_pref,
            'set_choice':           self._do_set_choice,
            'toggle_overlay':       self._do_toggle_overlay,
            'apply_overlay_preset': self._do_apply_overlay_preset,
            'restart_services':     self._do_service_action,
            'stop_services':        self._do_service_action,
            'restart_config_only':  self._do_service_action,
            'stop_config_only':     self._do_service_action,
            'open_prefs_app':       self._do_open_prefs_app,
            'open_config_folder':   self._do_open_config_folder,
            'show_services_log':    self._do_show_services_log,
            'quit':                 self._do_quit,
        }
        handler = action_handlers_dct.get(item.action)
        if handler is None:
            return
        handler(item)

    def _do_toggle_section(self, item):
        section = item.payload
        if section in self.menu_ctx.expanded:
            self.menu_ctx.expanded.discard(section)
        else:
            self.menu_ctx.expanded.add(section)

    def _do_toggle_pref(self, item):
        attr_name = item.payload
        new_value = not bool(getattr(self.cnfg, attr_name))
        # No-change guard is inherent here (strict inversion), but reload
        # first so a near-simultaneous external change isn't clobbered.
        setattr(self.cnfg, attr_name, new_value)
        self.cnfg.save_settings()
        # Re-read committed state: the watchdog reload can race the write
        # and briefly leave stale values in memory (same reason the tray
        # queues a reload after every save).
        self.cnfg.load_settings()

    def _do_set_choice(self, item):
        attr_name, value = item.payload
        if getattr(self.cnfg, attr_name) == value:
            return
        setattr(self.cnfg, attr_name, value)
        self.cnfg.save_settings()
        self.cnfg.load_settings()
        if attr_name == KBTYPE_GROUP.attr_name and value in KBTYPE_OVERRIDE_VALUES:
            self.set_message(KBTYPE_OVERRIDE_WARNING, alert=True)
            self.ntfy.send_notification(
                KBTYPE_OVERRIDE_WARNING.replace('\n', '\r'),
                _ICON_GRAYSCALE, urgency='critical')

    def _do_toggle_overlay(self, item):
        flag = item.payload
        if self.cnfg.overlay_mask & flag:
            new_mask = self.cnfg.overlay_mask & ~flag
        else:
            new_mask = self.cnfg.overlay_mask | flag
        if new_mask == self.cnfg.overlay_mask:
            return
        # The overlay_mask setter enforces flag dependency rules.
        self.cnfg.overlay_mask = new_mask
        self.cnfg.save_settings()
        self.cnfg.load_settings()

    def _do_apply_overlay_preset(self, item):
        preset_mask = item.payload
        if self.cnfg.overlay_mask == preset_mask:
            return
        self.cnfg.overlay_mask = preset_mask
        self.cnfg.save_settings()
        self.cnfg.load_settings()

    def _do_service_action(self, item):
        if self.busy_action:
            return
        action_name = item.action
        self.busy_action        = _ACTION_LABELS_DCT.get(action_name, action_name)
        self.menu_ctx.busy      = True

        service_methods_dct = {
            'restart_services':     self.service_manager.restart_services,
            'stop_services':        self.service_manager.stop_services,
            'restart_config_only':  self.service_manager.restart_config_only,
            'stop_config_only':     self.service_manager.stop_config_only,
        }
        service_method = service_methods_dct[action_name]

        def run_and_clear():
            try:
                service_method()
            finally:
                self.busy_action    = ''
                self.menu_ctx.busy  = False
                self.wake_main_loop()

        worker = threading.Thread(target=run_and_clear, daemon=True)
        worker.start()

    def _do_open_prefs_app(self, item):
        if launch_detached(['toshy-gui']):
            self.set_message('Launched Toshy Preferences app.')
            return
        error_text = ("The 'toshy-gui' utility is missing. "
                      'Please check your installation.')
        self.set_message(error_text, alert=True)
        self.ntfy.send_notification(error_text, _ICON_INVERSE, urgency='critical')

    def _do_open_config_folder(self, item):
        opener_cmd = 'xdg-open'
        if (self.desktop_env == 'kde' and self.de_major_version == '6'
                and shutil.which('kde-open')):
            # Sometimes xdg-open is unpatched for Plasma 6 (e.g. Leap 16).
            opener_cmd = 'kde-open'
        if launch_detached([opener_cmd, runtime.config_dir]):
            self.set_message('Opening the Toshy config folder.')
            return
        error_text = ("The 'xdg-open' utility is missing. "
                      "Try installing the 'xdg-utils' package.")
        self.set_message(error_text, alert=True)
        self.ntfy.send_notification(error_text, _ICON_INVERSE, urgency='critical')

    def _do_show_services_log(self, item):
        try:
            term_utils.run_cmd_lst_in_terminal(
                ['toshy-services-log'], desktop_env=self.desktop_env)
            self.set_message('Opened the services log in a new terminal.')
        except term_utils.TerminalNotFoundError as term_err:
            self.set_message(str(term_err), alert=True)
            self.ntfy.send_notification(str(term_err), _ICON_INVERSE)

    def _do_quit(self, item):
        self.wants_exit = True

    # ---- event handling -----------------------------------------------------

    def handle_event(self, event):
        self.clear_message()

        if event[0] == 'key':
            self._handle_key(event[1])
            return
        if event[0] == 'mouse':
            self._handle_mouse(event[1], event[2], event[3])

    def _handle_key(self, key_name):
        if key_name in ('q', 'quit'):
            self.wants_exit = True
        elif key_name in ('up', 'k'):
            self.move_selection(-1)
        elif key_name in ('down', 'j'):
            self.move_selection(1)
        elif key_name == 'pgup':
            self.move_selection_page(-1)
        elif key_name == 'pgdn':
            self.move_selection_page(1)
        elif key_name == 'home':
            self.move_selection_edge(to_end=False)
        elif key_name == 'end':
            self.move_selection_edge(to_end=True)
        elif key_name in ('enter', 'space'):
            self._activate_selected()
        elif key_name in ('left', 'esc'):
            self._collapse_current_section()
        elif key_name == 'right':
            self._expand_if_heading()

    def _handle_mouse(self, kind, column, row):
        if kind == 'wheel_up':
            for _step in range(3):
                self.move_selection(-1)
            return
        if kind == 'wheel_down':
            for _step in range(3):
                self.move_selection(1)
            return
        if kind != 'press':
            return
        item_index = self.row_to_index_dct.get(row)
        if item_index is None or item_index >= len(self.items_lst):
            return
        item = self.items_lst[item_index]
        if item.kind == KIND_LABEL:
            return
        self.selected_id = item.item_id
        self.activate_item(item)

    def _activate_selected(self):
        index = self.selected_index()
        if index is None:
            return
        self.activate_item(self.items_lst[index])

    def _collapse_current_section(self):
        index = self.selected_index()
        if index is None:
            return
        section = self.items_lst[index].section
        if section not in self.menu_ctx.expanded:
            return
        self.menu_ctx.expanded.discard(section)
        self.selected_id = f'heading_{section}'

    def _expand_if_heading(self):
        index = self.selected_index()
        if index is None:
            return
        item = self.items_lst[index]
        if item.kind == KIND_HEADING and item.payload not in self.menu_ctx.expanded:
            self.menu_ctx.expanded.add(item.payload)

    # ---- main loop ----------------------------------------------------------

    def redraw(self):
        self.rebuild_items()
        selected_index = self.selected_index()
        if selected_index is None:
            selected_index = 0
        self.row_to_index_dct, self.viewport_top = render_frame(
            self.items_lst, selected_index, self.viewport_top,
            self.config_status, self.sessmon_status,
            *self.footer_content())

    def run(self):
        self.detect_environment()
        self.install_signal_handlers()

        settings_monitor = SettingsMonitor(self.cnfg, self.on_settings_changed)
        settings_monitor.start_monitoring()
        service_monitor = None
        if runtime.is_systemd and shutil.which('systemctl'):
            service_monitor = ServiceMonitor(self.on_service_status_changed)
            service_monitor.start_monitoring()

        self.terminal.enter()
        try:
            self.rebuild_items()
            self.selected_id = self.items_lst[self._first_selectable()].item_id
            self.redraw()
            self._event_loop()
        finally:
            self.terminal.restore()
            settings_monitor.stop_monitoring_thread()
            if service_monitor is not None:
                service_monitor.stop_monitoring_thread()

    def _event_loop(self):
        stdin_fd = sys.stdin.fileno()
        while not self.wants_exit:
            try:
                readable_lst, _w, _x = select.select(
                    [stdin_fd, self.wake_read_fd], [], [])
            except InterruptedError:
                readable_lst = []

            if self.wake_read_fd in readable_lst:
                self._drain_wake_pipe()

            if stdin_fd in readable_lst:
                try:
                    data = os.read(stdin_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                for event in parse_input_bytes(data):
                    self.handle_event(event)
                    if self.wants_exit:
                        break

            if not self.wants_exit:
                self.redraw()

    def _drain_wake_pipe(self):
        while True:
            try:
                data = os.read(self.wake_read_fd, 4096)
            except (BlockingIOError, OSError):
                return
            if not data:
                return


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('toshy-terminal-menu needs an interactive terminal (a TTY).')
        print('Run it inside a terminal window or console session.')
        return 1

    app = TerminalMenuApp()
    try:
        app.run()
    except Exception:
        # Restore the terminal BEFORE the traceback prints, or the report
        # lands invisibly on the alternate screen with mouse mode stuck on.
        app.terminal.restore()
        raise
    return 0


if __name__ == '__main__':
    sys.exit(main())

# End of file #
