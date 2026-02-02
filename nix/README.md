# Toshy Nix Packages and Modules

This directory contains Nix flake packages and modules for installing Toshy on NixOS.

## Directory Structure

```
nix/
├── packages/
│   ├── xwaykeyz.nix       # xwaykeyz Python package derivation
│   └── toshy.nix          # Main Toshy package derivation
├── modules/
│   ├── home-manager.nix   # Home-manager module (recommended)
│   └── nixos.nix          # NixOS system module (optional)
├── tests/
│   └── integration.nix    # NixOS VM integration tests
├── examples/
│   ├── home-manager-basic.nix    # Simple home-manager config
│   ├── home-manager-advanced.nix # All options example
│   ├── flake-example.nix         # Complete flake template
│   └── nixos-configuration.nix   # Traditional config.nix
└── README.md              # This file
```

## Quick Start

### For NixOS Users with Home-Manager

Add to your `flake.nix`:

```nix
{
  inputs.toshy.url = "github:RedBearAK/toshy";
  # For local development: inputs.toshy.url = "path:/path/to/toshy";

  outputs = { toshy, ... }: {
    nixosConfigurations.my-machine = nixpkgs.lib.nixosSystem {
      modules = [
        # Apply overlay (REQUIRED - makes pkgs.toshy and pkgs.xwaykeyz available)
        ({ config, pkgs, ... }: {
          nixpkgs.overlays = [ toshy.overlays.default ];
        })

        # System module (udev rules, kernel modules)
        toshy.nixosModules.default
        { services.toshy.enable = true; }

        # Home Manager
        home-manager.nixosModules.home-manager {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;

          # Make module available to all users
          home-manager.sharedModules = [
            toshy.homeManagerModules.default
          ];

          home-manager.users.myuser = {
            services.toshy = {
              enable = true;
              autoStart = true;
            };
          };
        }
      ];
    };
  };
}
```

### For Standalone Home-Manager

```nix
# ~/.config/home-manager/flake.nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    toshy.url = "github:RedBearAK/toshy";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, toshy, home-manager, ... }: {
    homeConfigurations.myuser = home-manager.lib.homeManagerConfiguration {
      # Apply overlay to make pkgs.toshy available
      pkgs = import nixpkgs {
        system = "x86_64-linux";
        overlays = [ toshy.overlays.default ];
      };

      modules = [
        toshy.homeManagerModules.default
        {
          services.toshy = {
            enable = true;
            autoStart = true;
          };

          home = {
            username = "myuser";
            homeDirectory = "/home/myuser";
            stateVersion = "24.05";
          };
        }
      ];
    };
  };
}
```

## Packages

### xwaykeyz

Python package for the keyboard remapping engine.

```sh
# Build xwaykeyz
nix build .#xwaykeyz

# Run xwaykeyz
nix run .#xwaykeyz -- --help
```

### toshy

Main Toshy package including:
- Python modules (toshy_common, toshy_gui)
- Shell scripts and wrapper commands
- Systemd service unit templates
- D-Bus services for desktop integration
- Configuration file templates

```sh
# Build Toshy
nix build .#toshy

# Explore package contents
nix build .#toshy && ls -la result/
```

## Modules

### Home-Manager Module

The recommended way to install Toshy. Provides:
- Per-user installation
- Declarative configuration
- Systemd user service management
- Desktop environment integration

**⚠️ Important:** The Toshy overlay MUST be applied for `pkgs.toshy` and `pkgs.xwaykeyz` to be available. See examples above.

**Options:** See `modules/home-manager.nix` or `examples/home-manager-advanced.nix`

### NixOS Module

System-wide configuration (optional). Provides:
- System package installation
- Udev rules for input device access
- Kernel module loading (uinput)
- User group configuration

**Usage:** See `examples/nixos-configuration.nix`

## Testing

### Local Testing

Build packages locally:

```sh
# Build all packages
nix flake check

# Build specific package
nix build .#toshy
nix build .#xwaykeyz
```

### Integration Tests

We provide comprehensive NixOS VM integration tests. See `tests/README.md` for full documentation.

**Quick Start:**

