# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Toshy is a macOS-to-Linux keyboard remapping utility that allows Linux users to use macOS-style keyboard shortcuts. It's built on top of `xwaykeyz` (a Python-based keymapper) and includes extensive support for multiple Linux distributions, desktop environments, and both X11 and Wayland sessions.

The project is designed as a "just works" monolithic solution requiring minimal user configuration while supporting automatic detection of keyboard types, desktop environments, and session types.

## ⚠️ CRITICAL: Test-Driven Development (TDD) Workflow

**This project strictly follows TDD principles. ALL code changes MUST follow this workflow:**

### The Red-Green-Refactor Cycle

**BEFORE writing ANY production code:**

1. **RED** - Write a failing test first
   - Write the minimal test that describes the desired behavior
   - Run the test to confirm it fails (and fails for the right reason)
   - Never skip this step - it validates your test setup

2. **GREEN** - Write minimal code to pass the test
   - Implement only what's needed to make the test pass
   - Avoid adding features not covered by tests
   - Run tests frequently to verify progress

3. **REFACTOR** - Improve code quality while maintaining green tests
   - Clean up duplication
   - Improve naming and structure
   - Run tests after each refactor to ensure nothing broke

**Repeat this cycle for each new behavior or feature.**

### TDD Commands (Run these frequently)

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=toshy_common --cov=toshy_gui --cov-report=term-missing

# Run specific test file
pytest tests/test_env_context.py

# Run specific test
pytest tests/test_env_context.py::TestEnvironmentInfo::test_distro_detection

# Run tests in watch mode (re-run on file changes)
pytest-watch

# Run tests with verbose output
pytest -v

# Run fast tests only (skip slow integration tests)
pytest -m "not slow"

# Run tests and stop at first failure
pytest -x

# Run last failed tests only
pytest --lf
```

### Test Coverage Requirements

- **Minimum coverage**: 80% for all new code
- **Target coverage**: 90%+ for critical modules
- All public functions MUST have tests
- All bug fixes MUST include a regression test first

### When Writing Tests

**ALWAYS:**
- Write tests BEFORE implementation code
- Test behavior, not implementation details
- Use descriptive test names: `test_should_detect_kde_plasma_when_kde_session_active`
- Follow AAA pattern: Arrange, Act, Assert
- Mock external dependencies (D-Bus, systemd, file system)
- Test edge cases and error conditions

**NEVER:**
- Write production code without a failing test first
- Skip tests because "it's just a small change"
- Commit code with failing tests
- Delete tests to make code pass
- Mock what you don't own without good reason

## Essential Development Commands

### Installation and Setup
```bash
# Install Toshy (main installation command)
./setup_toshy.py install

# Install with options
./setup_toshy.py install --fancy-pants         # Includes extra DE tweaks
./setup_toshy.py install --barebones-config    # Minimal config template
./setup_toshy.py install --override-distro distro_name

# Show available distros and environment info
./setup_toshy.py list-distros
./setup_toshy.py show-env

# Uninstall
./setup_toshy.py uninstall
```

### Service Management
```bash
# Start/stop/restart services
toshy-services-start
toshy-services-stop
toshy-services-restart
toshy-services-status       # Check current service status
toshy-services-log          # View systemd journal logs

# Enable/disable autostart
toshy-services-enable
toshy-services-disable

# Systemd service management (advanced)
toshy-systemd-setup         # Install and start systemd services
toshy-systemd-remove        # Stop and remove systemd services
```

### Config Management
```bash
# Run config manually (without systemd)
toshy-config-start          # Start keymapper
toshy-config-stop           # Stop keymapper
toshy-config-restart        # Restart keymapper

# Debug mode (shows verbose output)
toshy-debug                 # Alias for toshy-config-start-verbose
toshy-config-start-verbose  # Run with debug output in terminal
```

### Diagnostic Commands
```bash
toshy-env                   # Show detected environment
toshy-devices               # List input devices seen by keymapper
toshy-versions              # Show component versions
toshy-machine-id            # Show machine ID for config conditionals
toshy-fnmode                # Change Apple keyboard function key mode
```

### GUI Applications
```bash
toshy-gui                   # Launch preferences app (GTK-4)
toshy-gui --tk              # Launch older Tkinter version
toshy-tray                  # Launch tray icon indicator
toshy-layout-selector       # Interactive keyboard layout selector
```

### Development Environment
```bash
# Activate Toshy Python virtual environment
source toshy-venv

