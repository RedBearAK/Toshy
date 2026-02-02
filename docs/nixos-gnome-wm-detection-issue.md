# NixOS GNOME Window Manager Detection Issue

## Problem Summary

On NixOS with GNOME Wayland, Toshy fails to detect the window manager (`gnome-shell`) when running as a systemd service. This causes the GNOME D-Bus service dependency check to fail, preventing proper window context tracking.

## Symptoms

1. `toshy-env` shows `WINDOW_MGR = 'keymissing'` when run from systemd service context
2. GNOME D-Bus service (`toshy-gnome-dbus.service`) fails to start
3. Config service may fail or have limited functionality
4. GUI preferences may not work correctly

## Root Cause

**NixOS binary wrapping prevents process name detection in systemd service context.**

### How NixOS Wrapping Works

NixOS wraps executables in shell scripts to set up the environment (PATH, library paths, etc.). For example:

```bash
# /nix/store/xxx-gnome-shell/bin/gnome-shell is actually:
#!/nix/store/yyy-bash-5.x/bin/bash
exec -a "$0" "/nix/store/xxx-gnome-shell/bin/.gnome-shell-wrapped" "$@"
```

The `-a "$0"` preserves the process name as `gnome-shell` in most contexts.

### Why It Fails in Systemd Service Context

Toshy's environment detection (`toshy_common/env_context.py`) uses these methods to find the window manager:

1. **Process name matching** - Looks for `gnome-shell`, `mutter`, `kwin_wayland`, etc.
   - Uses `psutil` to iterate running processes
   - Checks `proc.name()` and `proc.cmdline()`
   - **FAILS**: In systemd service context with sandboxing, the wrapped binary name doesn't propagate correctly

2. **Fallback: Desktop environment mapping** - Maps `DESKTOP_ENV` to expected WM
   - GNOME → `gnome-shell`
   - KDE → `kwin_wayland` or `kwin_x11`
   - **NOT IMPLEMENTED** for all DEs yet

3. **Environment variable override** - `TOSHY_WM_OVERRIDE`
   - Now supported in NixOS module as workaround

### Why `toshy-env` Command Works

When run interactively:
- No systemd sandboxing restrictions
- Full process tree visibility
- Environment variables propagate correctly
- Wrapped binary names resolve properly

When run as systemd service:
- Limited process visibility (depending on sandboxing)
- Different capability set
- Environment isolation
- Wrapped names may not resolve

## Investigation Timeline

### What We Tried

1. **Added debug logging** to `env_context.py`
   - Confirmed process iteration works
   - Found that `gnome-shell` process not visible to service

2. **Checked systemd sandboxing**
   - Removed `ProtectHome`, `ProtectSystem`, `PrivateTmp`
   - Added `org.gnome.Shell.target` dependency
   - **Result**: Still failed to detect WM in service context

3. **Verified NixOS wrapping**
   - Confirmed `exec -a "$0"` preserves process name
   - Works in interactive shell
   - Fails in systemd service

4. **Environment variable override**
   - Added `TOSHY_DE_OVERRIDE` support
   - Added `TOSHY_WM_OVERRIDE` support (this PR)
   - **Result**: Workaround successful

### What We Know

✅ Process name detection works in interactive shell
✅ NixOS wrapping uses `exec -a` to preserve names
✅ Systemd service has limited process visibility
✅ Environment variable override works as workaround
❌ Root cause of process visibility limitation unclear
❌ Don't know why sandboxing changes didn't help

### What We Don't Know

❓ **Why doesn't process visibility work with standard systemd service setup?**
   - Is it a NixOS-specific systemd configuration?
   - Is it a namespace isolation issue?
   - Is it related to user session vs system services?

❓ **Why doesn't removing sandboxing directives help?**
   - Expected `ProtectHome=false` to give full access
   - Should have same visibility as interactive shell
   - Something else must be restricting it

❓ **Is there a better systemd configuration?**
   - Should we run as system service instead of user service?
   - Should we add more capabilities?
   - Should we use `DynamicUser=false`?

## Current Workaround

### NixOS Home Manager Configuration

Add explicit window manager override:

```nix
{
  services.toshy = {
    enable = true;
    desktopEnvironment = "gnome";
    windowManager = "gnome-shell";  # Workaround for NixOS
  };
}
```

This sets `TOSHY_WM_OVERRIDE=gnome-shell` in the service environment.

### Manual Configuration

If not using NixOS module, set environment variable in systemd service:

```ini
[Service]
Environment="TOSHY_WM_OVERRIDE=gnome-shell"
```

### Config File Override

Edit `~/.config/toshy/toshy_config.py`:

```python
OVERRIDE_WINDOW_MGR = 'gnome-shell'
```

## Next Steps for Permanent Fix

### Immediate (This PR)

- [x] Add `windowManager` option to NixOS module
- [x] Document issue and workaround
- [x] Add `TOSHY_WM_OVERRIDE` environment variable support
- [ ] Update `toshy_config.py` to read `TOSHY_WM_OVERRIDE` from environment

### Short-term (Future PRs)

1. **Add fallback DE→WM mapping** in `env_context.py`:
   ```python
   # If WINDOW_MGR not found, infer from DESKTOP_ENV
   if not window_mgr and desktop_env == 'gnome':
       window_mgr = 'gnome-shell'
   elif not window_mgr and desktop_env == 'kde':
       window_mgr = 'kwin_wayland' if session_type == 'wayland' else 'kwin_x11'
   ```

2. **Improve process detection**:
   - Check process executable path, not just name
   - Look for `/gnome-shell-wrapped` or similar NixOS patterns
   - Add NixOS-specific detection heuristics

3. **Add D-Bus introspection**:
   - Query `org.gnome.Shell` D-Bus service presence
   - Use D-Bus to confirm WM instead of process scanning
   - More reliable than process name matching

### Long-term Investigation

1. **Debug systemd process visibility**:
   - Create minimal reproducible test case
   - Compare `ps aux` output between service and interactive
   - Check systemd namespace configuration
   - Test on non-NixOS system for comparison

2. **Upstream to Toshy project**:
   - Report NixOS-specific detection issue
   - Propose fallback WM detection logic
   - Share findings about systemd service context

3. **NixOS-specific fixes**:
   - Investigate if NixOS systemd has special restrictions
   - Check if other NixOS packages face similar issues
   - Consider NixOS module-level fixes (wrapper detection)

## Testing Checklist

When testing fixes:

- [ ] `toshy-env` shows correct `WINDOW_MGR` when run as service
- [ ] GNOME D-Bus service starts successfully
- [ ] Window context tracking works in applications
- [ ] GUI preferences app launches and works
- [ ] Keymaps apply correctly per-application
- [ ] Survives logout/login cycle
- [ ] Works after system reboot

## Related Files

- `nix/modules/home-manager.nix` - NixOS module with `windowManager` option
- `toshy_common/env_context.py` - Environment detection logic
- `default-toshy-config/toshy_config.py` - Config override variables
- `systemd-user-service-units/toshy-gnome-dbus.service.sh` - GNOME D-Bus service

## References

- [Toshy Issue #778](https://github.com/RedBearAK/toshy/pull/778) - This PR
- [NixOS Manual: Wrapping](https://nixos.org/manual/nixpkgs/stable/#sec-wrappers)
- [systemd Service Sandboxing](https://www.freedesktop.org/software/systemd/man/systemd.exec.html)
- [psutil Documentation](https://psutil.readthedocs.io/)

---

**Status**: Workaround implemented, root cause investigation ongoing.
**Last Updated**: 2026-02-02
