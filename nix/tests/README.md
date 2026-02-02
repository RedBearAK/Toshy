# Toshy NixOS Integration Tests

This directory contains integration tests for Toshy on NixOS using the NixOS VM testing framework.

## Overview

The tests verify that Toshy works correctly on NixOS across different configurations and desktop environments. Each test creates isolated NixOS virtual machines, installs Toshy, and verifies functionality.

## Test Files

### `basic.nix`
**Purpose:** Basic system-level functionality test

**What it tests:**
- System package installation
- Udev rules configuration
- Kernel module loading (uinput)
- User group membership
- Device permissions

**Run time:** ~2-3 minutes

**Usage:**
```bash
nix-build nix/tests/basic.nix
# or
nix build .#checks.x86_64-linux.toshy-basic-test
```

### `home-manager.nix`
**Purpose:** Home-manager integration test

**What it tests:**
- Home-manager module functionality
- Systemd user services creation
- Service file generation
- Configuration activation
- User-level package installation

**Run time:** ~3-5 minutes

**Usage:**
```bash
nix-build nix/tests/home-manager.nix
# or
nix build .#checks.x86_64-linux.toshy-home-manager-test
```

### `multi-de.nix`
**Purpose:** Multi-desktop-environment test

**What it tests:**
- Configuration across different DEs (XFCE, generic X11)
- Desktop environment detection
- Service customization per DE
- Multiple machines simultaneously

**Run time:** ~5-7 minutes

**Usage:**
```bash
nix-build nix/tests/multi-de.nix
# or
nix build .#checks.x86_64-linux.toshy-multi-de-test
```

### `integration.nix` (Legacy)
**Purpose:** Original integration test (kept for compatibility)

**What it tests:**
- Full integration with all components
- Similar to basic + home-manager combined

**Usage:**
```bash
nix-build nix/tests/integration.nix
# or
nix build .#checks.x86_64-linux.toshy-integration-test
```

## Quick Start

### Run All Tests

The easiest way to run all tests:

```bash
./nix/tests/run-tests.sh
```

Or using nix flake:

```bash
nix flake check
```

### Run Individual Tests

```bash
# Run only basic tests
./nix/tests/run-tests.sh basic

# Run home-manager tests
./nix/tests/run-tests.sh home-manager

# Run multi-DE tests
./nix/tests/run-tests.sh multi-de
```

### Interactive Testing

For debugging, run tests in interactive mode:

```bash
./nix/tests/run-tests.sh --interactive basic
```

This opens the NixOS test driver where you can:
- Run individual commands
- Inspect VM state
- Debug failures
- Get an interactive shell: `machine.shell_interact()`

## Test Runner Options

The `run-tests.sh` script provides several options:

```bash
./nix/tests/run-tests.sh [OPTIONS] [TEST]

OPTIONS:
  -i, --interactive    Run in interactive mode (debugging)
  -k, --keep-going     Continue on test failures
  -v, --verbose        Show detailed output
  -h, --help           Show help message

TESTS:
  basic           Basic system-level tests
  home-manager    Home-manager integration
  multi-de        Multi-desktop-environment tests
  legacy          Legacy integration test
  all             All tests (default)
```

### Examples

```bash
# Run all tests
./nix/tests/run-tests.sh

# Run only basic tests
./nix/tests/run-tests.sh basic

# Debug home-manager test interactively
./nix/tests/run-tests.sh -i home-manager

# Run all tests, continue on failures
./nix/tests/run-tests.sh -k all

# Verbose output for debugging
./nix/tests/run-tests.sh -v basic
```

## Writing Tests

### Test Structure

All tests follow the `pkgs.testers.runNixOSTest` pattern:

```nix
pkgs.testers.runNixOSTest {
  name = "test-name";

  nodes.machine = { config, pkgs, ... }: {
    # NixOS configuration for the VM
  };

  testScript = ''
    # Python test code
    machine.start()
    machine.wait_for_unit("multi-user.target")

    with subtest("Test description"):
        machine.succeed("some-command")
        machine.fail("should-fail-command")
  '';
}
```

### Python Test API

The testScript has access to machine objects with these methods:

**Starting/Stopping:**
- `machine.start()` - Start the VM
- `machine.shutdown()` - Shutdown gracefully
- `machine.crash()` - Force shutdown
- `start_all()` - Start all VMs in multi-machine tests

**Waiting:**
- `machine.wait_for_unit("unit.service")` - Wait for systemd unit
- `machine.wait_for_file("/path")` - Wait for file to exist
- `machine.wait_for_open_port(80)` - Wait for network port
- `machine.wait_until_succeeds("command")` - Retry until success

**Running Commands:**
- `machine.succeed("command")` - Run command, expect success (exit 0)
- `machine.fail("command")` - Run command, expect failure (exit != 0)
- `machine.execute("command")` - Run command, return (status, output)

**Interactive:**
- `machine.shell_interact()` - Interactive shell access
- Useful for debugging: set breakpoint, then use this