# Install development dependencies (includes pytest, coverage, etc.)
pip install -r requirements-dev.txt

# Reinstall CLI commands (if PATH issues occur)
~/.config/toshy/scripts/toshy-bincommands-setup.sh
```

### Testing Commands (Use frequently during TDD)
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=toshy_common --cov=toshy_gui --cov-report=html --cov-report=term

# Run specific test module
pytest tests/test_env_context.py

# Run in watch mode (continuous testing)
pytest-watch

# Run with verbose output
pytest -vv

# Run and stop at first failure
pytest -x

# Run only last failed tests
pytest --lf

# Run tests matching pattern
pytest -k "test_distro"

# Generate coverage HTML report
pytest --cov=. --cov-report=html
# View at: htmlcov/index.html
```

## Architecture Overview

### Core Components

**1. Keymapper Core (`xwaykeyz`)**
- Custom fork of `keyszer` (which forked from `xkeysnail`)
- Installed automatically in Python venv at `~/.config/toshy/.venv/`
- Entry point: `xwaykeyz -c ~/.config/toshy/toshy_config.py`
- Runs as systemd user service (`toshy-config.service`)

**2. Configuration File**
- Location: `~/.config/toshy/toshy_config.py` (user copy)
- Default template: `default-toshy-config/toshy_config.py` (322KB, highly detailed)
- Barebones template: `default-toshy-config/toshy_config_barebones.py`
- Pure Python configuration using `xwaykeyz` API
- Defines modmaps (modifier key remapping) and keymaps (shortcut remapping)

**3. Environment Detection (`toshy_common/env_context.py`)**
- `EnvironmentInfo` class provides comprehensive environment detection
- Detects: distro type, desktop environment, window manager, session type (X11/Wayland)
- Reads: `/etc/os-release`, `/etc/lsb-release`, environment variables
- Used throughout codebase for conditional behavior

**4. Settings Management (`toshy_common/settings_class.py`)**
- `Settings` class manages user preferences via SQLite database
- Database: `~/.config/toshy/toshy_user_preferences.sqlite`
- Thread-safe operations for GUI/service synchronization
- File watchers for cross-process updates

**5. D-Bus Services (Wayland Window Context)**
Three environment-specific D-Bus services provide window context to the keymapper:

- **KDE Plasma**: `kwin-dbus-service/toshy_kwin_dbus_service.py`
  - Works with KWin script to track window focus
  - Service: `toshy-kwin-dbus.service`

- **COSMIC Desktop**: `cosmic-dbus-service/toshy_cosmic_dbus_service.py`
  - Uses Wayland protocols for window tracking
  - Service: `toshy-cosmic-dbus.service`

- **Wlroots Compositors**: `wlroots-dbus-service/toshy_wlroots_dbus_service.py`
  - Supports Sway, Hyprland, niri, Wayfire, etc.
  - Service: `toshy-wlroots-dbus.service`

Services auto-start only in their target environments and self-terminate if environment is incompatible.

**6. Desktop Integration**
- **KWin Script**: `kwin-script/` (separate versions for KDE 5/6)
  - Provides window focus events to D-Bus service
  - Auto-installed during setup on KDE Plasma

- **Cinnamon Extension**: `cinnamon-extension/`
  - Native extension for Cinnamon desktop
  - Installed via shell scripts

### Directory Structure

