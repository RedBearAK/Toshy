> The [Toshy] readme is like a phd thesis paper.  
> -- No_Sandwich3888 on Reddit

Yes. Yes, it is. So here are some...

# ... Quick Links!

_(See top-right icon here on GitHub for full README table of contents)_

- [How to Install](#how-to-install)
- [How to Uninstall](#how-to-uninstall)
- [Requirements](#requirements)
- [Supported Desktop Environments/Window Managers](#currently-working-desktop-environments-or-window-managers)
- [Supported Linux Distros](#currently-workingtested-linux-distros)
- [Frequently Asked Questions (FAQ)](#faq-frequently-asked-questions)
- [Sponsor/Donate](#sponsor-me--donate)

◊  

# Help others find out about Toshy

Toshy is a pretty unique utility for a very niche audience of Mac users who also use Linux or Linux users who switch between macOS and Linux a lot, and prefer the Mac-style keyboard shortcuts. It's difficult for anyone to even think to look for something like Toshy, or Kinto (the original seed project that Toshy was based on). If you want anyone else to know about Toshy, you'll have to make a post or comment about it somewhere, on your own. 

I spent time making some release announcements on various Linux-related Reddit forums over the past couple of years, where it seemed to be most relevant. But my Reddit account was suddenly "permanently banned" in early January 2025, for no reason that has been provided to me, either by email or in my Reddit messages inbox. So everything I ever posted there is now gone, or at least hidden from Reddit and search engines. I don't really have any interest in ever posting on that site again, even if the account could be unbanned. Before you ask, there was no response to the appeal form. 

I don't really know many other places where it might be considered appropriate to make announcements about the releases/updates of an open source project like this, where it would get the attention of the type of Mac/Linux users who would find it interesting or useful. If you have suggestions, open a (question) issue here. 

◊  

# Current status: Stable Beta (Please Read)

**2025-07-10 UPDATE**: Substantial refactoring of multiple internal components has taken place. There should be very little obvious external sign of the changes, but submit issues if you run into problems. 

**2025-07-01 UPDATE**: Added experimental support for fully `asyncio` implementation of multi-tap functionality. Have a key or combo do different things based on how many times it's tapped within the time limit (25ms default). Does not affect other remaps that aren't marked as multi-tap. 

**2025-06-15 UPDATE**: Added support for Mageia (similar to OpenMandriva and descended from Mandrake/Mandriva distros).

**2025-06-13 UPDATE**: The window context provider KWin script component (for Plasma Wayland) has always had a significant defect in seeing window title changes, such as what happens in apps with a tabbed UI (browsers, file managers, terminals, code editors, etc.). That KWin script has been updated to follow the window title changes via the `captionChanged()` signal, from the KWin API. Now the window title (name) can be added to app class conditionals in the config file, to invoke custom remaps or actions on specific tabs or sub-dialogs with wonky titles. And it will work in Plasma just as reliably as in all other Wayland environments (and X11).

**2025-05-03 UPDATE**: Added support for ALT Linux, another independent distro type. Required prerequisite: Install the 'python3-modules-sqlite3' package, or the setup script will fail immediately with a ModuleNotFoundError. This is unusual, since `sqlite3` is normally part of the standard Python library, but ALT seems to keep some of the standard modules in separate packages.

**2025-03-13 UPDATE**: The Chimera support required adapting the setup script to use `doas` or `run0` if `sudo` is not available to the user. So this is no longer an impediment to installing Toshy.

**2025-03-13 UPDATE**: Added support for Chimera Linux, an independent distro with BSD userland utilities. GUI preferences app will not work until someone adds a Python Tkinter package to Chimera. The current maintainer of other Python packages in Chimera was not interested.

**2025-03-02 UPDATE**: The solution for working with Synergy as a server/host network KVM switch system was expanded to support Deskflow, Input Leap and Barrier. (**_Requires working log file_** for the KVM switch app in all cases.) Client systems are ignored because input cannot be detected by the keymapper, so no remaps would ever be performed on incoming input from the server system, but the keymapper will still operate on a local input device on the client.

**2025-01-18 UPDATE**: Fixed some issues in the `wlroots` window context method, and verified the bulk of the available LXQt Wayland session options seem to work. That includes `labwc`, `sway`, `Hyprland`, `niri`, `wayfire`, and `river` (tested on Tumbleweed). The `kwin_wayland` session option is still untested (unavailable on Tumbleweed for now).

**2024-11-28 UPDATE**: Added support for Pantheon's Wayland session in elementary OS 8.

**2024-10-03 UPDATE**: Fixed the broken COSMIC desktop environment support to work with COSMIC alpha 2 or later (unless they change the relevant Wayland protocol again).

**2024-07-28 UPDATE**: Some basic `wlroots` based Wayland compositor support has been added. See the [Wiki article](https://github.com/RedBearAK/toshy/wiki/Wlroots-Based-Wayland-Compositors).

**2024-07-14 UPDATE**: Toshy was recently mentioned favorably in a video on Framework's YouTube channel, about transitioning from macOS to Linux, by Zach Feldman, a lead software engineer on the Marketplace team at Framework. I discovered this quite by accident, watching the video simply because it was in my recommended videos and the title said it was about macOS and Linux, and I've watched several videos from the Framework team. Imagine my surprise when Zach said one of the more important tools that allowed him to use Linux productively after using macOS for many years was Toshy. 😲🤯 Well, I can't be that surprised, since that's exactly why Toshy (and Kinto) were put together. Toshy references start about 2 minutes into the video:  

https://www.youtube.com/watch?v=g4aUSRi8QX4  

For new updates on the performance advancements, check the dedicated [Wiki page](https://github.com/RedBearAK/toshy/wiki/Performance-Improvement-History).  

◊  

## Main issues you might run into

- **KEYBOARD TYPE**: The Toshy config file tries to automatically identify the "type" of your keyboard based on some pre-existing lists of keyboard device names, which do not have many entries, and there are thousands of keyboard name variants. So your keyboard may be misidentified, leading to modifier keys in the "wrong" place. BE PREPARED to identify the name of your keyboard device (try `toshy-devices` in a terminal) and enter it into the custom list (actually a Python "dictionary") in the config file to fix this problem. The custom entry is designed to be retained even if you reinstall later. There is a sub-menu in the tray icon menu intended to allow temporarily bypassing this problem while you find the device name and enter it in your config file. Go to this FAQ entry for more info:  

    [Keyboard Type Not Correct](https://github.com/RedBearAK/toshy/wiki/FAQ-(Frequently-Asked-Questions)#my-keyboard-is-not-recognized-as-the-correct-type)  

- **INTERNATIONAL KEYBOARD USERS**: The keymapper is evdev-based and has **_no idea_** what keyboard layout you are using. It only sees "key codes", not the symbols on the keys. So if it encounters a combo of key _codes_ you've asked it to remap to something else, it will remap it. This is a problem if for instance you're on an AZERTY keyboard where `A` and `Q` are swapped, and you think you're pressing `Cmd+A` but the keymapper thinks you want to remap `Cmd+Q` to `Alt+F4`. I'm looking into a way to get the keymapper to use the proper layout, but in the meantime, depending on how different your layout is from the standard US layout, this keymapper may either be unusable or may just need some small tweaks to the key definition file to fix a few key positions. Open an issue if you have this kind of problem.  

- **DISTRO SUPPORT**: Toshy will have issues installing on distros not on the [list of supported distros](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros) in the Wiki. If you think your distro is closely related to one on the supported list, try the `./setup_toshy.py list-distros` command, and then use one of the distro names with the `--override-distro` option added to the `./setup_toshy.py install` command. See the [**How to Install**](#how-to-install) section.  

- **STARTUP**: Toshy may seem to run at login, but not do any remapping, needing the use of the debugging command `toshy-debug` in the terminal to troubleshoot. Or, it may just need a restart of the services from the tray icon or with `toshy-services-restart`. Check the output of `toshy-services-log` and `toshy-services-status` first to see if there is an obvious error message that explains the problem. Like not having a compatible GNOME Shell extension installed/enabled to support a Wayland+GNOME session. Other than the Wayland+GNOME situation, I don't really see this much anymore.  

- **INIT SYSTEMS**: On a dual-init distro like MX Linux, if you install Toshy while using SysVinit (default on MX) the installer will avoid installing the `systemd` packages and service unit files. If you then switch to using `systemd` as init at the boot screen (you can do this from the "Advanced" menu) you'll need to re-run the Toshy installer (only once) while using `systemd` to make Toshy work automatically like it does on other distros where the default init is `systemd`. Or, you can just keep running the config manually, like is currently necessary under SysVinit and any other init system besides `systemd`.  

§  

# Toshy README

• • • • • • • 
![Toshy app icon inverse grayscale](./assets/toshy_app_icon_rainbow_inverse_grayscale.svg "Toshy app icon inverse grayscale")
• • • • • • • 
![Toshy app icon inverted](./assets/toshy_app_icon_rainbow_inverse.svg "Toshy app icon inverse")
• • • • • • • 
![Toshy app icon](./assets/toshy_app_icon_rainbow.svg "Toshy app icon")


## Make your Linux keyboard act like a 'Tosh! <br> (or, What the heck is this?!?)

The purpose of Toshy is to match, as closely as possible, the behavior of keyboard shortcuts in macOS while using similar applications in Linux.  

General system-wide shortcuts such as Cmd+Q/W/R/T/A/Z/X/C/V and so on are relatively easy to mimic by just moving the modifier key locations, with `modmaps` specific to each supported keyboard type (and a `modmap` specific to retaining the Ctrl key usage in terminals). A lot of shortcuts in Linux just use `Ctrl` in the place of where macOS would use `Cmd`. But many other shortcut combos from macOS applications have to be remapped onto entirely different shortcut combos in the Linux equivalent application. This is done using application-specific `keymaps`, that only become active when you are using the specified application or window. Some of the keymaps apply to entire groups of apps, like "terminals", "web browsers" or "file managers".  

Toshy is mainly a config file for the `xwaykeyz` Python-based keymapper for Linux (which was forked from `keyszer`, which was in turn forked from `xkeysnail`) along with some commands and apps to more conveniently interact with and manage the keymapper. The Toshy config is not strictly a fork of Kinto, but was based in the beginning entirely on the config file for Kinto.sh by Ben Reaves (https://github.com/rbreaves/kinto or https://kinto.sh). Without Kinto, Toshy would not exist. Using Toshy should feel basically the same as using Kinto, just with some new features and some problems solved.  

All of the basic functionality in the config is inherited from Kinto. Toshy just tries to be a bit fancier in implementing it. Such as auto-detecting the keyboard type (supporting multiple keyboards of different types at the same time), and allowing some preferences be changed without restarting the keymapper.  

Since this project is aimed at an audience who may be used to a typical easy-to-use Mac software app, Toshy is meant to be a "just works" monolithic project, requiring minimal (often zero) configuration to start using it. I see no purpose in forcing myself or any other user into following some complicated instructions to set up the "correct" components to get a project like this to work (custom remaps are a separate issue). So you may see many dependencies installed and services starting that won't necessarily ever be used on your own particular setup. This enables supporting all the Wayland environment varations, a long list of common Linux distros, all sorts of desktop environments, and even easy switching between desktop environments on the same system, **_without needing to ever modify the config file settings_**. At the heart of this is a module that detects all the important aspects of your environment. 

None of this "extra stuff" is harmful to the performance of the keymapper. Any unused services will immediately stop themselves to avoid using resources. Unused Python packages just sit in the Python virtual environment folder taking up a few extra megabytes of disk space. If you're looking for something simple and bespoke, with manual setup for only a specific environment, and you only care about shifting a couple of modifier key positions rather than also normalizing hundreds of shortcut combos in various apps, this probably isn't what you're looking for. In that case try something like `keyd` or `xremap`. But you can always try Toshy and uninstall it if you don't like it.  

> [!IMPORTANT]
> You **_DO NOT_** need to and **_SHOULD NOT_** change any native keyboard shortcuts in Linux apps when using this keymapper config. If you've already changed some existing in-app shortcuts to try to mimic macOS shortcuts, you will need to reset those in-app shortcuts to their defaults. The keymapper config non-destructively (and temporarily, only while enabled) remaps hundreds of Mac-like shortcut combos onto the **_default_** native shortcuts for many apps in Linux, and global shortcuts. If those defaults are not in place, things will appear to "not work".  
>  
> Depending on the desktop environment, there are sometimes a couple of global shortcuts for app launchers and modifier-only shortcuts that need to be changed or disabled for the smoothest experience. Those changes are minimal and easily reversible.  
>  
> Competing techniques of remapping modifier keys like other keymappers or `~/.Xmodmap` should be reversed/disabled before trying to use Toshy, or the resulting virtualized modifier locations won't make much sense. The Toshy installer will make you respond to a warning about `~/.Xmodmap` if it exists, to remind you about potential conflicts.  
>  
> If you're on an Apple keyboard and you chose "Apple" as the hardware keyboard model in a desktop environment like KDE to try to "fix" the modifier locations prior to trying Toshy, this may also interfere with getting the expected results. Leave the keyboard model in the DE settings to whatever it defaulted to, which is usually something like "Generic 101-key". Then Toshy's modifier remaps can take care of making the keyboard behave predictably like an Apple keyboard (even if it is not an Apple keyboard).  

◊  

## Toshifying an Application

A detailed guide to how to identify a window's application class and make a new keymap to apply shortcut remaps to a particular Linux application has been moved into this Wiki article: 

https://github.com/RedBearAK/toshy/wiki/Toshifying-a-New-Linux-Application

◊  

## Windows Support

Toshy has no Windows version, unlike the Kinto.sh project. I was trying to solve a number of issues and add features to the Linux version of Kinto, so that's all I'm focused on for Toshy. The Windows version of Kinto works great. Go check it out if you need Mac-like keyboard shortcuts on Windows. I also contribute to Kinto on the Windows side.  

https://github.com/rbreaves/kinto  
https://kinto.sh  

◊  

## Keyboard Types

Four different keyboard types are supported by Toshy (Windows/PC, Mac/Apple, IBM and Chromebook), just as in Kinto. But Toshy does its best to automatically treat each keyboard device as the correct type in real-time, as you use it, rather than requiring you to change the keyboard type from a menu. This means that you _should_ be able to use an Apple keyboard connected to a PC laptop, or an IBM keyboard connected to a MacBook, and shortcut combos on both the external and internal keyboards should work as expected, with the modifier keys appearing to be in the correct place to "Act like a 'Tosh".  

◊  

## Option-key Special Characters

Toshy includes a complete implementation of the macOS Option-key special characters, including all the "dead key" accent keys, from two keyboard layouts. The standard US keyboard layout, and the "ABC Extended" layout (which is still a US keyboard layout otherwise). This adds up to somewhere over 600 special characters being available, between the two layouts. It works the same way it does on macOS, when you hold the Option or Shift+Option keys. For example, Option+E, then Shift+E, gets you an "E" with Acute accent: É.  

The special characters may not work as expected unless you add a bit of "throttle" delay to the macro output. This is an `xwaykeyz` API function that inserts timing delays in the output of combos that involve modifier keys. There is a general problem with Linux keymappers using `libinput` in a lot of situations, especially in virtual machines, with the modifier key presses being misinterpreted as occuring at a slightly different time, leading to problems with macro output.  

A slight delay will usually clear this right up, but a virtual machine environment may need a few dozen milliseconds to achieve macro stability. In fact it's not just macros, but many shortcuts in general may seem very flaky or unusuble in a VM, and this will impact the Option-key special characters, since it uses Unicode macro sequences.  

A dedicated Unicode processing function was added to `keyszer` (and inherited by `xwaykeyz`) that made it possible to bring the Option-key special characters to Linux, where previously I could only add it to the Windows version of Kinto using AutoHotkey.  

If you're curious about what characters are available and how to access them, the fully documented lists for each layout are available here:  

https://github.com/RedBearAK/optspecialchars

It's important to understand that your actual keyboard layout will have no effect on the layout used by the Option-key special character scheme. The keymapper generally has no idea what your keyboard layout is, and has a tendency to treat your keyboard as if it is always a US layout. This is a problem that needs a solution. I haven't found even so much as a way to reliably detect the active keyboard layout. So currently Toshy works best with a US layout.  

The other problem is that the Unicode entry shortcut (`Shift+Ctrl+U`) only seems to work if you have `ibus` or `fcitx5` set up as your input manager. If not, the special characters (or any other Unicode character sequence) will only work correctly in GTK apps, which seem to have the built-in ability to understand the Shift+Ctrl+U shortcut that invokes Unicode character entry.  

There's no simple way around this, since the keymapper is only designed to send key codes from a virtual keyboard. Unlike AutoHotkey in Windows, which can just "send" a character pasted in an AHK script to an application (although there are potential problems with that if the AHK file encoding is wrong). 

◊  

## General improvements over Kinto

This section was moved to a Wiki page to make the README shorter:  

https://github.com/RedBearAK/toshy/wiki/General-improvements-over-Kinto  

◊  

## Requirements

- Linux (no Windows support planned, use Kinto for Windows)

    - See the full [**list of supported distros**](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros) maintained in the Wiki

- Python >=3.6 (to run the setup script)

- Python >=3.8 (to run the keymapper in its `venv`)

- [**`xwaykeyz`**](https://github.com/RedBearAK/xwaykeyz/) (keymapper for Linux, forked from `keyszer`)

    - Automatically installed by Toshy setup script

- X11/Xorg, or a supported Wayland environment

    - See the full [**list of working DEs/WMs**](#currently-working-desktop-environments-or-window-managers) further down in the README

- `systemd` (Optional. You can manually run the config from terminal, shell script, GUI preferences app, or tray indicator menu, so the basic functionality of the Toshy config can work regardless of the init system in use.)

- D-Bus, and `dbus-python` (but it is possible to install and run without it)

Several Python modules and their dependencies will be installed in a self-contained `venv` (Python virtual environment) folder to support the operation of the keymapper and accompanying "apps" like the tray indicator. These modules are listed (for information only) in the `requirements.txt` file.  

A short list of native packages (and their automatic dependencies) will be installed as the first setup stage on each supported distro type, mostly to allow the `pip` package list to cleanly build and install in the Python `venv`. But some native packages, like `zenity`, are critical for additional functionality that would stop working if they were removed.  

### Specific requirements for certain DEs/WMs

On some Wayland environments it takes extra steps to get the per-app or per-app-group (e.g., "terminals") specific keymapping to work. Special methods need to be used to grab the window context info, and sometimes that means installing something external to Toshy.  

- **`Wayland+Plasma`** sessions have a small glitch where you have to change the focused window once after the Toshy KWin script is installed, to get the app-specific remapping to start working. I am trying a solution that uses a pop-up dialog to create a KWin event that "kickstarts" the KWin script. You should briefly see a dialog appear and then disappear shortly after you log in to a Wayland+Plasma session. This has been working well for some time now.  

- **`Wayland+GNOME`** sessions require one of the GNOME Shell extensions listed in this section to be installed and enabled (see the [**`next section`**](#managing-shell-extensions-in-gnome) below on how to easily download and install GNOME Shell extensions):

    ___
    - **Name: 'Xremap'** (Supports GNOME 3.36/3.38, and 40 or later)
    - UUID: `xremap@k0kubun.com`
    - URL: https://extensions.gnome.org/extension/5060/xremap/
    ___
    - **Name: 'Window Calls Extended'** (Supports GNOME 41 or later)
    - UUID: `window-calls-extended@hseliger.eu`
    - URL: https://extensions.gnome.org/extension/4974/window-calls-extended/
    ___
    - **Name: 'Focused Window D-Bus'** (Supports GNOME 43 or later)
    - UUID: `focused-window-dbus@flexagoon.com`
    - URL: https://extensions.gnome.org/extension/5592/focused-window-d-bus/
    ___

### Managing shell extensions in GNOME

It's very easy to search for and install GNOME Shell extensions now, if you install the "Extension Manager" Flatpak application from Flathub. No need to mess around with downloading a zip file from `extensions.gnome.org` and manually installing/enabling in the terminal, or trying to get the link between a native package and a browser extension working in a web browser. (Certain browsers and distros often make this a painful process.)  

Many distro variants that come with GNOME may need the `AppIndicator and KStatusNotifierItem` extension (or some other extension that enables what GNOME calls "legacy" indicator tray icons) to make the tray icon appear in the top bar, and if you want to use Wayland you'll need one of the extensions from the list above. Ubuntu usually has that exact extension for tray icons already installed and enabled. You will only need the suggested extension (or something similar) if you see nothing in the tray for Toshy after installing and rebooting for the first time after the Toshy install. The Toshy icon will usually look like a rainbow-colored rounded square, with a slighly tilted Command-key "flower" symbol inside it.  

Here's how to install "Extension Manager":  

```sh
flatpak install com.mattjakeman.ExtensionManager
```

... or just:

```sh
flatpak install extensionmanager
```

If the app is not found you may need to enable the Flathub repo on your machine. Go to https://flathub.org/setup for instructions for your distro. (If your distro doesn't even have the "flatpak" command pre-installed, you should reboot after installing the command and enabling the Flathub repo, to activate some necessary environment variables/paths.)  

> [!NOTE]
> The "Extension Manager" Flatpak app is NOT the same thing as the "Extensions" app that sometimes comes pre-installed on GNOME distros. That is a simpler app with no ability to browse the available extensions.  

When you get it installed, you can just use the "Browse" tab in this application to search for the extensions by name and quickly install them.  

There is no risk of any kind of conflict when installing more than one of the compatible shell extensions that provide window context info over D-Bus. Which might be advisable, to reduce the risk of not having a working extension for a while the next time you upgrade your system in-place and wind up with a newer version of GNOME that one or two of the extensions hasn't been updated to support. I expect at least one of the (now three) extensions will always be updated quickly to support the latest GNOME. 

The window context module of the keymapper installed by Toshy will seamlessly jump to trying the other compatible extensions in case one fails or is disabled/uninstalled for any reason. You just need to have at least one from the list installed and enabled, and when it responds over D-Bus to the query from the keymapper it will be marked as the "good" one and used from then on, unless it stops responding. Lather, rinse, repeat.  

The `Xremap` GNOME shell extension is the only one that supports older GNOME versions, so it's the only one that will show up when browsing the extensions list from an environment like Zorin OS 16.x (GNOME 3.38.x) or the distros based on Red Hat Enterprise Linux (clones or RHEL compatibles like AlmaLinux, Rocky Linux, Oracle Linux, EuroLinux, etc.) which are still using GNOME 40.x on the 9.x versions.  

There is a weird bug at times with searching for extensions by name, where you actually have to use the option "Show Unsupported" from the hamburger menu in order to get it to show up. This seems to happen at random, and may be dependent on what is going on with GNOME's extension site. Just make sure that the extension says in its details page that it is compatible with your version of the GNOME shell, and it should be fine to install.  

◊  

## How to Install  

> [!WARNING]
> **_DO NOT_** attempt to manually install Python dependencies 
> with `pip` using the `requirements.txt` file. That file only 
> exists to let GitHub show some dependency info. (This may 
> change at some point in the future, but ignore it for now.)

> [!NOTE]  
> Installer commands and options are now very different from early Toshy releases.  
> **_CentOS 7 and CentOS Stream 8 users_**: run `./prep_centos_before_setup.sh` first.  
> If the prep script doesn't completely work, run it a second time!

1. Verify that your specific distro or basic distro type is [supported](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros) (most are now).  

1. Try the new [bootstrap command](https://github.com/RedBearAK/toshy/wiki/How-to-install-Toshy-with-a-single-command) that will auto-download the branch of your choice, and allow adding install option flags (see below for more info). Default choices are good for most users.  

Or get the zip you want manually, and run the setup script yourself (almost as easy)...

1. Click the big green **`  <> Code  ▼  `** button near the top of the page.  

1. Download the latest zip file from the drop-down. ("Releases" are older.)  

1. Unzip the archive, and open a terminal **_in the resulting folder_**.  

1. Run the Toshy installer script command in the terminal, like this:  

```sh
./setup_toshy.py install
```

If you didn't open the terminal by right-clicking on the folder that was created when the archive was unzipped, you may have to do something like this first:  

```sh
cd ~/Downloads/Toshy[hit Tab to autocomplete the folder name, and Enter]
```

You should now be in a folder called something like `toshy-main` or `toshy-dev_beta`, depending on which branch you downloaded the zip archive from, and you should be able to run the installation command from earlier (`./setup_toshy.py install`).  

Check out the `--options` in the next section if the basic install doesn't work. If you are on KDE Plasma and want a more Mac-like task switching experience, take a look at the `--fancy-pants` option in particular.

### NixOS Installation

> [!NOTE]
> **NixOS requires a different installation approach** due to its declarative system configuration model.

NixOS users cannot use traditional package managers or make direct system changes. Instead, Toshy will generate configuration snippets that you must add to `/etc/nixos/configuration.nix`.

#### Quick Start for NixOS

1. Download and extract Toshy as described above

2. Run the NixOS helper script to generate configuration:
   ```sh
   ./scripts/toshy-nixos-helper.sh
   ```

3. Copy the generated configuration snippet to `/etc/nixos/configuration.nix`

4. Replace `<username>` with your actual username in the configuration

5. Rebuild your system:
   ```sh
   sudo nixos-rebuild switch
   ```

6. Log out and log back in (for group changes to take effect)

7. Run the Toshy installer:
   ```sh
   ./setup_toshy.py install
   ```

The installer will detect NixOS automatically and skip system-level changes (packages, udev rules, user groups). It will only set up the user-space components (Python venv, config files, systemd user services).

#### What Gets Configured Declaratively

The configuration snippet includes:

- **System Packages**: All required dependencies (Python, build tools, libraries)
- **Udev Rules**: Input device access permissions
- **User Groups**: Adding your user to `input` and `systemd-journal` groups
- **Kernel Modules**: Loading the `uinput` module

#### Example NixOS Configuration

Add this to your `/etc/nixos/configuration.nix`:

```nix
{ config, pkgs, ... }:
{
  # Toshy dependencies
  environment.systemPackages = with pkgs; [
    git python3 python3Packages.pip python3Packages.dbus-python
    libnotify zenity cairo gobject-introspection
    libappindicator-gtk3 systemd libxkbcommon wayland
    dbus gcc libjpeg evtest xorg.xset pkg-config
  ];

  # Udev rules for input device access
  services.udev.extraRules = ''
    SUBSYSTEM=="input", GROUP="input", MODE="0660", TAG+="uaccess"
    KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", TAG+="uaccess"
  '';

  # Add your user to required groups (replace myuser)
  users.users.myuser.extraGroups = [ "input" "systemd-journal" ];

  # Load uinput kernel module
  boot.kernelModules = [ "uinput" ];
}
```

#### Troubleshooting NixOS Installation

If the installer shows warnings about missing packages or groups:

1. Verify your `/etc/nixos/configuration.nix` includes all the sections above
2. Ensure you ran `sudo nixos-rebuild switch`
3. Log out and back in if you just added group memberships
4. Check you're in the input group: `groups | grep input`

If you're still having issues, run the installer with verbose output to see exactly what's being skipped:

```sh
./setup_toshy.py install --verbose
```

#### NixOS Flake Installation (Recommended)

> [!TIP]
> **New!** Toshy now provides a Nix flake for fully declarative installation via home-manager.

The flake-based installation is the recommended method for NixOS users as it:
- Provides fully declarative configuration
- Handles all dependencies automatically
- Integrates seamlessly with NixOS and home-manager
- Enables/disables services declaratively
- Simplifies updates and rollbacks

##### Prerequisites

1. Enable flakes in your NixOS configuration:
   ```nix
   # /etc/nixos/configuration.nix
   {
     nix.settings.experimental-features = [ "nix-command" "flakes" ];
   }
   ```

2. Rebuild your system: `sudo nixos-rebuild switch`

##### Installation Methods

###### Method 1: NixOS + Home-Manager (Recommended)

Add Toshy to your `flake.nix`:

```nix
{
  description = "My NixOS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager.url = "github:nix-community/home-manager";

    # Add Toshy
    toshy.url = "github:RedBearAK/toshy";
  };

  outputs = { nixpkgs, home-manager, toshy, ... }: {
    nixosConfigurations.my-machine = nixpkgs.lib.nixosSystem {
      modules = [
        # Optional: System-wide configuration (udev rules, kernel modules)
        toshy.nixosModules.default
        {
          services.toshy.enable = true;
        }

        # Home-manager with Toshy
        home-manager.nixosModules.home-manager
        {
          home-manager.users.myuser = {
            imports = [ toshy.homeManagerModules.default ];

            services.toshy = {
              enable = true;
              autoStart = true;
              enableGui = true;
            };
          };
        }
      ];
    };
  };
}
```

Then rebuild: `sudo nixos-rebuild switch --flake .`

###### Method 2: Standalone Home-Manager

If you use home-manager without NixOS:

```nix
# ~/.config/home-manager/flake.nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager.url = "github:nix-community/home-manager";
    toshy.url = "github:RedBearAK/toshy";
  };

  outputs = { nixpkgs, home-manager, toshy, ... }: {
    homeConfigurations.myuser = home-manager.lib.homeManagerConfiguration {
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      modules = [
        toshy.homeManagerModules.default
        {
          services.toshy = {
            enable = true;
            autoStart = true;
            enableGui = true;
          };
        }
      ];
    };
  };
}
```

Apply: `home-manager switch --flake .`

##### Configuration Options

The home-manager module provides these options:

```nix
services.toshy = {
  enable = true;  # Enable Toshy

  # Optional: Use specific version
  package = pkgs.toshy;

  # Optional: Custom configuration file
  config = ./my-toshy-config.py;

  # Auto-start on login (default: true)
  autoStart = true;

  # Enable GUI components (default: true)
  enableGui = true;
  enableTray = true;

  # Override desktop environment detection
  desktopEnvironment = "kde";  # or "gnome", "sway", etc.

  # Enable verbose logging
  verboseLogging = false;
};
```

##### Customizing Configuration

1. Get the default config:
   ```sh
   nix build github:RedBearAK/toshy#toshy
   cp result/share/toshy/default-toshy-config/toshy_config.py ~/.config/toshy/
   ```

2. Edit `~/.config/toshy/toshy_config.py` to customize key mappings

3. Reference it in your home-manager config:
   ```nix
   services.toshy.config = ./toshy_config.py;
   ```

4. Rebuild: `home-manager switch` or `sudo nixos-rebuild switch`

##### Managing Services

With the flake installation, services are managed declaratively:

```nix
# Enable all services (default)
services.toshy.enable = true;

# Disable auto-start
services.toshy.autoStart = false;

# Disable GUI/tray
services.toshy.enableGui = false;
services.toshy.enableTray = false;
```

Manual service control (if autoStart = false):
```sh
systemctl --user start toshy-config.service
systemctl --user stop toshy-config.service
systemctl --user status toshy-config.service
```

##### Examples

Complete example configurations are available in `nix/examples/`:
- `home-manager-basic.nix` - Simple setup
- `home-manager-advanced.nix` - All options
- `flake-example.nix` - Complete flake template
- `nixos-configuration.nix` - Traditional configuration.nix

##### Updating

Update Toshy flake input:
```sh
nix flake update toshy
sudo nixos-rebuild switch  # or: home-manager switch
```

##### Troubleshooting Flake Installation

**Service won't start:**
- Check logs: `journalctl --user -u toshy-config.service`
- Verify group membership: `groups | grep input`
- System module enabled: `services.toshy.enable = true;` in NixOS config

**Config changes not applying:**
- Ensure `services.toshy.config` points to your file
- Rebuild after changes: `home-manager switch`
- Check config syntax: `python3 ~/.config/toshy/toshy_config.py`

**GUI not appearing:**
- Verify: `services.toshy.enableGui = true;`
- Check tray: `services.toshy.enableTray = true;`
- Log: `journalctl --user -u toshy-tray.service`

### Options for installer script

The installer script has a few different `commands` and `--options` available, as shown in this section.  

```sh
./setup_toshy.py --help
```

Shows a short description of all available commands.  

```sh
./setup_toshy.py install --help
```

Shows a short description of all available options to modify the `install` command. The modifier options can be combined.  

```sh
./setup_toshy.py install --override-distro distro_name
```

This option will force the installer to attempt the install for that distro name/type. You can use this if you have a distro that is not on the distro list yet, but you think it is close enough to one of the existing distros in the list that the installer should do the right things. For instance if you have some very Arch-ish or very Debian-ish distro, or something based on Ubuntu (there are many!) that doesn't identify as one of the "known" distros when you use `show-env` and `list-distros` (see below), then you can try to make it install using one of the related distro names. This will probably work, if the distro is just a minor variation of its parent distro.  

```sh
./setup_toshy.py install --barebones-config
```

This special option will install a "barebones" config file that does no modmapping or keymapping by default (besides a simple example keymap that gives access to a couple of currency symbols, as a demo). The option will also convert an existing Toshy config into a "barebones" config file, but will ask for explicit confirmation. This config will of course not provide any of the features that a normal Toshy config would, other than the ability to use the keymapper in any of the [compatible environments](#currently-working-desktop-environments-or-window-managers).  

The Toshy installer should try to retain your changes inside any of the editable "slices" of the barebones config file, and avoid replacing your barebones config with a regular Toshy config file, **_even if you don't use the same CLI option the next time you run the installer_**. Submit an issue if it doesn't respect your barebones config. Even if that happens, the previous config file should be in the timestamped backup folder that the installer always creates.  

```sh
./setup_toshy.py install --skip-native
```

This is primarily a convenient **debug/development** option. It just bypasses the attempt to install any native package list.  

In theory, you could use this option to get Toshy working on a new distro type that is not currently supported. You could take one of the existing package lists (found inside the installer script file) from a distro type that is closely related to your distro, and try to manually install packages after using this `--skip-native` option, and the `--override-distro` option to provide the installer a "known" distro name. There will of course be errors, particularly during the process of installing/building the Python packages that get installed in the virtual environment folder via the `pip` command. Then you would search the web for what kind of package might fix that error, and try again, with the same options. There will often also be errors to overcome after the install is finished, when trying to launch the tray and GUI apps. Using the `toshy-tray` and `toshy-gui` commands in the terminal will display the errors that prevent those apps from launching or working correctly.  

If you go through this process I hope you'll keep track of exactly what packages you ended up needing to install, and take the time to submit an issue with the package list, distro details, and the native package command(s) you needed to use, so support for the the distro type can be added to the installer.  

One pitfall that is hard to avoid in this process is installing packages that don't actually solve any issue, and then not removing them to verify whether they are truly dependencies. Be careful about that.  

Last, but definitely not least, the "extra" install option:  

```sh
./setup_toshy.py install --fancy-pants
```

This will do the full install, but also add various things that I find convenient, fun, or that somehow make the desktop environment behave more sensibly, which often means "more like macOS".  

At the moment this installer option will do the following: 

- ALL: Installs "Fantasque Sans Mono noLig" font
    - From a fork with no coding ligatures
    - LargeLineHeight-NoLoopK variant
    - Try it in terminals or code editors
    - May look a bit "heavy" on KDE due to forced "stem darkening" in Qt apps
- KDE: Installs "Application Switcher" KWin script (groups apps like macOS/GNOME)
- KDE: Disables task switcher option "Show selected window"
- KDE: Sets the task switcher to "Large Icons" (like macOS/GNOME task switcher)
- KDE: Enables task switcher option "Only one window per application" (makes the task switcher dialog show only a single icon for each application, like macOS/GNOME)

Note that any or all of the "--options" for the `install` command can be combined, as they modify independent aspects of what the `install` command will do:  

```sh
./setup_toshy.py install --override-distro distro-name --skip-native --barebones-config --fancy-pants
```

### Other commands in the setup script

Here are some other things (commands) that are available in the setup script, besides the primary `install` command. These commands are mutually exclusive, just like the `install` command.  

```sh
./setup_toshy.py list-distros
```

This command will print out a list of the distros that the Toshy installer theoretically "knows" how to deal with, as far as knowing the correct package manager to use and having a list of package names that would actually work. Entries from the displayed distro list can be used with the `--override-distro` option for the `install` command.  

```sh
./setup_toshy.py show-env
```

This will just show what the installer will see as the environment when you try to install, but won't actually run the full install process.  

```sh
./setup_toshy.py apply-tweaks
```

Just applies the "desktop tweaks" for the environment, does not do the full install. Might be handy if you have a system with multiple desktop environments.  

```sh
./setup_toshy.py remove-tweaks
```

Just removes the "desktop tweaks" the installer applied. Does not do the full uninstall.  

```sh
./setup_toshy.py install-font
```

Just installs the coding/terminal font Fantasque Sans Mono, a task that is also included in the `install --fancy-pants` or `apply-tweaks --fancy-pants` modified commands. If you didn't use the `--fancy-pants` option in either case, this will install the font indepdently.  

This will only install the font. It won't cause the font to be set as a default for any app, and Linux apps have to be restarted to be able to see a newly installed font in their font selectors.  

```sh
./setup_toshy.py prep-only
```

This will only perform the necessary steps to "prep" the system to make Toshy's user-specific components work correctly. Things like package installs and setting up the `udev` rules file. This `prep-only` command will avoid installing any of Toshy's user components (user services, tray icon, etc.) for the admin user running the command. 

Invoking this command instead of doing the "install" command may require some extra manual steps to get a user's Toshy install fully working, if the user that wants to use Toshy is a non-admin (unprivileged) user with no access to `sudo`. Mainly this might be adding the unprivileged user to the correct `input` group and restarting the system. See the [dedicated Wiki page](https://github.com/RedBearAK/toshy/wiki/Prep-Only-and-Unprivileged-installs) for more information about the use of the `prep-only` command.  

◊  

## How to Uninstall

The `uninstall` command is just another command inside the setup script, so follow the same initial instructions from the "[How to Install](#how-to-install)" section above, but run the setup script with `uninstall` as the command argument, instead of `install`. Like this:  

```sh
./setup_toshy.py uninstall
``` 

Please file an issue if you have some sort of trouble with the `uninstall` command. If you have a multi-desktop system you may need to run the uninstall procedure while logged into KDE if you ran the installer in KDE, due to the KDE-specific components that get installed for Wayland support. Or just manually remove the KWin script from the KWin Scripts control panel.  

◊  

## Currently working/tested Linux distros:

Detailed info on supported Linux distros has been moved into a Wiki article to make the README shorter. Check for notes on your specific distro or distro type if you haven't installed Toshy before. If you aren't using a distro type found on the list, it's extremely unlikely that the Toshy installer will work, even with the `--override_distro` option. The components in Toshy's Python virtual environment are supported by a list of native packages that must first be in place.  

https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros  

You will find these distro groupings in the Wiki article:

- [Fedora and variants](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros#fedora-and-fedora-variants)

- [RHEL, CentOS and clones/compatibles](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros#red-hat-enterprise-linux-rhel-clones-centos-stream)

- [openSUSE Leap / Tumbleweed / Aeon / MicroOS](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros#opensuse-rpm-based-packaging-system)

- [OpenMandriva](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros#openmandriva-dnfrpm-based-descended-from-mandriva-mandrake)

- [Ubuntu and variants](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros#ubuntu-variants-and-ubuntu-based-distros)

- [Debian and variants](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros#debian-and-debian-based-distros)

- [Arch (... BTW) and variants](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros#arch-arch-based-and-related-distros)

- [Independent distros](https://github.com/RedBearAK/toshy/wiki/Supported-Linux-distros#independent-distros)

◊  

## Currently working desktop environments or window managers

> [!NOTE]  
> What is meant in this section by a DE or WM "working" with Toshy is specifically that the keymapper Toshy uses has a method available, when operating in the listed X11/Xorg or Wayland environments, to acquire knowledge about the **_actively focused_** window's application class (e.g., `WM_CLASS` or `app_id` equivalent) and window name/title (e.g., `WM_NAME` or `title` equivalent). This information is **_essential_** to correctly apply app-specific modifier remaps and app-specific shortcut combo remaps. The keymapper may run without this context info, but the results will be very limited and [disappointing](https://github.com/RedBearAK/toshy/wiki/FAQ-(Frequently-Asked-Questions)#how-do-i-know-toshy-is-working-correctly--or-it-sort-of-works-but-sort-of-doesnt-whats-going-on).  

- ### X11/Xorg sessions

    - Any desktop environment or window manager should work _[via `Xlib`]_

- ### Wayland sessions

    - **Cinnamon 6.0 or later** - _[uses custom shell extension]_
    - **COSMIC desktop environment** - _[uses D-Bus service]_
    - **GNOME 3.38, and 40 or later** - _[needs shell extension, see [**Requirements**](#requirements)]_
    - **Hyprland** - _[currently uses `hyprpy` Python module]_
    - **MiracleWM** - _[via `wlroots` method]_
    - **Niri** - _[via `wlroots` method]_
    - **Pantheon** - _[uses D-Bus queries to Gala WM]_
    - **Plasma 5 (KDE)** - _[uses custom KWin script and D-Bus service]_
    - **Plasma 6 (KDE)** - _[uses custom KWin script and D-Bus service]_
    - **Qtile** - _[via `wlroots` method]_
    - **Sway** - _[currently uses `ipc` Python module]_
    - **Wayland compositors with `zwlr_foreign_toplevel_manager_v1` interface**
        - See [Wiki article](https://github.com/RedBearAK/toshy/wiki/Wlroots-Based-Wayland-Compositors) for usage of this method with unknown compositors that may be compatible

If you are in an X11/Xorg login session, the desktop environment or window manager doesn't really matter. The keymapper gets the window class/name/title information directly from the X server using functionality available in the `Xlib` Python module.  

On the other hand, if you are in a Wayland session, it is only possible to obtain the per-application or per-window information (for the app-specific shortcut keymaps) by using solutions that are custom to a limited set of desktop environments (or window managers).  

For Wayland+GNOME this requires at least one of the known compatible GNOME Shell extensions to be installed and enabled. See above in [**Requirements**](#requirements). I do not maintain the GNOME shell extensions, and they frequently need to be updated for new GNOME releases.  

There are specific remaps or overrides of default remaps for several common desktop environments (or distros which have shortcut peculiarities in their default desktop setups). They become active if the desktop environment is detected correctly by the environment evaluation module used by the config file. If that isn't working for some reason, the information about the desktop environment can be placed in some `OVERRIDE` variables in the config file. But open an issue if that seems to be necessary.  

Tiling window managers may need [some adjustments](https://github.com/RedBearAK/toshy/issues/294) in your config file, to be usable while retaining the tiling shortcuts. The example issue at the link is for a user's setup of i3 WM, where the physical `Meta/Super/Win` key was chosen as the `Mod` key in i3 config, on a PC keyboard type. Other WMs or other configuration choices will need modifications of the solution shown.  

◊  

## Usage (changing preferences)

See next section for usage of the Toshy terminal commands to manage the services and keymapper process. This section is about the preferences available via the tray icon menu, or the GUI "Toshy Preferences" app.

The tray icon menu has a few more convenient features that aren't entirely mirrored in the simple GUI app window.  

> [!TIP]  
> Note that changing the items in the submenus from the tray icon menu or the GUI app will cause the behavior of the keymapper config to change **_immediately_** (or within a couple of seconds), without requiring the keymapper process/services to be restarted. You only need to restart the services after editing the config file itself. Preferences are taken care of in memory, and the current state is stored in a small sqlite3 file (which gets preserved if you re-run the Toshy installer). Once you tweak a preference it should stay that way even if you reinstall.  

In the tray icon menu, you'll find a number of useful functions: 

- Top items show services status (not clickable)
- Toggle to disable/enable autostart of services
- Items to (re)start or stop the services
- Items to (re)start or stop just the config script
- Preferences submenu
- OptSpec Layout submenu
- Keyboard Type submenu
- Item to open the GUI app
- Item to open the Toshy config folder
- Item to show the services log (journal)
- Items to disable or remove the tray icon

### Why there are separate items for "Services" and "Config-Only"

On some distros there may be some reason the `systemd` services can't run, or you simply don't want them to be enabled. For instance, CentOS 7 supports `systemd` services in general, but had the capacity for "user" services completely disabled, and Toshy uses "user" services. Some distros also don't use `systemd` at all as the init system, so the services won't exist. For these cases, the "Config-Only" items provide a simple way to start just the keymapper config process, if you don't feel like setting up your own auto-start item that will run the `toshy-config-start` command. The lack of `systemd` and `loginctl` will mean that Toshy won't have the multi-user support that will otherwise be present. Not a big deal on a single-user system.  

### Preferences submenu

Here are the preferences that are currently available:  

- `Alt_Gr on Right Cmd`
- `CapsLock is Cmd`
- `CapsLock is Esc & Cmd`
- `Enter is Ent & Cmd`
- `Sublime3 in VSCode`
- `Forced Numpad`
- `Media Arrows Fix`

And what each of these preferences do:  

`Alt_Gr on Right Cmd` - International keyboard users will need to enable this to get to the additional ISO level 3 characters that they would normally reach by using the `Alt_Gr` key on the right side of the Space bar. Otherwise the Toshy config will turn that key into another Command key equivalent, like the key on the left side of the space bar. Note that this only fixes one aspect of the issues that non-US layout users may have with the keymapper.  

`CapsLock is Cmd` - Turns the CapsLock key into an additional Command key equivalent.  

`CapsLock is Esc & Cmd` - Turns the CapsLock key into a multi-purpose key. Escape if tapped, Command if held and combined with another key. (This can be easily modified to make the key `Esc & Ctrl` instead.)  

`Enter is Ent & Cmd` - Turns the Enter key into a multi-purpose key. Enter if tapped, Command if held and combined with another key.  

`Sublime3 in VSCode` - Enables Sublime 3 keyboard shortcut variations in VSCode variants, instead of native VSCode shortcuts.  

`Forced Numpad` - Enabled by default, this causes a PC keyboard's numeric keypad to simulate how a full-sized Apple keyboard behaves in macOS, where the keypad always acts like a numeric keypad. If you need the navigation functions, this can be disabled from the tray icon menu or GUI app, or with Option+NumLock (Fn+Clear also works on an Apple keyboard). The "Clear" key on an Apple keyboard is actually a NumLock key.  

`Media Arrows Fix` - If you have a laptop like mine where they put "media" functions (PlayPause/Stop/Rew/Fwd) on the arrow/cursor keys (when holding the `Fn` key), this preference option will "fix" them by letting the arrow keys behave like the arrow keys on a MacBook instead. They will be PgUp/PgDn/Home/End when holding the `Fn` key, and as long as the `Fn` key is included you can use them in keyboard shortcuts like `Fn+Shift+PgDn` (to select a page of text below the cursor, for example).  

### OptSpec Layout submenu

The `OptSpec Layout` submenu in the tray icon (or the radio buttons in the GUI app) shows which hard-coded Option-key special character layout is currently enabled in the Toshy config. Toggling one of the other items should almost immediately cause the layout to change or be disabled if desired.  

### Keyboard Type submenu

This submenu is a sort of temporary hack to force all attached keyboard devices to be seen as a specific type, which disables on-the-fly auto-adaptation, in case your keyboard type is being misidentified. You will receive a notification warning that this is only meant as a temporary fix while you follow the instructions to get the config file to correctly identify your keyboard type. If you restart Toshy, the setting will not be saved.  

The main reason you'd need to use this is when a keyboard that is not made by Apple either was made for use with macOS, or just has the modifier keys next to the Space bar swapped like an Apple keyboard (common in small keyboards made to work with multiple devices including iOS/iPadOS devices), so you need to force it to be treated like an Apple keyboard. These types of keyboards can't be easily identified as the correct type by just looking at the device name.  

After verifying that the forced keyboard type puts the modifiers in the correct place to work with muscle memory from using an Apple keyboard with macOS, you'll want to fix this permanently by opening your config file and editing the custom dictionary item to make the config see your device name as the correct type. See [here](#my-keyboard-is-not-recognized-as-the-correct-type) for more information.  

◊  

## Usage (terminal commands)

See above section for the GUI tools and preferences explanations. This section is only about the Toshy terminal commands. 

Toshy does its best to set itself up automatically on any Linux system that uses `systemd` and that is a "known" Linux distro type that the installer knows how to deal with (i.e., has a list of the correct native support packages to install, and knows how to use the package manager). Generally this means distros that use one of these package managers:  

- `apk`
- `apt`
- `dnf`
- `eopkg`
- `pacman`
- `rpm-ostree`
- `transactional-update`
- `xbps-install`
- `zypper`

If the install was successful, there should be a number of different `toshy-*` terminal commands available to check the status of the Toshy `systemd` user services (the services are not system-wide, in an attempt to support multi-user setups and support Wayland environments more easily) and do useful like stop/start/restart the services.  

Toshy primarily consists of two separate `systemd` services meant to work together, with one monitoring the other, so the shell commands are meant to make working with the paired services much easier.  

> [!NOTE]  
> (There are now multiple other services, but they will only stay active in a specific Wayland environment, creating a D-Bus service for the keymapper to query. The D-Bus service in turn acqquires data from some source with the necessary active/focused window info, such as a KWin script in Plasma, or events from a Wayland protocol interface in `wlroots` or COSMIC. If you aren't in one of the relevant environments, these extra service units should all be inactive a few seconds after all the services start/restart.)  

The commands are copied into `~/.local/bin/`, and you will be prompted to let the installer script automatically add that location to your user's `PATH` if it is not present in the default `PATH` variable. It depends on the distro whether that location is already set up as part of the path or not, so you may not see this prompt if it's not necessary.  

Originally the local/bin location was added to the user's `PATH` in their shell's RC file. But this made the commands only available in a terminal app. The Toshy installer now adds `~/.local/bin/` to the `PATH` in a more appropriate place, the `~/.profile` file, which makes the commands available throughout the login session, even if you aren't in a terminal. This means the commands should work in startup scripts and app launchers that are capable of running raw commands.  

If for any reason you need to fix the `PATH`, such as having deleted or modified `~/.profile` in a way that removed the `PATH` addition, an easy way to fix that is to run this script that re-installs the terminal commands in the same way they were initially installed:  

```sh
~/.config/toshy/scripts/toshy-bincommands-setup.sh
```

These are the main commands for managing and checking the services:  

```
toshy-services-restart
toshy-services-start
toshy-services-stop
```

```
toshy-services-log      (shows journalctl output for Toshy services)
toshy-services-status   (shows the current state of all Toshy services)
```

To disable or re-enable the Toshy services (to prevent or restore autostart at login), use the commands below. It should still be possible to start/restart the services with the commands above if they are disabled. Using the "enable" command in turn will not automatically start the services immediately if they are not running (but the services will then autostart at the next login). If the services are enabled they can be stopped at any time with the command above, but the enabled services will start automatically at the next login. (NEW: This can finally also be dealt with in the tray icon menu, by toggling the `Autostart Toshy Services` item near the top of the menu.)  

```
toshy-services-disable  (services can still be started/stopped manually)
toshy-services-enable   (does not auto-start the service until next login)
```

If you'd like to completely uninstall or re-install the Toshy services, use the commands below. These are the same commands used by the Toshy installer to set up the services.  

```
toshy-systemd-remove    (stops and removes the systemd service units)
toshy-systemd-setup     (installs and starts the systemd service units)
```

The following commands are also available, and meant to allow manually running just the Toshy config file, without any reliance on `systemd`. These will automatically stop the `systemd` services so there is no conflict, for instance if you need to run the `-debug` or `-verbose-start` version of the command (same thing) to debug a shortcut that is not working as expected, or find out how you broke the config file.  

Restarting the Toshy services, either with one of the above commands or from the GUI preferences app or tray icon menu, will stop any manual config process and return to running the Toshy config as a `systemd` service. All the commands are designed to work together as conveniently as possible.  

```
toshy-config-restart
toshy-config-start
toshy-config-stop
```

```
toshy-debug                 (newer alias of 'toshy-config-start-verbose')
toshy-config-verbose-start  (older alias of 'toshy-config-start-verbose')
toshy-config-start-verbose  (show debugging output in the terminal)
```

There are some informative commands that will print different kinds of useful output. These commands may be helpful when troubleshooting or making reports:  

```
toshy-env                   (show what Toshy sees as the "environment")
toshy-devices               (show the keymapper's list of evdev devices)
toshy-versions              (show versions of some major Toshy components)
```

To see a unique identifier that can be used to limit a keymap (or modmap) to only existing (if you use an `if` statement) or only being active on a single machine (if you use it in the `when` conditional of the keymap/modmap), use the `toshy-machine-id` command below. The machine ID that will be shown is a shortened (truncated) hash of the machine ID used by DBus and/or `systemd`. This may be useful if you want to sync a single config file between multiple machines, and one of them has a peculiar keyboard or some hardware/media keys that need to be remapped differently from other machines. This would mostly apply to laptop keyboards. The ID may change if you reinstall Linux on the same machine.  

```
toshy-machine-id            (show ID that can be used to limit a keymap/modmap)
```

For changing the function keys mode of a keyboard device that uses the `hid_apple` device driver/kernel module, use this command:  

```
toshy-fnmode                    (change fnmode with interactive prompts)
toshy-fnmode --help             (show usage/options)
toshy-fnmode --info             (show current status of fnmode)
toshy-fnmode [--option] [mode]  (change fnmode non-interactively)
```

To activate the Toshy Python virtual environment for doing things like running the keymapper command directly instead of through one of the launcher scripts, it is necessary to first run this command:  

```
source toshy-venv
```

There are also some desktop apps that will be found in most Linux app launchers (like "Albert" or "Ulauncher") or application menus in Linux desktop environments:  

- Toshy Preferences
- Toshy Tray Icon

You may find them under a "Utilities" folder in some application menus (such as the IceWM menu). Or possibly under "Accessories" (LXDE menu).  

Both of these apps will show the current status of the `systemd` services, and allow the immediate changing of the exposed optional features, as well as stopping or restarting the Toshy services. The tray icon menu also allows opening the Preferences app, and opening the `~/.config/toshy` folder if you need to edit the config file.  

If the desktop apps aren't working for some reason, it may be useful to try to launch them from a terminal and see if they have any error output:  

```
# Run the newer GTK-4 version
toshy-gui

# Run the older Tkinter version
toshy-gui --tk

# Tray icon indicator app
toshy-tray
```

The GUI Preferences app started as a Tkinter app but has now been converted to GTK-4 in 25.07.1 or later, with some extra features to more closely match the tray indicator app menu.  Really only useful for those who can't use `AppIndicator` apps for some reason.  

◊  

## FAQ (Frequently Asked Questions)

The lengthy FAQ section has been moved to a Wiki page to make the README shorter:  

https://github.com/RedBearAK/toshy/wiki/FAQ-(Frequently-Asked-Questions)

◊  

## Sponsor Me / Donate

This type of project takes extraordinary amounts of time and effort to work around weird problems in different distros and develop the methods to allow the keymapper to perform app-specific remapping in all the different Wayland environments. If you feel like I did something useful by creating this, and you'd like me to be able to spend time maintaining and improving it, throw some money at me via one of these platforms:  

<a href="https://www.buymeacoffee.com/RedBearAK"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=&slug=RedBearAK&button_colour=865e3c&font_colour=ffffff&font_family=Bree&outline_colour=ffffff&coffee_colour=FFDD00" /></a>

https://buymeacoffee.com/RedBearAK

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/G2G34VVZW)

https://ko-fi.com/RedBearAK

Thanks for checking out Toshy!  

§  

