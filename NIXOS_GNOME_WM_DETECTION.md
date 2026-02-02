# NixOS GNOME Window Manager Detection Issue

## Summary

Window manager detection on NixOS GNOME fails when running as systemd service, despite working correctly when tested manually. A workaround override has been implemented while we investigate the root cause.

## Problem Description

### Symptoms
- **Manual testing**: `python3 toshy_common/env_context.py` correctly detects `WINDOW_MGR: mutter` ✅
- **Service context**: Systemd service detects `WINDOW_MGR: WM_unidentified_by_logic` ❌
- **Impact**: Toshy fails to start because environ_api rejects invalid compositor name

### Environment
- Distribution: NixOS
- Desktop Environment: GNOME (Wayland)
- Session Type: Wayland
- Toshy installed via: Nix flake (path input)

## Root Cause Identified

### NixOS Binary Wrapping
NixOS wraps executables to manage dependencies:
- Actual binary: `/nix/store/.../bin/gnome-shell`
- Wrapper: `.gnome-shell-wrapped`
- Process name (truncated to 15 chars): `.gnome-shell-wr`

### Detection Method
`is_process_running()` in `toshy_common/env_context.py` uses:
```bash
pgrep -x gnome-shell  # Exact match - fails for .gnome-shell-wr
```

### Fix Implemented
Added NixOS fallback in `is_process_running()`:
```python
except subprocess.CalledProcessError:
    # On NixOS, binaries are wrapped (gnome-shell → .gnome-shell-wrapped)
    # and process names are truncated to 15 chars (.gnome-shell-wr).
    # Fallback: try substring match without -x flag
    if self.DISTRO_ID == 'nixos' and len(process_name) <= 15:
        fallback_cmd = ['pgrep']
        if use_pgrep_i:
            fallback_cmd.append('-i')
        fallback_cmd.append(process_name)
        try:
            result = subprocess.check_output(fallback_cmd)
            return bool(result.strip())
        except subprocess.CalledProcessError:
            pass
    return False
```

Additionally mapped `mutter` → `gnome-shell` for environ_api compatibility:
```python
# In toshy_config.py
if SESSION_TYPE == 'wayland' and DESKTOP_ENV == 'gnome' and WINDOW_MGR in ['mutter', 'gnome-shell']:
    _wl_compositor = 'gnome-shell'
```

## The Mystery

### What We Know
1. ✅ Fix correctly detects wrapped processes when tested manually
2. ❌ Same fix fails when running as systemd service
3. ✅ Both contexts use identical Nix store version (6d6qrfy1cyq83p3yp3g7xm488nhrh72c-toshy-20260202)
4. ❌ NOT a race condition - Adding `org.gnome.Shell.target` dependency didn't help
5. ❌ NOT a version mismatch - Verified via `which python3` and module inspection

### Test Results
```bash
# Manual test (works)
$ python3 toshy_common/env_context.py
DISTRO_ID: nixos
DISTRO_VER: 25.05
DESKTOP_ENV: gnome
SESSION_TYPE: wayland
WINDOW_MGR: mutter ✅

# Service test (fails)
$ journalctl --user -u toshy-config -n 50
ERROR: Compositor 'WM_unidentified_by_logic' is not valid ❌
```

### Hypotheses to Investigate

**Hypothesis 1: Environment Differences**
- Systemd service may have different `$PATH`, `$PYTHONPATH`, or other env vars
- Test: Compare `env` output in both contexts
- Relevant: Service sets `PYTHONPATH=${cfg.package}/share/toshy`

**Hypothesis 2: Process Visibility**
- Service may run before GNOME processes are visible to pgrep
- Countered by: `org.gnome.Shell.target` dependency should prevent this
- Test: Add debug logging to show pgrep output in service

**Hypothesis 3: Execution Permissions**
- Service user context may have different process visibility
- Test: Run `pgrep gnome-shell` as service user vs interactive user
- Relevant: Both are user services, should have same permissions

**Hypothesis 4: Python Subprocess Behavior**
- subprocess.check_output() may behave differently in service context
- Test: Add debug logging showing exact command and output
- Relevant: Same Python interpreter in both contexts

**Hypothesis 5: Timing of Process Name Resolution**
- Wrapped process name may not be stable at service start time
- Test: Add retry logic with delays
- Countered by: Manual tests don't require delays

## Workaround Implementation