```
~/.config/toshy/           # User configuration directory
├── toshy_config.py        # Main keymapper config (user editable)
├── toshy_user_preferences.sqlite  # Settings database
├── .venv/                 # Python virtual environment
└── scripts/               # Helper scripts

Repository structure:
toshy/
├── setup_toshy.py         # Master installer (218KB, ~5500 lines)
├── toshy_tray.py          # System tray application
├── toshy_layout_selector.py  # Keyboard layout selector
├── toshy_common/          # Shared Python utilities
├── toshy_gui/             # GUI applications (Tkinter + GTK-4)
├── kwin-dbus-service/     # KDE Plasma integration
├── cosmic-dbus-service/   # COSMIC desktop integration
├── wlroots-dbus-service/  # Wlroots compositor integration
├── cinnamon-extension/    # Cinnamon DE extension
├── kwin-script/           # KWin scripts for Plasma
├── default-toshy-config/  # Default config templates
├── scripts/               # Installation and utility scripts
├── systemd-user-service-units/  # Systemd service definitions
├── desktop/               # .desktop files for app launchers
├── tests/                 # Test suite (pytest)
│   ├── unit/              # Fast unit tests
│   ├── integration/       # Integration tests
│   ├── fixtures/          # Test fixtures and data
│   ├── conftest.py        # Pytest configuration and shared fixtures
│   └── __init__.py
├── pytest.ini             # Pytest configuration
├── .coveragerc            # Coverage configuration
└── requirements-dev.txt   # Development dependencies
```

### Service Architecture

```
systemd (user session)
├── toshy-config.service          # Main keymapper service
├── toshy-session-monitor.service # Monitors desktop session changes
├── toshy-kwin-dbus.service       # KDE Plasma window context
├── toshy-cosmic-dbus.service     # COSMIC window context
└── toshy-wlroots-dbus.service    # Wlroots window context
```

### Window Context Providers (Critical for App-Specific Remapping)

Toshy requires window context (application class and title) to apply app-specific keymaps:

- **X11**: Direct queries via `python-xlib`
- **Wayland+GNOME**: Requires GNOME Shell extension (Xremap, Window Calls Extended, or Focused Window D-Bus)
- **Wayland+KDE**: KWin script + D-Bus service
- **Wayland+COSMIC**: D-Bus service with Wayland protocols
- **Wayland+Wlroots**: D-Bus service using `zwlr_foreign_toplevel_manager_v1` interface
- **Cinnamon**: Custom shell extension

## Key Development Patterns

### Keyboard Type Detection
The config auto-detects keyboard types (Windows/PC, Mac/Apple, IBM, Chromebook) based on device names. Custom keyboard identification is done via dictionary in config file:

```python
# In toshy_config.py, look for USER_CUSTOM_KEYBOARD_MODEL_DICT
USER_CUSTOM_KEYBOARD_MODEL_DICT = {
    # 'Device Name String': 'DEVICE_TYPE',  # <- TEMPLATE, DO NOT UNCOMMENT
}
```

Valid device types: `'APPLE_KEYBOARD'`, `'WINDOWS_KEYBOARD'`, `'IBM_KEYBOARD'`, `'CHROMEBOOK_KEYBOARD'`

### Config File Structure
The main config uses context managers and conditional blocks:

```python
# Modmaps: Remap modifier keys
keymap("Modmap - Win/PC keyboards", { ... }, when = lambda ctx: ...)

# Keymaps: App-specific shortcut remaps
keymap("App Name", { ... }, when = lambda ctx: ctx.app == "app_class")

# Multi-tap functionality (experimental)
multitap("Combo", { ... }, tap_count, timeout)
```

### Environment-Specific Behavior
Use `env.py` module (imported in config) to check environment:

```python
if env.DE_ENV == 'kde':
    # KDE-specific remaps
elif env.DE_ENV == 'gnome':
    # GNOME-specific remaps
```

### Adding Support for New Applications
1. Identify application class: Use `toshy-debug` and trigger keyboard shortcuts
2. Find window context info in debug output
3. Add keymap block in `toshy_config.py`:

```python
keymap("App Display Name", {
    C("RC-KEY"): KEY,  # Remap Right-Cmd+Key
}, when = lambda ctx: ctx.app == "app-class-name")
```

See Wiki article: https://github.com/RedBearAK/toshy/wiki/Toshifying-a-New-Linux-Application

## Important Files and Modules

### Installation and Setup
- **`setup_toshy.py`**: Master installer with distro detection, dependency installation, service setup
- **`scripts/toshy-bincommands-setup.sh`**: Installs CLI commands to `~/.local/bin/`
- **`scripts/toshy-desktopapps-setup.sh`**: Installs .desktop files for app launchers

