#!/usr/bin/env python3
__version__ = '20250710'

# NOTE: This new context module for monitoring keyboard-mouse sharing software was
# originally produced by Claude 3.7 Sonnet, based on the window_context module in
# the keymapper (xwaykeyz) as a template. [2025-02-25]

import os
import re
import abc
import time
import socket
import platform
import subprocess

from typing import Dict, List, Optional, Set, Callable, Tuple
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from toshy_common.logger import debug, error, warn


class SharedDeviceMonitorInterface(abc.ABC):
    """Abstract base class for all shared device monitor classes"""

    @classmethod
    @abc.abstractmethod
    def get_supported_software(cls):
        """
        Returns a list of software names this monitor supports.

        :returns: A list of strings, each representing a software name
                    (e.g., 'synergy', 'input-leap', 'deskflow')
        """
        pass

    @abc.abstractmethod
    def is_running(self):
        """
        Checks if the software is currently running.

        :returns: True if the software is running, False otherwise
        """
        pass

    @abc.abstractmethod
    def get_log_file_path(self):
        """
        Returns the path to the log file for this software.

        :returns: String path to the log file, or None if not available
        """
        pass

    @abc.abstractmethod
    def parse_log_line(self, line: str) -> Optional[bool]:
        """
        Parses a line from the log file to determine if it indicates a focus change.

        :param line: A line from the log file
        :returns: True if focus entered, False if focus left, None if not a focus change event
        """
        pass

    @abc.abstractmethod
    def is_server(self) -> bool:
        """
        Determines if this system is running as a server/host for the shared device software.

        :returns: True if this is a server, False if it's a client or undetermined
        """
        pass

    def get_active_log_file_paths(self, max_age_hours=8) -> List[Tuple[str, float]]:
        """
        Returns all existing log file paths sorted by likelihood of being active.

        :param max_age_hours: Maximum age in hours for a log to be considered possibly active
        :returns: List of tuples (path, score) sorted by score (higher is more likely active)
        """
        log_files = []

        # Check all possible paths
        for path in self.log_paths:
            if not os.path.exists(path):
                continue

            # Base score on file modification time (newer is better)
            try:
                mod_time = os.path.getmtime(path)
                age_hours = (time.time() - mod_time) / 3600

                # If file is very old, give it a low score but still include it
                if age_hours > max_age_hours:
                    score = 0.1  # Very low but non-zero score
                    debug(f"Log file {path} is old (modified {age_hours:.1f} hours ago)")
                else:
                    # Score based on recency (newer files get higher scores)
                    # 1.0 for just modified, approaching 0.1 as age approaches max_age_hours
                    score = 1.0 - (0.9 * age_hours / max_age_hours)

                # Check file size - very small files might be inactive
                size = os.path.getsize(path)
                if size < 100:  # Less than 100 bytes
                    score *= 0.5  # Reduce score for very small files

                # Check for recent timestamps inside the file
                recent_activity_score = self.check_log_file_activity(path, max_age_hours)
                if recent_activity_score > 0:
                    # Boost score if we found recent timestamps
                    score = max(score, recent_activity_score)

                log_files.append((path, score))
            except Exception as e:
                error(f"Error checking log file {path}: {e}")

        # Sort by score (descending)
        return sorted(log_files, key=lambda x: x[1], reverse=True)

    def check_log_file_activity(self, log_path, max_age_hours=8) -> float:
        """
        Check if log file contains recent entries and return an activity score.

        :param log_path: Path to the log file
        :param max_age_hours: Maximum age in hours for log entries to be considered recent
        :returns: Activity score between 0.0 (inactive) and 1.0 (very active)
        """
        try:
            with open(log_path, 'r') as f:
                # Read last 20 lines
                f.seek(0, os.SEEK_END)
                file_size = f.tell()

                # If file is empty, return 0
                if file_size == 0:
                    return 0.0

                # Read at most the last 4KB
                read_size = min(4096, file_size)
                f.seek(file_size - read_size)
                chunk = f.read(read_size)

                # Get last 20 lines
                lines = chunk.splitlines()[-20:]

            newest_timestamp = None

            for line in lines:
                timestamp_match = re.search(r'(?:.*\[|\[)?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\])?', line)
                if timestamp_match:
                    line_time_str = timestamp_match.group(1)
                    try:
                        format_str = "%Y-%m-%d %H:%M:%S" if " " in line_time_str else "%Y-%m-%dT%H:%M:%S"
                        line_time = time.strptime(line_time_str, format_str)
                        line_timestamp = time.mktime(line_time)

                        if newest_timestamp is None or line_timestamp > newest_timestamp:
                            newest_timestamp = line_timestamp
                    except ValueError:
                        pass

            if newest_timestamp is None:
                debug(f"No valid timestamps found in log file {log_path}")
                return 0.1  # Very low but non-zero score

            # Calculate age in hours
            age_hours = (time.time() - newest_timestamp) / 3600

            if age_hours <= max_age_hours:
                # Score based on recency (1.0 for just now, approaching 0.1 as age approaches max_age_hours)
                score = 1.0 - (0.9 * age_hours / max_age_hours)
                return score
            else:
                debug(f"Log file {log_path} has no recent entries (newest is {age_hours:.1f} hours old)")
                return 0.0
        except Exception as e:
            error(f"Error checking log file activity: {e}")
            return 0.0


