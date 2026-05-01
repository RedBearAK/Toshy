__version__ = '20260201'

import shutil
import subprocess

from subprocess import DEVNULL
from toshy_common.logger import debug



class NotificationManager:
    def __init__(self, icon_file=None, title=None, urgency='normal'):
        self.is_p_option_supported = self.check_p_option()
        self.ntfy_cmd       = shutil.which('notify-send')
        self.prio_arg       = f'--urgency={urgency}'
        self.icon_arg       = '' if icon_file is None else f'--icon={icon_file}'
        self.app_name_arg   = '--app-name=Toshy'
        self.title_arg      = "" if title is None else title
        self.ntfy_id_new    = None
        self.ntfy_id_last   = '0'

    # @staticmethod
    # def check_p_option():
    #     """check that notify-send command supports -p flag"""
    #     try:
    #         subprocess.run(['notify-send', '-p'], check=True, capture_output=True)
    #     except subprocess.CalledProcessError as e:
    #         # Check if the error message contains "Unknown option" for -p flag
    #         error_output: bytes = e.stderr  # type hint to validate decode()
    #         if 'Unknown option' in error_output.decode('utf-8'):
    #             return False
    #     return True

    @staticmethod
    def check_p_option():
        """check that notify-send command supports -p flag"""
        if not shutil.which('notify-send'):
            return False
        try:
            subprocess.run(['notify-send', '-p'], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            error_output: bytes = e.stderr
            if 'Unknown option' in error_output.decode('utf-8'):
                return False
        return True

    def send_notification(self, message: str, icon_file: str=None, 
                                urgency: str=None, replace_previous=True):
        """Show a notification with given message and icon.
            Replace existing notification unless argument is false."""

        # Prevent exception from missing 'notify-send' command.
        if not self.ntfy_cmd:
            return

        _icon_arg = self.icon_arg if icon_file is None else f'--icon={icon_file}'
        _prio_arg = self.prio_arg if urgency is None else f'--urgency={urgency}'
        if self.is_p_option_supported and replace_previous:
            _ntfy_id_new = subprocess.run(
                [self.ntfy_cmd, _prio_arg, self.app_name_arg,
                    _icon_arg, self.title_arg,
                    message, '-p','-r', self.ntfy_id_last],
                stdout=subprocess.PIPE).stdout # .decode().strip()
            _ntfy_id_new: bytes     # type hint to help VSCode validate the ".decode().strip()"
            self.ntfy_id_new = _ntfy_id_new.decode().strip()
            self.ntfy_id_last = self.ntfy_id_new
        else:
            subprocess.run([self.ntfy_cmd, self.app_name_arg, 
                            _prio_arg, _icon_arg, self.title_arg, message])

    def forced_numpad(self, state):
        """Show a notification when Forced Numpad feature is enabled/disabled."""
        if state:
            message = ( 'Forced Numpad feature is now ENABLED.' +
                        '\rNumlock becomes "Clear" key (Escape).' +
                        '\rDisable with Opt+NumLock or Fn+NumLock.')
        else:
            message = ( 'Forced Numpad feature is now DISABLED.' +
                        '\rRe-enable with Opt+NumLock or Fn+NumLock.')
        self.send_notification(message, None, None, False)

    def apple_logo(self):
        """Show a notification about needing specific font for displaying Apple logo"""
        message = 'Apple logo requires "Baskerville Old Face" font.'
        self.send_notification(message, urgency='critical')