### Common Utilities (`toshy_common/`)
- **`env_context.py`**: Environment detection (`EnvironmentInfo` class)
- **`settings_class.py`**: Settings management (`Settings` class)
- **`shared_device_context.py`**: KVM switch detection and monitoring
- **`service_manager.py`**: Systemd service control
- **`process_manager.py`**: Process lifecycle management
- **`monitoring.py`**: Settings/service change monitoring
- **`notification_manager.py`**: Desktop notifications via DBus
- **`runtime_utils.py`**: Runtime initialization helpers
- **`logger.py`**: Logging utilities

### GUI Applications
- **`toshy_tray.py`**: System tray icon (PyGObject/AppIndicator3)
- **`toshy_gui/main_tkinter.py`**: Tkinter-based preferences app
- **`toshy_gui/main_gtk4.py`**: GTK-4 based preferences app

### Testing and Debugging
- **Primary debugging**: Run automated test suite with `pytest`
- Use `toshy-debug` for verbose keymapper output showing all key events
- Check `toshy-services-log` for service-level errors
- Use `toshy-env` to verify environment detection
- Use `toshy-devices` to see input device enumeration

### Test Organization
```
tests/
├── unit/                          # Fast, isolated unit tests
│   ├── test_env_context.py        # Environment detection tests
│   ├── test_settings_class.py     # Settings management tests
│   ├── test_service_manager.py    # Service control tests
│   └── test_process_manager.py    # Process lifecycle tests
│
├── integration/                   # Integration tests (slower)
│   ├── test_dbus_services.py      # D-Bus service integration
│   ├── test_systemd_integration.py # Systemd service tests
│   └── test_config_loading.py     # Config file loading tests
│
├── fixtures/                      # Test data and fixtures
│   ├── sample_os_release.txt
│   ├── mock_dbus_responses.py
│   └── test_configs/
│
└── conftest.py                    # Shared fixtures and configuration
```

## Common Development Tasks (TDD Workflow)

### Modifying the Config (TDD Approach)
1. **RED**: Write test for desired config behavior
   ```python
   def test_should_remap_cmd_c_to_ctrl_c_in_terminal():
       # Test not yet implemented
       assert False, "Write this test first"
   ```
2. **GREEN**: Edit `~/.config/toshy/toshy_config.py` to pass test
3. **REFACTOR**: Clean up config code
4. **VERIFY**: Run `toshy-config-restart` and `pytest`

### Adding Distro Support (TDD Approach)
**Always follow RED-GREEN-REFACTOR:**

1. **RED**: Write failing test first
   ```python
   # tests/unit/test_env_context.py
   def test_should_detect_new_distro_when_os_release_matches():
       with mock.patch('builtins.open', mock.mock_open(read_data='ID=newdistro')):
           env = EnvironmentInfo()
           assert env.DISTRO_ID == 'newdistro'
   ```

2. **GREEN**: Implement minimal code
   - Add distro detection logic to `EnvironmentInfo` class
   - Create package list in `setup_toshy.py`
   - Run `pytest` until test passes

3. **REFACTOR**: Clean up detection logic
   - Extract duplicated code
   - Improve naming
   - Run `pytest` to ensure still green

4. **INTEGRATION TEST**: Test installation with `--override-distro` option

### Adding Desktop Environment Support (TDD Approach)
**Follow strict TDD cycle:**

1. **RED**: Write tests for DE detection
   ```python
   # tests/unit/test_env_context.py
   def test_should_detect_new_de_from_xdg_current_desktop():
       with mock.patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'NewDE'}):
           env = EnvironmentInfo()
           assert env.DE_ENV == 'newde'
   ```

2. **GREEN**: Add detection to `env_context.py`
   ```python
   def test_should_initialize_dbus_service_for_new_de():
       # Test D-Bus service creation
       pass
   ```

3. **GREEN**: Create D-Bus service if needed
   - Use existing services as templates
   - Write tests for service behavior first
   - Implement service to pass tests