class DeskflowMonitor(SharedDeviceMonitorInterface):
    """Monitor for Deskflow software (upstream project of Synergy)"""

    def __init__(self):
        self.process_names = ['deskflow', 'deskflows', 'deskflowc']
        self.server_process_names = ['deskflows', 'deskflow']  # 'deskflow' might be both
        self.client_process_names = ['deskflowc', 'deskflow']  # 'deskflow' might be both
        self.log_paths = [
            # Observed in the wild
            os.path.expanduser("~/deskflow.log"),
            # Additional guesses
            os.path.expanduser("~/.local/state/Deskflow/deskflow.log"),
            os.path.expanduser("~/.local/share/Deskflow/deskflow.log"),
            os.path.expanduser("~/.config/Deskflow/deskflow.log"),
            "/var/log/deskflow.log",
        ]
        self._server_status = None  # Cache for server status

    @classmethod
    def get_supported_software(cls):
        return ['deskflow']

    def is_running(self):
        """Check if any Deskflow process is running"""
        for process_name in self.process_names:
            try:
                result = subprocess.run(['pgrep', '-x', process_name], 
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    return True
            except subprocess.SubprocessError:
                pass
        return False

    def get_log_file_path(self):
        """Return the first existing log file path"""
        active_logs = self.get_active_log_file_paths()
        if active_logs:
            path, score = active_logs[0]
            if score < 0.5:
                warn(f"Log file {path} seems to be inactive (activity score: {score:.2f})")
            return path
        return None

    def parse_log_line(self, line: str) -> Optional[bool]:
        """Parse Deskflow log line for focus events"""
        if "leaving screen" in line.lower():
            return False
        elif "entering screen" in line.lower():
            return True
        return None

    def is_server(self) -> bool:
        """
        Determine if this system is running Deskflow as a server.

        Checks:
        1. If 'deskflows' process is running
        2. If log file contains server initialization messages
        3. If 'deskflow' is running with server arguments

        Returns True if any check suggests this is a server, False otherwise.
        """
        if self._server_status is not None:
            return self._server_status

        # Check if server process is running
        for process_name in self.server_process_names:
            try:
                # Use -f flag to match full command line arguments for 'deskflow'
                cmd = 'pgrep' 
                args = ['-x', process_name] if process_name == 'deskflows' else ['-f', f'(^|/){process_name}.*--server']
                result = subprocess.run([cmd] + args, capture_output=True, text=True)
                if result.returncode == 0:
                    self._server_status = True
                    debug("Deskflow server process detected")
                    return True
            except subprocess.SubprocessError:
                pass

        # Check if only client process is running (definitively a client)
        client_only = False
        for process_name in self.client_process_names:
            try:
                cmd = 'pgrep'
                args = ['-x', process_name] if process_name == 'deskflowc' else ['-f', f'(^|/){process_name}.*--client']
                result = subprocess.run([cmd] + args, capture_output=True, text=True)
                if result.returncode == 0:
                    client_only = True
                    break
            except subprocess.SubprocessError:
                pass

        if client_only:
            self._server_status = False
            debug("Deskflow client process detected")
            return False

        # Check log file for server messages
        log_path = self.get_log_file_path()
        if log_path and os.path.exists(log_path):
            try:
                file_size = os.path.getsize(log_path)
                if file_size < 50:  # Less than 50 bytes
                    warn(f"Found empty/minimal log file: {log_path}. Server detection may be unreliable.")

                # Only check the first 50 lines for server initialization messages
                with open(log_path, 'r') as f:
                    lines = [f.readline() for _ in range(50)]
                    for line in lines:
                        if ("server started" in line.lower() or 
                            "started server" in line.lower() or
                            "accepted client connection" in line.lower() or
                            "waiting for clients" in line.lower()):
                            self._server_status = True
                            debug("Deskflow server detected from log file")
                            return True
            except Exception as e:
                error(f"Error reading Deskflow log file: {e}")

        # Default assumption: if Deskflow is running but we couldn't determine, assume client
        self._server_status = False
        return False


class SynergyMonitor(SharedDeviceMonitorInterface):
    """Monitor for Synergy software"""

    def __init__(self):
        self.process_names = ['synergy', 'synergys', 'synergyc', 'synergy-core']
        self.server_process_names = ['synergys', 'synergy', 'synergy-core']  # 'synergy' can be both
        self.client_process_names = ['synergyc', 'synergy', 'synergy-core']  # 'synergy' can be both
        self.log_paths = [
            # Observed in the wild
            os.path.expanduser("~/.local/state/Synergy/synergy.log"),
            # Additional possibilities
            os.path.expanduser("~/.local/share/Synergy/synergy.log"),
            os.path.expanduser("~/.config/Synergy/synergy.log"),
            os.path.expanduser("~/synergy.log"),
            # Older versions
            os.path.expanduser("~/.synergy/synergy.log"),
        ]
        self._server_status = None  # Cache for server status

    @classmethod
    def get_supported_software(cls):
        return ['synergy']

    def is_running(self):
        """Check if any Synergy process is running"""
        for process_name in self.process_names:
            try:
                result = subprocess.run(['pgrep', '-x', process_name], 
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    return True
            except subprocess.SubprocessError:
                pass
        return False

    def get_log_file_path(self):
        """Return the first existing log file path"""
        active_logs = self.get_active_log_file_paths()
        if active_logs:
            path, score = active_logs[0]
            if score < 0.5:
                warn(f"Log file {path} seems to be inactive (activity score: {score:.2f})")
            return path
        return None

    def parse_log_line(self, line: str) -> Optional[bool]:
        """Parse Synergy log line for focus events"""
        if "leaving screen" in line.lower():
            return False
        elif "entering screen" in line.lower():
            return True
        return None

    def is_server(self) -> bool:
        """
        Determine if this system is running Synergy as a server.

        Checks:
        1. If 'synergys' process is running
        2. If log file contains server initialization messages
        3. If configuration is set up for server mode

        Returns True if any check suggests this is a server, False otherwise.
        """
        if self._server_status is not None:
            return self._server_status

        # Check if server process is running
        for process_name in self.server_process_names:
            try:
                # Use -f flag to match full command line arguments
                result = subprocess.run(['pgrep', '-f', f'(^|/){process_name}.*server'], 
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    self._server_status = True
                    debug("Synergy server process detected")
                    return True
            except subprocess.SubprocessError:
                pass

        # Check if only client process is running (definitively a client)
        client_only = False
        for process_name in self.client_process_names:
            try:
                result = subprocess.run(['pgrep', '-f', f'(^|/){process_name}.*client'], 
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    client_only = True
                    break
            except subprocess.SubprocessError:
                pass

        if client_only:
            self._server_status = False
            debug("Synergy client process detected")
            return False

        # Check log file for server messages
        log_path = self.get_log_file_path()
        if log_path and os.path.exists(log_path):
            try:
                file_size = os.path.getsize(log_path)
                if file_size < 50:  # Less than 50 bytes
                    warn(f"Found empty/minimal log file: {log_path}. Server detection may be unreliable.")

                # Only check the first 50 lines for server initialization messages
                with open(log_path, 'r') as f:
                    lines = [f.readline() for _ in range(50)]
                    for line in lines:
                        if ("server started" in line.lower() or 
                            "started server" in line.lower() or
                            "accepted client connection" in line.lower() or
                            "waiting for clients" in line.lower()):
                            self._server_status = True
                            debug("Synergy server detected from log file")
                            return True
            except Exception as e:
                error(f"Error reading Synergy log file: {e}")

        # Default assumption: if Synergy is running but we couldn't determine, assume client
        self._server_status = False
        return False


class InputLeapMonitor(SharedDeviceMonitorInterface):
    """Monitor for Input Leap software (open source fork of Barrier)"""

    def __init__(self):
        self.process_names = ['input-leap', 'input-leaps', 'input-leapc']
        self.server_process_names = ['input-leaps', 'input-leap']  # 'input-leap' might be both
        self.client_process_names = ['input-leapc', 'input-leap']  # 'input-leap' might be both
        self.log_paths = [
            # Most likely locations based on observed patterns
            "/var/log/input-leap.log",
            os.path.expanduser("~/input-leap.log"),
            # Additional guesses
            os.path.expanduser("~/.local/state/InputLeap/input-leap.log"),
            os.path.expanduser("~/.local/share/InputLeap/input-leap.log"),
            os.path.expanduser("~/.config/InputLeap/input-leap.log"),
        ]
        self._server_status = None  # Cache for server status

    @classmethod
    def get_supported_software(cls):
        return ['input-leap']

    def is_running(self):
        """Check if any Input Leap process is running"""
        for process_name in self.process_names:
            try:
                result = subprocess.run(['pgrep', '-x', process_name], 
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    return True
            except subprocess.SubprocessError:
                pass
        return False

    def get_log_file_path(self):
        """Return the first existing log file path"""
        active_logs = self.get_active_log_file_paths()
        if active_logs:
            path, score = active_logs[0]
            if score < 0.5:
                warn(f"Log file {path} seems to be inactive (activity score: {score:.2f})")
            return path
        return None

    def parse_log_line(self, line: str) -> Optional[bool]:
        """Parse Input Leap log line for focus events"""
        if "leaving screen" in line.lower():
            return False
        elif "entering screen" in line.lower():
            return True
        return None

    def is_server(self) -> bool:
        """
        Determine if this system is running Input Leap as a server.

        Checks:
        1. If 'input-leaps' process is running
        2. If log file contains server initialization messages
        3. If 'input-leap' is running with server arguments

        Returns True if any check suggests this is a server, False otherwise.
        """
        if self._server_status is not None:
            return self._server_status

        # Check if server process is running
        for process_name in self.server_process_names:
            try:
                # Use -f flag to match full command line arguments for 'input-leap'
                cmd = 'pgrep' 
                args = ['-x', process_name] if process_name == 'input-leaps' else ['-f', f'(^|/){process_name}.*--server']
                result = subprocess.run([cmd] + args, capture_output=True, text=True)
                if result.returncode == 0:
                    self._server_status = True
                    debug("Input Leap server process detected")
                    return True
            except subprocess.SubprocessError:
                pass

        # Check if only client process is running (definitively a client)
        client_only = False
        for process_name in self.client_process_names:
            try:
                cmd = 'pgrep'
                args = ['-x', process_name] if process_name == 'input-leapc' else ['-f', f'(^|/){process_name}.*--client']
                result = subprocess.run([cmd] + args, capture_output=True, text=True)
                if result.returncode == 0:
                    client_only = True
                    break
            except subprocess.SubprocessError:
                pass

        if client_only:
            self._server_status = False
            debug("Input Leap client process detected")
            return False

        # Check log file for server messages
        log_path = self.get_log_file_path()
        if log_path and os.path.exists(log_path):
            try:
                file_size = os.path.getsize(log_path)
                if file_size < 50:  # Less than 50 bytes
                    warn(f"Found empty/minimal log file: {log_path}. Server detection may be unreliable.")

                # Only check the first 50 lines for server initialization messages
                with open(log_path, 'r') as f:
                    lines = [f.readline() for _ in range(50)]
                    for line in lines:
                        if ("server started" in line.lower() or 
                            "started server" in line.lower() or
                            "accepted client connection" in line.lower() or
                            "waiting for clients" in line.lower()):
                            self._server_status = True
                            debug("Input Leap server detected from log file")
                            return True
            except Exception as e:
                error(f"Error reading Input Leap log file: {e}")

        # Default assumption: if Input Leap is running but we couldn't determine, assume client
        self._server_status = False
        return False


class BarrierMonitor(SharedDeviceMonitorInterface):
    """
    Monitor for Barrier software

    Note: This implementation is based on expected similarities with Input Leap,
    as Input Leap is a fork of Barrier. The log parsing may need refinement
    if Barrier's logging format differs significantly.
    """

    def __init__(self):
        self.process_names = ['barrier', 'barriers', 'barrierc', 'barrier-daemon']
        self.server_process_names = ['barriers', 'barrier', 'barrier-daemon']  # 'barrier' might be both
        self.client_process_names = ['barrierc', 'barrier', 'barrier-daemon']  # 'barrier' might be both
        self.log_paths = [
            # Most likely locations based on observed patterns in similar software
            "/var/log/barrier.log",
            os.path.expanduser("~/barrier.log"),
            # Standard XDG paths
            os.path.expanduser("~/.local/state/Barrier/barrier.log"),
            os.path.expanduser("~/.local/share/Barrier/barrier.log"),
            os.path.expanduser("~/.config/Barrier/barrier.log"),
            # Application-specific paths
            os.path.expanduser("~/.barrier/barrier.log"),
            # Case variations
            os.path.expanduser("~/.Barrier/barrier.log"),
            # Potential paths with version numbers
            os.path.expanduser("~/.barrier/barrier-2.log"),
            os.path.expanduser("~/.local/share/barrier/barrier.log"),
        ]
        self._server_status = None  # Cache for server status

    @classmethod
    def get_supported_software(cls):
        return ['barrier']

    def is_running(self):
        """Check if any Barrier process is running"""
        for process_name in self.process_names:
            try:
                result = subprocess.run(['pgrep', '-x', process_name], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return True
            except subprocess.SubprocessError:
                pass
        return False

    def get_log_file_path(self):
        """Return the first existing log file path"""
        active_logs = self.get_active_log_file_paths()
        if active_logs:
            path, score = active_logs[0]
            if score < 0.5:
                warn(f"Log file {path} seems to be inactive (activity score: {score:.2f})")
            return path
        return None

    def parse_log_line(self, line: str) -> Optional[bool]:
        """
        Parse Barrier log line for focus events

        Assumes logging format similar to Input Leap and Synergy.
        May need adjustment if actual format differs.
        """
        if "leaving screen" in line.lower():
            return False
        elif "entering screen" in line.lower():
            return True
        return None

    def is_server(self) -> bool:
        """
        Determine if this system is running Barrier as a server.

        Checks:
        1. If 'barriers' process is running
        2. If log file contains server initialization messages
        3. If 'barrier' is running with server arguments

        Returns True if any check suggests this is a server, False otherwise.
        """
        if self._server_status is not None:
            return self._server_status

        # Check if server process is running
        for process_name in self.server_process_names:
            try:
                # Use -f flag to match full command line arguments for 'barrier'
                cmd = 'pgrep' 
                args = ['-x', process_name] if process_name == 'barriers' else ['-f', f'(^|/){process_name}.*--server']
                result = subprocess.run([cmd] + args, capture_output=True, text=True)
                if result.returncode == 0:
                    self._server_status = True
                    debug("Barrier server process detected")
                    return True
            except subprocess.SubprocessError:
                pass

        # Check if only client process is running (definitively a client)
        client_only = False
        for process_name in self.client_process_names:
            try:
                cmd = 'pgrep'
                args = ['-x', process_name] if process_name == 'barrierc' else ['-f', f'(^|/){process_name}.*--client']
                result = subprocess.run([cmd] + args, capture_output=True, text=True)
                if result.returncode == 0:
                    client_only = True
                    break
            except subprocess.SubprocessError:
                pass

        if client_only:
            self._server_status = False
            debug("Barrier client process detected")
            return False

        # Check log file for server messages
        log_path = self.get_log_file_path()
        if log_path and os.path.exists(log_path):
            try:
                file_size = os.path.getsize(log_path)
                if file_size < 50:  # Less than 50 bytes
                    warn(f"Found empty/minimal log file: {log_path}. Server detection may be unreliable.")

                # Only check the first 50 lines for server initialization messages
                with open(log_path, 'r') as f:
                    lines = [f.readline() for _ in range(50)]
                    for line in lines:
                        if ("server started" in line.lower() or 
                            "started server" in line.lower() or
                            "accepted client connection" in line.lower() or
                            "waiting for clients" in line.lower()):
                            self._server_status = True
                            debug("Barrier server detected from log file")
                            return True
            except Exception as e:
                error(f"Error reading Barrier log file: {e}")

        # Default assumption: if Barrier is running but we couldn't determine, assume client
        self._server_status = False
        return False


class LogWatcherHandler(FileSystemEventHandler):
    """Handler for log file changes"""

    def __init__(self, log_path: str, parse_func: Callable[[str], Optional[bool]], 
                    on_focus_change: Callable[[bool], None]):
        super().__init__()
        self.log_path = log_path
        self.parse_func = parse_func
        self.on_focus_change = on_focus_change
        self.last_position = 0
        self.initialized = False
        self.startup_time = time.time()
        self.last_activity_time = None
        self.activity_counter = 0

    def on_modified(self, event: FileSystemEvent):
        if event.src_path == self.log_path:
            self.handle_log_file_change()

    def on_created(self, event: FileSystemEvent):
        if event.src_path == self.log_path:
            self.handle_log_file_change()

    def handle_log_file_change(self):
        if not os.path.exists(self.log_path):
            return

        with open(self.log_path, 'r') as f:
            if not self.initialized:
                # On first run, seek to the end of the file
                # We'll ignore all historical log entries and assume focus is on this screen
                f.seek(0, os.SEEK_END)
                self.last_position = f.tell()
                self.initialized = True
                # Default to having focus at startup
                self.on_focus_change(True)
                return
            else:
                f.seek(self.last_position)

            lines = f.readlines()
            new_position = f.tell()

            # If we got new content, update last activity time
            if new_position > self.last_position:
                self.last_activity_time = time.time()
                self.activity_counter += 1

            self.last_position = new_position

            # Process lines to find focus changes
            most_recent_state = None
            newest_timestamp = None

            for line in lines:
                line_to_process = line.strip()

                # Try to extract a timestamp from the log line
                timestamp_match = re.search(r'(?:.*\[|\[)?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\])?', line_to_process)

                if timestamp_match:
                    line_time_str = timestamp_match.group(1)
                    try:
                        # Handle both formats: '2025-02-24 18:13:23' and '2025-02-24T18:13:23'
                        format_str = "%Y-%m-%d %H:%M:%S" if " " in line_time_str else "%Y-%m-%dT%H:%M:%S"
                        line_time = time.strptime(line_time_str, format_str)
                        line_timestamp = time.mktime(line_time)

                        # Update newest timestamp
                        if newest_timestamp is None or line_timestamp > newest_timestamp:
                            newest_timestamp = line_timestamp

                        # Ignore entries from before we started monitoring
                        if line_timestamp < self.startup_time:
                            debug(f"Ignoring focus event from before monitor startup: {line_to_process}")
                            continue
                    except ValueError:
                        # If we can't parse the timestamp, process the line anyway
                        pass

                # Process the line for focus change events
                state = self.parse_func(line_to_process)
                if state is not None:
                    most_recent_state = state

            # If we found a focus change, notify the callback
            if most_recent_state is not None:
                self.on_focus_change(most_recent_state)

    def is_active(self, max_inactive_hours=8) -> bool:
        """
        Check if this log file shows signs of activity.

        :param max_inactive_hours: Maximum hours of inactivity before considering inactive
        :returns: True if the log file shows recent activity, False otherwise
        """
        if not self.last_activity_time:
            # If we've never seen activity, check based on file modification time
            try:
                mod_time = os.path.getmtime(self.log_path)
                hours_since_mod = (time.time() - mod_time) / 3600
                return hours_since_mod <= max_inactive_hours
            except Exception:
                return False

        # If we've seen activity, check how long it's been
        hours_since_activity = (time.time() - self.last_activity_time) / 3600
        return hours_since_activity <= max_inactive_hours


class SharedDeviceContext:
    """
    Manages focus tracking for shared device software (Synergy, Input Leap, Deskflow, Barrier)
    """

    def __init__(self):
        self.observer = Observer()
        self.handlers = {}
        self.monitors = []
        self.screen_has_focus = True
        self.active_monitors = set()
        self.is_server_system = False
        self.last_health_check = 0

        # Initialize all available monitors
        for monitor_class in SharedDeviceMonitorInterface.__subclasses__():
            self.monitors.append(monitor_class())

        # Log which monitors are available
        software_list = [software for monitor in self.monitors 
                        for software in monitor.get_supported_software()]
        debug(f"SharedDeviceContext initialized with support for: {', '.join(software_list)}")

    def detect_active_software(self) -> Set[str]:
        """
        Detects which shared device software is currently running

        :returns: Set of software names that are currently running
        """
        active_software = set()
        self.is_server_system = False  # Reset server status for fresh detection

        for monitor in self.monitors:
            if monitor.is_running():
                active_software.update(monitor.get_supported_software())
                # If any monitor is running as a server, mark this as a server system
                if monitor.is_server():
                    self.is_server_system = True
        return active_software

    def start_monitoring(self):
        """
        Start monitoring all active shared device software
        """
        # Detect which software is running
        active_software = self.detect_active_software()

        if not active_software:
            # Debug line is redundant with settings class debug line
            # debug("No shared device software detected")
            return

        debug(f"Detected active shared device software: {', '.join(active_software)}")

        # If we're on a client system, don't bother monitoring logs
        # Always keep screen_has_focus as True
        if not self.is_server_system:
            debug("Running as a client system - keeping keymapping enabled")
            self.screen_has_focus = True
            return

        debug("Running as a server system - monitoring focus changes")

        # Start monitoring each active software
        for monitor in self.monitors:
            supported_software = set(monitor.get_supported_software())
            if not supported_software.intersection(active_software):
                continue

            # Get all potential log files sorted by activity likelihood
            active_logs = monitor.get_active_log_file_paths()

            if not active_logs:
                warn(f"No log files found for {', '.join(supported_software)}")
                continue

            # Check if all logs have low activity scores
            all_inactive = all(score < 0.5 for _, score in active_logs)
            if all_inactive:
                warn(f"WARNING: All detected log files for {', '.join(supported_software)} appear to be inactive!")
                warn(f"Focus detection may not work correctly. Check software configuration.")

            # If we have multiple potential log files, log them with their scores
            if len(active_logs) > 1:
                debug(f"Found multiple potential log files for {', '.join(supported_software)}:")
                for path, score in active_logs:
                    debug(f"  - {path} (activity score: {score:.2f})")

            # Monitor all potential log files, but prefer the most likely active ones
            for log_path, score in active_logs:
                log_dir = os.path.dirname(log_path)
                if not os.path.exists(log_dir):
                    warn(f"Log directory does not exist: {log_dir}")
                    continue

                # Create a handler for this log file
                handler = LogWatcherHandler(
                    log_path=log_path,
                    parse_func=monitor.parse_log_line,
                    on_focus_change=self.on_focus_change
                )

                # Schedule the handler with the observer
                self.observer.schedule(handler, path=log_dir, recursive=False)
                self.handlers[log_path] = handler
                self.active_monitors.update(supported_software)

                if os.path.exists(log_path):
                    if score < 0.5:
                        warn(f"Monitoring possibly inactive log file: {log_path} (score: {score:.2f})")
                    else:
                        debug(f"Monitoring log file: {log_path} (score: {score:.2f})")
                else:
                    debug(f"Watching for future log file: {log_path}")

        # Start the observer if we have any handlers
        if self.handlers:
            self.observer.start()
            debug("Log file monitoring started")

            # Initialize the log handlers
            for log_path, handler in self.handlers.items():
                if os.path.exists(log_path):
                    handler.handle_log_file_change()

        # Initialize health check timer
        self.last_health_check = time.time()

    def check_health(self) -> bool:
        """
        Check if our monitoring is healthy and working properly.

        :returns: True if healthy, False if we need to refresh monitoring
        """
        # Only run health check every 5 minutes
        current_time = time.time()
        if current_time - self.last_health_check < 300:  # 5 minutes in seconds
            return True

        self.last_health_check = current_time

        # Verify monitored software is still running
        active_software = self.detect_active_software()
        if not active_software:
            debug("Health check: No active shared device software detected")
            return False

        # For servers, check if log files are still active
        if self.is_server_system:
            # Check if any handlers are showing activity
            any_active = False
            for log_path, handler in self.handlers.items():
                if os.path.exists(log_path) and handler.is_active():
                    any_active = True
                    break

            if not any_active and self.handlers:
                warn("Health check: No active log files detected, refreshing monitoring")
                warn("Focus detection may not be working! Check KVM software configuration.")
                return False

            # Check if any new log files have appeared that might be more active
            for monitor in self.monitors:
                if not set(monitor.get_supported_software()).intersection(active_software):
                    continue

                active_logs = monitor.get_active_log_file_paths()
                if active_logs:
                    top_path, top_score = active_logs[0]
                    # If we found a highly active log we're not currently monitoring, refresh
                    if top_score > 0.8 and top_path not in self.handlers:
                        debug(f"Health check: Found new active log file: {top_path}")
                        return False
        else:
            # For clients, check if we might actually be a server
            for monitor in self.monitors:
                if not monitor.is_running():
                    continue

                # Reset cached server status to force fresh detection
                monitor._server_status = None

                # If any monitor is now detected as a server, refresh monitoring
                if monitor.is_server():
                    debug(f"Health check: Detected change from client to server mode for {monitor.get_supported_software()[0]}")
                    self.is_server_system = True
                    return False  # Trigger a refresh

        return True

    def stop_monitoring(self):
        """
        Stop monitoring all shared device software
        """
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            debug("Log file monitoring stopped")

        self.handlers.clear()
        self.active_monitors.clear()

    def on_focus_change(self, has_focus: bool):
        """
        Callback function for when focus changes

        :param has_focus: True if the screen has focus, False otherwise
        """
        if has_focus != self.screen_has_focus:
            self.screen_has_focus = has_focus
            print()
            debug(f"Screen focus changed: {'entered screen' if has_focus else 'left screen'}",
                ctx="FC")

    def get_focus_state(self) -> bool:
        """
        Returns the current focus state

        :returns: True if the screen has focus, False otherwise
        """
        # Periodically check health of our monitoring
        if not self.check_health():
            debug("Health check failed, refreshing monitoring")
            self.refresh_monitoring()

        # Client systems always have focus for keymapping purposes
        if not self.is_server_system:
            return True

        return self.screen_has_focus

    def refresh_monitoring(self):
        """
        Refresh which software is being monitored
        """
        self.stop_monitoring()
        self.start_monitoring()


# For testing the module directly
if __name__ == "__main__":
    context = SharedDeviceContext()
    context.start_monitoring()

    try:
        while True:
            time.sleep(1)
            print(f"Screen has focus: {context.get_focus_state()}")
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        context.stop_monitoring()
