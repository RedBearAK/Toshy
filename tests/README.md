# Toshy Test Suite

This directory contains all automated tests for the Toshy project.

## TDD Workflow (MANDATORY)

**Always follow the Red-Green-Refactor cycle:**

1. **RED** - Write a failing test first
2. **GREEN** - Write minimal code to make it pass
3. **REFACTOR** - Improve code while keeping tests green

## Directory Structure

```
tests/
├── unit/           # Fast, isolated unit tests
├── integration/    # Integration tests (slower, test component interaction)
├── fixtures/       # Test data and sample files
├── conftest.py     # Shared fixtures and pytest configuration
└── README.md       # This file
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=toshy_common --cov=toshy_gui --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_env_context.py

# Run specific test
pytest tests/unit/test_env_context.py::TestEnvironmentInfo::test_distro_detection

# Run tests in watch mode (re-run on changes)
pytest-watch

# Run only fast unit tests
pytest -m unit

# Skip slow integration tests
pytest -m "not slow"
```

## Writing Tests

### Test Naming Convention

- **Files**: `test_<module_name>.py`
- **Classes**: `Test<ClassName>`
- **Functions**: `test_should_<behavior>_when_<condition>`

Examples:
```python
def test_should_return_kde_when_xdg_desktop_is_kde():
    pass

def test_should_raise_error_when_dbus_unavailable():
    pass
```

### Test Structure (AAA Pattern)

```python
def test_example():
    # ARRANGE - Set up test data and mocks
    mock_data = {'key': 'value'}

    # ACT - Execute the code being tested
    result = function_under_test(mock_data)

    # ASSERT - Verify expected outcome
    assert result == expected_value
```

### Using Fixtures

Fixtures are defined in `conftest.py` and provide reusable test setup:

```python
def test_with_kde_environment(mock_kde_environment):
    # mock_kde_environment fixture sets up KDE env vars
    import os
    assert os.environ['XDG_CURRENT_DESKTOP'] == 'KDE'
```

## Available Fixtures

- `clean_environment` - Empty environment variables
- `mock_kde_environment` - KDE Plasma environment
- `mock_gnome_environment` - GNOME environment
- `mock_x11_session` - X11 session type
- `mock_wayland_session` - Wayland session type
- `mock_fedora_os_release` - Fedora /etc/os-release content
- `mock_ubuntu_os_release` - Ubuntu /etc/os-release content
- `mock_dbus_connection` - Mock D-Bus connection
- `temp_config_dir` - Temporary config directory
- `sample_sqlite_db` - Sample SQLite database

## Test Markers

Tests can be marked for categorization:

```python
@pytest.mark.unit
def test_fast_unit_test():
    pass

@pytest.mark.slow
@pytest.mark.integration
def test_slow_integration_test():
    pass

@pytest.mark.dbus
def test_requires_dbus():
    pass
```

Run specific markers:
```bash
pytest -m unit          # Only unit tests
pytest -m "not slow"    # Skip slow tests
pytest -m dbus          # Only D-Bus tests
```

## Coverage Requirements

- **Minimum**: 80% for all code
- **Target**: 90%+ for critical modules (toshy_common)
- **GUI code**: 70%+ (GUI testing is harder)

Check coverage:
```bash
pytest --cov=. --cov-report=html
# View at: htmlcov/index.html
```

## TDD Example Workflow

Let's add a new feature to detect keyboard layout:

### 1. RED - Write failing test first

```python
# tests/unit/test_kblayout_context.py
def test_should_return_us_layout_when_setxkbmap_outputs_us():
    with mock.patch('subprocess.check_output', return_value=b'layout:     us'):
        from toshy_common.kblayout_context import get_current_layout
        layout = get_current_layout()
        assert layout == 'us'
```

Run test: `pytest tests/unit/test_kblayout_context.py`
- **Expected**: Test fails (module doesn't exist)

### 2. GREEN - Write minimal code to pass

```python
# toshy_common/kblayout_context.py
def get_current_layout():
    return 'us'  # Simplest implementation
```

Run test: `pytest tests/unit/test_kblayout_context.py`
- **Expected**: Test passes

### 3. RED - Add more tests

```python
def test_should_return_de_layout_when_setxkbmap_outputs_de():
    with mock.patch('subprocess.check_output', return_value=b'layout:     de'):
        layout = get_current_layout()
        assert layout == 'de'
```

Run test: `pytest tests/unit/test_kblayout_context.py`
- **Expected**: New test fails (returns 'us' always)

### 4. GREEN - Implement full functionality

```python
import subprocess

def get_current_layout():
    output = subprocess.check_output(['setxkbmap', '-query'])
    for line in output.decode().split('\n'):
        if 'layout:' in line:
            return line.split(':')[1].strip()
    return 'us'
```

### 5. REFACTOR - Improve while keeping green

```python
import subprocess
from typing import Optional

def get_current_layout() -> Optional[str]:
    """Get current keyboard layout from setxkbmap."""
    try:
        output = subprocess.check_output(
            ['setxkbmap', '-query'],
            stderr=subprocess.DEVNULL
        )
        return _parse_layout_from_output(output.decode())
    except subprocess.CalledProcessError:
        return None

def _parse_layout_from_output(output: str) -> Optional[str]:
    """Parse layout from setxkbmap output."""
    for line in output.split('\n'):
        if 'layout:' in line:
            return line.split(':')[1].strip()
    return None
```

Run tests after each refactor: `pytest tests/unit/test_kblayout_context.py`

## Common Mocking Patterns

### Mock file reading
```python
mock_data = "file contents"
with mock.patch('builtins.open', mock.mock_open(read_data=mock_data)):
    # Your test code
```

### Mock environment variables
```python
with mock.patch.dict(os.environ, {'VAR': 'value'}):
    # Your test code
```

### Mock subprocess
```python
with mock.patch('subprocess.check_output', return_value=b'output'):
    # Your test code
```

### Mock D-Bus
```python
@mock.patch('dbus.SystemBus')
def test_dbus_function(mock_bus):
    # Configure mock
    mock_bus.return_value.get_object.return_value = mock.Mock()
    # Your test code
```

## Best Practices

✅ **DO:**
- Write tests before code (TDD)
- Keep tests fast and isolated
- Mock external dependencies
- Test behavior, not implementation
- Use descriptive test names
- Follow AAA pattern

❌ **DON'T:**
- Write code before tests
- Skip tests for "simple" changes
- Test private methods directly
- Over-mock (makes tests fragile)
- Commit failing tests
- Delete tests to make code pass

## Pre-Commit Checklist

Before committing:

1. ✅ All tests pass: `pytest`
2. ✅ Coverage ≥ 80%: `pytest --cov --cov-fail-under=80`
3. ✅ No tests commented out or deleted
4. ✅ New code has tests written first
5. ✅ Tests follow naming conventions