### NixOS Module Option
Added `windowManager` override to `nix/modules/home-manager.nix`:
```nix
windowManager = mkOption {
  type = types.nullOr types.str;
  default = null;
  example = "gnome-shell";
  description = ''
    Override window manager detection.
    If null, Toshy will auto-detect the WM.

    WORKAROUND: On NixOS with GNOME, set this to "gnome-shell" if auto-detection
    fails due to wrapped binary names. This is a temporary fix while we investigate
    why the NixOS wrapped binary detection doesn't work in service context.

    Common values: "gnome-shell", "mutter", "kwin_wayland", "sway", "hyprland"
  '';
};
```

### Environment Variable
Service sets `TOSHY_WM_OVERRIDE` when option is configured:
```nix
Environment = [
  "PYTHONPATH=${cfg.package}/share/toshy"
] ++ optional (cfg.desktopEnvironment != null) "TOSHY_DE_OVERRIDE=${cfg.desktopEnvironment}"
  ++ optional (cfg.windowManager != null) "TOSHY_WM_OVERRIDE=${cfg.windowManager}";
```

### Config Support
`toshy_config.py` reads override from environment:
```python
# Read overrides from environment variables (set by NixOS module)
if os.environ.get('TOSHY_DE_OVERRIDE'):
    OVERRIDE_DESKTOP_ENV = os.environ.get('TOSHY_DE_OVERRIDE')
if os.environ.get('TOSHY_WM_OVERRIDE'):
    OVERRIDE_WINDOW_MGR = os.environ.get('TOSHY_WM_OVERRIDE')
```

### Usage

Add to your NixOS home-manager configuration:
```nix
services.toshy = {
  enable = true;
  autoStart = true;
  desktopEnvironment = "gnome";
  windowManager = "gnome-shell";  # WORKAROUND for wrapped binary detection
};
```

Then rebuild:
```bash
cd ~/Documents/flakes-nixos
nix flake update toshy
sudo nixos-rebuild switch --flake .#gti14
```

## Next Steps for Investigation

### Priority 1: Environment Comparison
```bash
# Create debug script to compare environments
cat > /tmp/toshy_debug_env.sh <<'EOF'
#!/usr/bin/env bash
echo "=== Environment ==="
env | sort
echo ""
echo "=== Process detection ==="
pgrep -x gnome-shell || echo "pgrep -x failed: $?"
pgrep gnome-shell || echo "pgrep failed: $?"
ps aux | grep gnome-shell | grep -v grep
EOF

# Run manually
bash /tmp/toshy_debug_env.sh > /tmp/manual_env.txt

# Run from service
# Add ExecStartPre=/tmp/toshy_debug_env.sh to service unit
# Compare /tmp/manual_env.txt vs service journal output
```

### Priority 2: Add Debug Logging
Modify `is_process_running()` to log:
- Exact command being run
- Raw output from pgrep
- Exception details
- Fallback path taken (or not)

### Priority 3: Service Context Testing
Create minimal test service to isolate the issue:
```ini
[Unit]
Description=Test Process Detection
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/nix/store/.../bin/python3 -c "from toshy_common.env_context import EnvironmentInfo; env = EnvironmentInfo(); print(f'WM: {env.WINDOW_MGR}')"
```

### Priority 4: Strace Comparison
Run both contexts under strace to compare system calls:
```bash
# Manual
strace -o /tmp/manual.strace python3 toshy_common/env_context.py

# Service (add to ExecStart)
strace -o /tmp/service.strace /nix/store/.../xwaykeyz ...
```

## Related Files

- `toshy_common/env_context.py` - Environment detection logic
- `default-toshy-config/toshy_config.py` - Config with WM mapping
- `nix/modules/home-manager.nix` - NixOS module with workaround option
- `tests/unit/test_env_context_nixos.py` - Tests for wrapped process detection

## Git History

- `16251ce` - Fix GNOME window manager detection on NixOS
- `efd3ad7` - Fix: Map mutter to gnome-shell for environ_api compatibility
- `50d0dff` - Add windowManager override option for NixOS GNOME detection workaround

## References

- Issue: https://github.com/RedBearAK/Toshy/pull/778#discussion
- Linux process name limit: 15 characters (TASK_COMM_LEN - 1)
- NixOS wrapper documentation: https://nixos.wiki/wiki/Nix_Runtime_Environment