**Text Matching:**
- `machine.wait_for_text("pattern")` - Wait for text on screen
- `machine.wait_for_console_text("pattern")` - Wait for console text

### Subtests

Use subtests to organize test logic:

```python
with subtest("Description of what we're testing"):
    machine.succeed("command")
    machine.fail("should-fail")
```

Benefits:
- Clear test organization
- Individual subtest can fail without stopping others
- Better error messages

### Best Practices

1. **Use descriptive names:** Test names should clearly indicate what's being tested

2. **Organize with subtests:** Group related checks together

3. **Wait for services:** Always wait for units to be ready before testing

4. **Check actual behavior:** Don't just verify files exist, test functionality

5. **Test negative cases:** Verify things that should fail actually do fail

6. **Keep tests focused:** Each test file should test one aspect

7. **Document expectations:** Add comments explaining what should happen

### Example Test

```nix
pkgs.testers.runNixOSTest {
  name = "toshy-service-test";

  nodes.machine = { config, pkgs, ... }: {
    # Configuration here
  };

  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")

    with subtest("Toshy service starts"):
        machine.succeed("systemctl --user -M alice@ start toshy-config.service")
        machine.wait_for_unit("toshy-config.service", "alice")

    with subtest("Toshy service responds"):
        machine.succeed("systemctl --user -M alice@ status toshy-config.service")

    with subtest("Configuration file exists"):
        machine.succeed("test -f /home/alice/.config/toshy/toshy_config.py")
  '';
}
```

## Debugging Failed Tests

### 1. Run in Interactive Mode

```bash
./nix/tests/run-tests.sh -i basic
```

Then in the test driver:
```python
>>> start_all()
>>> machine.succeed("some-command")
>>> machine.shell_interact()  # Get a shell
```

### 2. Check Test Logs

```bash
nix build .#checks.x86_64-linux.toshy-basic-test --show-trace
```

### 3. Inspect VM

After a failed test:
```bash
# The VM logs are in the result
cat result/log.html  # View in browser
```

### 4. Add Debugging Output

Add to testScript:
```python
machine.succeed("ls -la /some/path >&2")  # Print to stderr
result = machine.succeed("command")
print(f"Result: {result}")  # Print in test output
```

### 5. Check Journal Logs

In the VM:
```python
machine.succeed("journalctl -u some.service >&2")
machine.succeed("journalctl --user -u toshy-config.service >&2")
```

## CI/CD Integration

### GitHub Actions

```yaml
name: NixOS Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: cachix/install-nix-action@v22
        with:
          extra_nix_config: |
            experimental-features = nix-command flakes
      - name: Run tests
        run: nix flake check
```

### GitLab CI

```yaml
test:
  image: nixos/nix:latest
  script:
    - nix --version
    - nix flake check
```

## Common Issues

### "KVM not available"

**Problem:** Tests run slowly without hardware acceleration

**Solution:** This is expected in VMs or containers. Tests will still work, just slower. To enable KVM on Linux hosts:

```bash
sudo modprobe kvm
sudo usermod -aG kvm $USER
```

### "Out of disk space"

**Problem:** Nix store fills up during tests

**Solution:**
```bash
nix-collect-garbage -d
```

### "Flakes not enabled"

**Problem:** `nix flake` command not recognized

**Solution:** Enable flakes:
```bash
mkdir -p ~/.config/nix
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

### "Test hangs forever"

**Problem:** Test waiting for something that never happens

**Solution:**
1. Run in interactive mode: `./nix/tests/run-tests.sh -i test-name`
2. Check what the VM is doing: `machine.succeed("ps aux >&2")`
3. Check logs: `machine.succeed("journalctl -xe >&2")`

## Performance

### Test Duration

Typical test durations on modern hardware:
- Basic test: 2-3 minutes
- Home-manager test: 3-5 minutes
- Multi-DE test: 5-7 minutes
- All tests: 10-15 minutes

### Optimization

**Speed up tests:**
1. Use `--no-link` to avoid creating result symlinks
2. Run tests in parallel (if you have multiple cores)
3. Enable KVM if available
4. Use a binary cache (Cachix)

**Cache builds:**
```bash
# Add to ~/.config/nix/nix.conf
builders-use-substitutes = true
```

## Resources

- [NixOS Testing Guide](https://nix.dev/tutorials/nixos/integration-testing-using-virtual-machines)
- [NixOS Test API](https://nixos.org/manual/nixos/stable/index.html#sec-nixos-tests)
- [Writing NixOS Tests](https://nixos.wiki/wiki/NixOS_Testing_library)
- [Python Test Driver](https://github.com/NixOS/nixpkgs/blob/master/nixos/lib/test-driver/)

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Add to `flake.nix` checks
3. Update this README
4. Test locally before committing
5. Ensure tests are deterministic (no random failures)

## License

Same as Toshy: GPL-3.0-or-later
