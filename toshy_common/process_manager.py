#!/usr/bin/env python3
__version__ = '20250710'

import os
import sys
import time
import fcntl
import psutil
import shutil
import signal

from toshy_common.logger import debug, error


class ProcessManager:
    """
    Manages process control, lockfiles, and signal handling for Toshy components.
    
    Usage:
        process_mgr = ProcessManager('gui', 'Toshy Preferences app')
        process_mgr.handle_existing_process()
        process_mgr.write_pid_to_lockfile()
        
        # App runs here...
        
        # Cleanup happens automatically via signal handlers
    """
    
    def __init__(self, component_name: str, pretty_name: str = None):
        """
        Initialize process manager for a specific Toshy component.
        
        Args:
            component_name: Component identifier ('gui', 'tray', 'config')
            pretty_name: Human-readable name for logging/errors
        """
        self.component_name = component_name
        self.pretty_name = pretty_name or f'Toshy {component_name.title()} app'
        
        # Set up paths
        self.user_id = f'{os.getuid()}'
        self.run_tmp_dir = os.environ.get('XDG_RUNTIME_DIR', f'/tmp/toshy_uid{self.user_id}')
        self.toshy_run_tmp_dir = os.path.join(self.run_tmp_dir, 'toshy_runtime_cache')
        self.lock_file_dir = f'{self.toshy_run_tmp_dir}/lock'
        self.lock_file_name = f'toshy_{self.component_name}.lock'
        self.lock_file = os.path.join(self.lock_file_dir, self.lock_file_name)
        
        # Set up directories and permissions
        self._setup_directories()
        
        # Set up signal handlers
        self._setup_signal_handlers()

    def _setup_directories(self):
        """Create necessary directories and set proper permissions."""
        if not os.path.exists(self.lock_file_dir):
            try:
                os.makedirs(self.lock_file_dir, mode=0o700, exist_ok=True)
            except Exception as e:
                error(f'NON-FATAL: Problem creating lockfile directory: {self.lock_file_dir}')
                error(e)

        # Recursively set user's Toshy temp folder as only read/write by owner
        try:
            chmod_cmd = shutil.which('chmod')
            if chmod_cmd:
                os.system(f'{chmod_cmd} 0700 {self.toshy_run_tmp_dir}')
        except Exception as e:
            error(f'NON-FATAL: Problem when setting permissions on temp folder.')
            error(e)

    def _setup_signal_handlers(self):
        """Set up signal handlers for clean shutdown."""
        def signal_handler(sig, frame):
            if sig in (signal.SIGINT, signal.SIGQUIT):
                # Perform any cleanup code here before exiting
                self.remove_lockfile()
                debug(f'\nSIGINT or SIGQUIT received. Exiting {self.pretty_name}.\n')
                sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGQUIT, signal_handler)

    def get_pid_from_lockfile(self):
        """
        Read PID from lockfile if it exists.
        
        Returns:
            int: PID if found and valid, None otherwise
        """
        try:
            with open(self.lock_file, 'r') as f:
                fcntl.flock(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
                pid = int(f.read().strip())
                fcntl.flock(f, fcntl.LOCK_UN)
                return pid
        except (IOError, ValueError, PermissionError) as e:
            debug(f'NON-FATAL: No existing lockfile or lockfile could not be read:')
            debug(e)
            return None

    def write_pid_to_lockfile(self):
        """Write current process PID to lockfile."""
        try:
            with open(self.lock_file, 'w') as f:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                f.write(str(os.getpid()))
                f.flush()
                fcntl.flock(f, fcntl.LOCK_UN)
                debug(f'PID {os.getpid()} written to lockfile: {self.lock_file}')
        except (IOError, ValueError, PermissionError) as e:
            error(f'NON-FATAL: Problem writing PID to lockfile:')
            error(e)

    def remove_lockfile(self):
        """Remove the lockfile if it exists."""
        try:
            if os.path.exists(self.lock_file):
                os.unlink(self.lock_file)
                debug(f'Lockfile removed: {self.lock_file}')
        except Exception as e:
            debug(f'NON-FATAL: Problem when trying to remove lockfile.')
            debug(e)

    def terminate_process(self, pid):
        """
        Terminate a process by PID using progressively stronger signals.
        
        Args:
            pid: Process ID to terminate
            
        Raises:
            EnvironmentError: If process cannot be terminated
        """
        for sig in [signal.SIGTERM, signal.SIGKILL]:
            try:
                process = psutil.Process(pid)
            except psutil.NoSuchProcess:
                debug(f'Process {pid} no longer exists')
                time.sleep(0.5)
                return None
                
            if process.status() == psutil.STATUS_ZOMBIE:
                debug(f'Process {pid} is already a zombie')
                time.sleep(0.5)
                return None
                
            debug(f'Sending signal {sig} to process {pid}')
            os.kill(pid, sig)
            time.sleep(0.5)
            
        raise EnvironmentError(f'FATAL ERROR: Failed to close existing process with PID: {pid}')

    def handle_existing_process(self):
        """
        Check for existing process and terminate it if found.
        
        This ensures only one instance of the component runs at a time.
        """
        pid = self.get_pid_from_lockfile()
        if pid:
            debug(f'Found existing {self.component_name} process with PID {pid}, terminating...')
            self.terminate_process(pid)
        else:
            debug(f'No existing {self.component_name} process found')

    def set_process_name(self, process_name: str = None):
        """
        Set the process name visible in process lists.
        
        Args:
            process_name: Name to set, defaults to toshy-{component_name}-app
        """
        if process_name is None:
            process_name = f'toshy-{self.component_name}-app'
            
        try:
            with open('/proc/self/comm', 'w') as f:
                f.write(process_name)
            debug(f'Process name set to: {process_name}')
        except Exception as e:
            debug(f'NON-FATAL: Could not set process name: {e}')

    def initialize(self):
        """
        Complete initialization: handle existing processes, write lockfile, set process name.
        
        Call this once at the start of your application.
        """
        debug(f'Initializing {self.pretty_name}...')
        self.handle_existing_process()
        self.write_pid_to_lockfile()
        self.set_process_name()
        debug(f'{self.pretty_name} initialization complete')

    def cleanup(self):
        """
        Manual cleanup method. Usually not needed due to signal handlers.
        """
        debug(f'Cleaning up {self.pretty_name}...')
        self.remove_lockfile()
