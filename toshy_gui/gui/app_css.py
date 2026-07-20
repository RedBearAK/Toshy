#!/usr/bin/env python3
__version__ = '20260719'
"""
Centralized application CSS for the Toshy GTK4 preferences app.

toshy_gui/gui/app_css.py

All panel styling lives here as a single display-wide stylesheet, applied
exactly once by the main window on realize. Panels import their sizing
constants from this module instead of defining their own, and must NOT
install their own display-wide CSS providers (that was the old pattern,
and it caused per-panel duplicate rules and cross-panel collisions).

Theme adaptation: colors reference the libadwaita named palette (e.g.
@window_fg_color), which libadwaita redefines live when the color scheme
changes. This gives correct per-theme colors in both light and dark modes
without any theme-detection code.
"""

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from toshy_common.logger import debug


# Help button sizes per panel (px). Each panel imports its own constant,
# typically aliased to HELP_BUTTON_SIZE locally to keep panel code simple.
SERVICE_HELP_BTN_SIZE   = 20
SETTINGS_HELP_BTN_SIZE  = 18
TOOLS_HELP_BTN_SIZE     = 24
BOTTOM_HELP_BTN_SIZE    = 36

# Section header bar (the gray "pill" behind group headers in the settings
# panel columns). Background is a tint of the theme foreground color, so it
# automatically reads as a darker pill in light mode and a lighter pill in
# dark mode, with full-contrast text in both.
HEADER_BAR_BG_ALPHA     = 0.12  # 0.0 - 1.0, higher = stronger pill background

# Service panel font sizing
HEADING_FONT_SIZE       = 22
SERVICE_FONT_SIZE       = 18

# Monospace font stack for service status readouts
MONO_FONT_FAMILIES      = ( '"FantasqueSansMNoLigNerdFont", '
                            '"JetBrains Mono", "Fira Code", '
                            '"SF Mono", "Monaco", "Inconsolata", '
                            '"Roboto Mono", "Ubuntu Mono", '
                            '"Consolas", "DejaVu Sans Mono", monospace')


APP_CSS = f"""
/* ------------------------------------------------------------------ */
/* Shared: section group headers                                       */
/* ------------------------------------------------------------------ */

.control-group-header {{
    font-size: 14px;
    font-weight: bold;
    color: alpha(currentColor, 0.7);
}}
.control-group-header-bar {{
    background-color: alpha(@window_fg_color, {HEADER_BAR_BG_ALPHA});
    border-radius: 6px;
    padding: 4px 8px;
}}
.control-group-header-bar .control-group-header {{
    color: @window_fg_color;
}}

/* ------------------------------------------------------------------ */
/* Service panel                                                       */
/* ------------------------------------------------------------------ */

.heading {{
    font-size: {HEADING_FONT_SIZE}px;
    font-weight: bold;
}}
.service-help-button {{
    min-width: {SERVICE_HELP_BTN_SIZE}px;
    min-height: {SERVICE_HELP_BTN_SIZE}px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
}}
.help-text {{
    font-size: 13px;
    line-height: 1.4;
}}
.service-status {{
    font-family: {MONO_FONT_FAMILIES};
    font-size: 12px;
    font-weight: bold;
}}
.service-label {{
    font-family: {MONO_FONT_FAMILIES};
    font-size: {SERVICE_FONT_SIZE}px;
    font-weight: bold;
}}
.service-value {{
    font-family: {MONO_FONT_FAMILIES};
    font-size: {SERVICE_FONT_SIZE}px;
    font-weight: bold;
}}

/* ------------------------------------------------------------------ */
/* Settings panel                                                      */
/* ------------------------------------------------------------------ */

.settings-help-button {{
    min-width: {SETTINGS_HELP_BTN_SIZE}px;
    min-height: {SETTINGS_HELP_BTN_SIZE}px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
}}
.switch-control {{
    margin-right: 8px;
}}
.radio-control {{
    margin-right: 8px;
}}

/* ------------------------------------------------------------------ */
/* Tools panel                                                         */
/* ------------------------------------------------------------------ */

.left-column {{
    margin-top: 10px;
}}
.tools-help-button {{
    min-width: {TOOLS_HELP_BTN_SIZE}px;
    min-height: {TOOLS_HELP_BTN_SIZE}px;
    padding: 2px;
    font-size: 12px;
    font-weight: bold;
}}
.action-button {{
    min-height: 36px;
}}

/* ------------------------------------------------------------------ */
/* Bottom panel                                                        */
/* ------------------------------------------------------------------ */

.debug-border {{
    border: 2px solid red;
    background-color: alpha(red, 0.1);
}}
.bottom-help-button {{
    min-width: {BOTTOM_HELP_BTN_SIZE}px;
    min-height: {BOTTOM_HELP_BTN_SIZE}px;
    padding: 0px;
    font-size: 18px;
    font-weight: bold;
}}
.version-info {{
    font-size: 14px;
    font-weight: bold;
    color: alpha(currentColor, 0.8);
}}
.info-text {{
    font-size: 20px;
    font-style: italic;
    color: alpha(currentColor, 0.6);
}}

/* NOTE: Historically defined by BOTH the tools panel (bold, margin) and
   the bottom panel (24px, bold, margin) as display-wide rules, so the
   merged result below is what both labels have actually been rendering
   with. Split into per-panel classes if they should ever differ. */
.control-label {{
    font-size: 24px;
    font-weight: bold;
    margin-right: 8px;
}}
"""


_css_applied = False


def apply_app_css(display):
    """Install the application stylesheet on the given display, once.

    Called by the main window on realize. Safe to call again (no-op after
    the first successful application). Complains loudly if the display is
    missing rather than silently skipping the app's entire styling.
    """
    global _css_applied

    if _css_applied:
        debug("app_css: stylesheet already applied, skipping")
        return

    if display is None:
        debug("app_css: ERROR: no display available, app styling NOT applied!")
        return

    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(APP_CSS, -1)

    Gtk.StyleContext.add_provider_for_display(
        display,
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    _css_applied = True
    debug("app_css: application stylesheet applied")

# End of file #