```sh
# Run all tests
cd nix/tests
./run-tests.sh

# Or use make
make all

# Or use nix flake
nix flake check
```

**Available Tests:**

1. **Basic Test** (`basic.nix`)
   - System package installation
   - Udev rules and kernel modules
   - User group membership
   - Device permissions

2. **Home-Manager Test** (`home-manager.nix`)
   - Home-manager module functionality
   - Systemd user services
   - Configuration activation
   - Service file generation

3. **Multi-DE Test** (`multi-de.nix`)
   - Multiple desktop environments (XFCE, generic X11)
   - Desktop-specific configuration
   - Multi-machine testing
   - DE detection

4. **Legacy Test** (`integration.nix`)
   - Original comprehensive test
   - Kept for compatibility

**Interactive Testing (for debugging):**

```sh
cd nix/tests
./run-tests.sh -i basic

# Or with make
make interactive-basic
```

**Individual Tests:**

```sh
# Run specific test
./run-tests.sh basic
./run-tests.sh home-manager
./run-tests.sh multi-de

# Or with make
make basic
make home-manager
make multi-de
```

The integration tests:
- Create isolated NixOS VMs
- Install Toshy via the modules
- Verify packages, services, and permissions
- Test commands and functionality
- Support interactive debugging

## Development

### Building from Local Source

When developing locally:

```nix
# In your flake.nix, use a path input
inputs.toshy.url = "path:/path/to/toshy";
```

Or override the source:

```nix
services.toshy.package = pkgs.toshy.overrideAttrs (old: {
  src = /path/to/toshy;
});
```

### Getting Correct Hashes

Package derivations use placeholder hashes. To get the correct hash:

1. Try building: `nix build .#toshy`
2. Build will fail with error showing correct hash
3. Update the hash in the derivation
4. Rebuild

Or use `nix-prefetch-git`:

```sh
nix-prefetch-git https://github.com/RedBearAK/xwaykeyz.git
nix-prefetch-git https://github.com/RedBearAK/toshy.git
```

### Updating Packages

To update to latest commits:

```sh
# In packages/xwaykeyz.nix or packages/toshy.nix
# 1. Get latest commit hash
git ls-remote https://github.com/RedBearAK/xwaykeyz.git HEAD
git ls-remote https://github.com/RedBearAK/toshy.git HEAD

# 2. Update rev in derivation
# 3. Get new hash (build will fail with correct hash)
# 4. Update hash in derivation
```

## Examples

Complete working examples are in `examples/`:

1. **home-manager-basic.nix** - Minimal setup, good starting point
2. **home-manager-advanced.nix** - All options with comments
3. **flake-example.nix** - Complete flake.nix template
4. **nixos-configuration.nix** - Traditional /etc/nixos/configuration.nix

Copy and adapt these for your configuration.

## Troubleshooting

### Build Failures

**Hash mismatch:**
```
error: hash mismatch in fixed-output derivation
  specified: sha256-AAAA...
  got:       sha256-XXX...
```

Update the hash in the derivation to the "got" value.

**Missing dependencies:**

Check `nativeBuildInputs` and `buildInputs` in the derivation. Add missing packages.

### Module Issues

**Services not starting:**

Check logs:
```sh
journalctl --user -u toshy-config.service
systemctl --user status toshy-config.service
```

**Group membership:**

Verify user is in input group:
```sh
groups | grep input
```

If not, ensure NixOS module is enabled or add manually:
```nix
users.users.myuser.extraGroups = [ "input" ];
```

## Resources

- **Full Installation Guide:** `/NIX_FLAKE_INSTALLATION.md`
- **Main README:** `/README.md` (NixOS section)
- **Toshy Wiki:** https://github.com/RedBearAK/toshy/wiki
- **Issues:** https://github.com/RedBearAK/toshy/issues

## Contributing

When contributing to Nix packages:

1. Test builds locally: `nix build .#package-name`
2. Run integration tests: `nix flake check`
3. Verify examples work
4. Update hashes to real values (not placeholders)
5. Document new options in module files
6. Add examples for new features

## License

Same as main Toshy project: GPL-3.0-or-later