4. **GREEN**: Add systemd service unit tests
   ```python
   def test_should_start_newde_dbus_service_when_in_newde():
       # Test service auto-start logic
       pass
   ```

5. **REFACTOR**: Clean up and consolidate
   - Run full test suite: `pytest`
   - Check coverage: `pytest --cov`

### Adding New Feature to Existing Module (TDD Mandatory)

**Example: Adding keyboard layout detection**

1. **RED**: Write test describing the feature
   ```python
   # tests/unit/test_kblayout_context.py
   def test_should_return_us_layout_when_setxkbmap_outputs_us():
       with mock.patch('subprocess.check_output', return_value=b'layout:     us'):
           layout = get_current_layout()
           assert layout == 'us'
   ```

2. **Run test**: `pytest tests/unit/test_kblayout_context.py -v`
   - Verify it fails for the right reason (function doesn't exist yet)

3. **GREEN**: Write minimal implementation
   ```python
   # toshy_common/kblayout_context.py
   def get_current_layout():
       return 'us'  # Simplest thing to make test pass
   ```

4. **Run test**: Verify it passes

5. **RED**: Add more tests for edge cases
   ```python
   def test_should_handle_multiple_layouts():
       # Test for layout switching
       pass

   def test_should_raise_error_when_setxkbmap_fails():
       # Test error handling
       pass
   ```

6. **GREEN**: Implement full functionality

7. **REFACTOR**: Improve code quality
   - Run `pytest` after each change

8. **VERIFY COVERAGE**:
   ```bash
   pytest --cov=toshy_common.kblayout_context --cov-report=term-missing
   ```

### Debugging Service Issues
```bash
# Check if services are running
toshy-services-status

# View logs
toshy-services-log

# Check environment detection
toshy-env

# Verify device detection
toshy-devices

# Manual run with debug output
toshy-services-stop
toshy-debug
```

### Working with Python Virtual Environment
All Python dependencies are isolated in `~/.config/toshy/.venv/`:

```bash
# Activate venv
source toshy-venv

# Now you can run xwaykeyz directly
xwaykeyz -c ~/.config/toshy/toshy_config.py --watch

# Deactivate
deactivate
```

## Special Considerations

### Multi-User Systems
Toshy uses systemd user services, which are per-user. Each user must run the installer separately.

### Wayland Requirements
- **GNOME**: Requires one of three compatible shell extensions installed
- **KDE Plasma**: Auto-installs KWin script during setup
- **Wlroots compositors**: Auto-detects `zwlr_foreign_toplevel_manager_v1` support

### International Keyboards
The keymapper is evdev-based and sees key codes, not symbols. Non-US layouts may require tweaking key definitions. Enable `Alt_Gr on Right Cmd` preference for ISO keyboards.

### KVM Switch Support
Toshy can detect when using Synergy, Deskflow, Input Leap, or Barrier as a KVM switch server and adjust behavior. Requires working log file for the KVM app.

### Performance
The config includes throttle settings for macro output. Virtual machines may need higher throttle values (20-50ms) to avoid timing issues with modifier keys.

## Configuration File Editing Guidelines

- Always edit `~/.config/toshy/toshy_config.py`, not the default template
- Preserve USER_CUSTOM sections when reinstalling
- Use `USER_CUSTOM_KEYBOARD_MODEL_DICT` for keyboard type overrides
- Test changes with `toshy-debug` before restarting services
- Backup config before major modifications (installer creates timestamped backups)

## Dependencies

### Python Dependencies (in venv)
- `xwaykeyz` (from GitHub, custom fork)
- `dbus-python`, `systemd-python`
- `pygobject` (GTK/AppIndicator)
- `watchdog`, `psutil`, `evdev`
- `pywayland`, `xkbcommon`
- `hyprpy`, `i3ipc` (for specific WMs)

### Development Dependencies (requirements-dev.txt)
**Required for TDD workflow:**
- `pytest` >= 7.0 - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `pytest-watch` - Continuous test runner
- `coverage` - Coverage measurement
- `mock` - Mocking library (backport for older Python)
- `freezegun` - Time mocking for tests
- `responses` - HTTP request mocking
- `faker` - Test data generation

### System Dependencies
- Python 3.8+ (for keymapper venv)
- Python 3.6+ (for setup script)
- `systemd` (optional, for service management)
- D-Bus
- Distro-specific packages (handled by installer)

## Emergency Recovery

If the keymapper is intercepting keys and preventing system use:

1. **Press F16** (or Fn+F16) to trigger emergency eject
2. **Kill the process**: `toshy-config-stop` or `toshy-services-stop`
3. **From another terminal/TTY**: `killall xwaykeyz`
4. **Disable autostart**: `toshy-services-disable`

## TDD Best Practices for Toshy

### Test Structure (AAA Pattern)
```python
def test_should_detect_kde_when_kde_session_active():
    # ARRANGE - Set up test data and mocks
    mock_env = {'XDG_CURRENT_DESKTOP': 'KDE'}

    # ACT - Execute the behavior being tested
    with mock.patch.dict(os.environ, mock_env):
        env_info = EnvironmentInfo()

    # ASSERT - Verify the expected outcome
    assert env_info.DE_ENV == 'kde'
```

### Naming Conventions
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test functions: `test_should_<expected_behavior>_when_<condition>`

Examples:
- `test_should_return_fedora_when_os_release_contains_fedora_id`
- `test_should_raise_error_when_dbus_connection_fails`
- `test_should_start_kwin_service_when_plasma_wayland_detected`

### Mocking Guidelines
```python
# Mock file system
@mock.patch('builtins.open', mock.mock_open(read_data='test data'))
def test_file_reading():
    pass

# Mock environment variables
@mock.patch.dict(os.environ, {'VAR': 'value'})
def test_env_var():
    pass

# Mock subprocess
@mock.patch('subprocess.check_output', return_value=b'output')
def test_subprocess_call():
    pass

# Mock D-Bus
@mock.patch('dbus.SystemBus')
def test_dbus_call(mock_bus):
    pass
```

### Test Fixtures (in conftest.py)
```python
@pytest.fixture
def mock_environment():
    """Provide clean environment for tests"""
    with mock.patch.dict(os.environ, {}, clear=True):
        yield

@pytest.fixture
def sample_env_info():
    """Provide pre-configured EnvironmentInfo"""
    with mock.patch('toshy_common.env_context.EnvironmentInfo') as mock_env:
        mock_env.DISTRO_ID = 'fedora'
        mock_env.DE_ENV = 'gnome'
        yield mock_env
```

### Coverage Goals by Module
- **toshy_common/**: 90%+ (critical utilities)
- **toshy_gui/**: 70%+ (GUI testing is harder)
- **D-Bus services**: 85%+ (integration critical)
- **setup_toshy.py**: 60%+ (complex installer logic)

### Red Flags (Avoid These)
❌ Writing code before tests
❌ Skipping tests for "simple" changes
❌ Testing implementation instead of behavior
❌ Overmocking (mocking too much makes tests fragile)
❌ Not running tests before committing
❌ Commenting out failing tests instead of fixing them

### Green Flags (Do These)
✅ Write test first, watch it fail
✅ Write minimal code to pass
✅ Refactor with green tests
✅ Test edge cases and errors
✅ Keep tests fast (mock external dependencies)
✅ Run full suite before pushing
✅ Maintain >80% coverage

## Pre-Commit Checklist

Before committing ANY code:

1. ✅ All tests pass: `pytest`
2. ✅ Coverage meets requirements: `pytest --cov --cov-fail-under=80`
3. ✅ No failing tests were commented out or deleted
4. ✅ New code has corresponding tests written first
5. ✅ Tests follow naming conventions
6. ✅ Integration tests pass (if modified services/installer)

## Resources

- **Main README**: Comprehensive user documentation in `README.md`
- **Wiki**: https://github.com/RedBearAK/toshy/wiki
- **Issue Tracker**: https://github.com/RedBearAK/toshy/issues
- **Contributing Guide**: `CONTRIBUTING.md`
- **Test Coverage Report**: `htmlcov/index.html` (after running `pytest --cov --cov-report=html`)
