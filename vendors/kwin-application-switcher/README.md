# Application Switcher

[latest release](https://github.com/nclarius/kwin-application-switcher/releases/latest) | [view in KDE store](https://store.kde.org/p/1805105)

Extension for KDE's window manager to automatically raise all other visible windows of the same application together when activating one of them, effectively creating application groups to task-switch between.

This gives rise to an application-centric task switching workflow as known from environments such as GNOME or MacOS, where an application’s windows are treated as a group, and task switching can take place at two levels: one mode for switching applications and one mode for switching between windows of an application. 

Raising all windows collectively whenever the application is entered means that all windows belonging to the application are available at the front, and closing or minimizing a window will keep focus on the same application, as the window switched to will be the most recently active one of that application provided that there is any, rather than the most recently active window overall which may belong to a different application.

Seen in the screencast: Switching from Konsole back to Dolphin also brings the other Dolphin window in front of the Konsole windows, and gives focus to it when the other Dolphin window is minimized - whereas without the script, the right Konsole window, being the second most recently active one, would remain on top of the center Dolphin window and be switched to when the most recently active Dolphin window is minimized.

![screenshot](.img/screenshot.gif)

## Installation

### Dependencies

`kwin`.

### Installation via graphical interface

**Please make sure to select the most recent version (v1.7)** in the installation process.

A [bug](https://bugs.kde.org/show_bug.cgi?id=453521) in Discover causes a wrong version to be installed, so using the installation module in System Settings instead is recommended.

1. Install the script via *System Settings* > *Window Management* > *KWin Scripts* > *Get New Scripts …* > search for *Application Switcher* > *Install*.
2. Enable the script by activating its checkbox, and apply the settings.

### Installation via command line

```bash
git clone https://github.com/nclarius/kwin-application-switcher.git
cd kwin-application-switcher
./install.sh
```

## Usage

### Tips

If you are intending to have one mode for switching applications and one mode for switching application windows, you may want to use the following settings:
- Task Switcher (Alt+Tab popup):  
  System Settings > Window Management > Task Switcher >  
  - Main (for switching between applications) >
    - Visualization: Large Icons
    - Only one window per application: checked
    - Shortcuts > All windows (which now means switching applications): set your preferred shortcut pair, e.g. Alt+(Shift+)Tab; Current application: leave empty
  - Alternative (for switching between windows of an application) >
    - Visualization: Thumbnails
    - Only one window per application: unchecked
    - Shortcuts > Current application: set your preferred shortcut pair, e.g. Alt+(Shift+)`; All windows: leave empty
- Task Manager (task bar in the panel):  
  right-click on task bar > Configure Task Manager … > Behavior > Group: By application name; Combine into single button: checked

### Limitations

- The KWin scripting API provides no possibility to distinguish how a window was activated (via alt-tabbing, clicking on the task bar, clicking on the window, or being requested from another process), so the plugin can not be applied selectively to only some activation types.
- The KWin scripting API provides no possibility to manipulate the recently used and stacking order without actually activating the window, so focus will briefly shift as windows are being brought to the front; however this happens so fast it shouldn’t be noticeable.

## Small Print

© 2022-2023 Natalie Clarius \<natalie_clarius@yahoo.de\> [nclarius.github.io](https://nclarius.github.io)

This work is licensed under the GNU General Public License v3.0.  
This program comes with absolutely no warranty.  
This is free software, and you are welcome to redistribute and/or modify it under certain conditions.  

Development was sponsored by user [RedBearAK](https://github.com/RedBearAK).

If you like this project, you can make me happy with a review in the [app store](https://store.kde.org/p/1619690).
