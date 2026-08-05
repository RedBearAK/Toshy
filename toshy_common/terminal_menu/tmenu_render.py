"""
Rendering for the Toshy terminal menu.

toshy_common/terminal_menu/tmenu_render.py

Paints the whole frame on every update: fixed header (title + service
status), scrolling item viewport, and a footer showing the highlighted
item's help text or a transient status message. Full repaint is cheap
at these sizes and avoids incremental-update state bugs.

All chrome is plain ASCII ('[+]', '[x]', '(*)', '>') so the menu stays
legible on a bare Linux console with limited glyph coverage — this tool
is a fallback for broken environments, and the rendering should be the
last thing that can break.

The renderer returns the screen row occupied by each visible item so
mouse hit-testing in tmenu_main is a plain dictionary lookup.
"""

__version__ = '20260804'

import sys
import textwrap

from toshy_common.terminal_menu.tmenu_term import (
    DIM,
    RED,
    BOLD,
    CYAN,
    GREEN,
    RESET,
    YELLOW,
    REVERSE,
    CLEAR_BELOW,
    CURSOR_HOME,
    CLEAR_TO_EOL,
    get_terminal_size,
)
from toshy_common.terminal_menu.tmenu_model import KIND_LABEL, KIND_RADIO, KIND_HEADING, KIND_TOGGLE


MIN_COLUMNS     = 46
MIN_ROWS        = 14

_HEADER_ROWS    = 3     # title, status, separator
_FOOTER_ROWS    = 5     # separator, three help/message lines, key hints

_STATUS_COLORS_DCT = {
    'Active':   GREEN,
    'Inactive': RED,
    'Unknown':  YELLOW,
}


def render_frame(items_lst, selected_index, viewport_top,
                 config_status, sessmon_status, footer_text, footer_is_alert):
    """Paint the frame. Returns (row_to_index_dct, viewport_top).

    viewport_top may be adjusted to keep the selection visible; the
    caller stores the returned value.
    """

    columns, rows = get_terminal_size()

    if columns < MIN_COLUMNS or rows < MIN_ROWS:
        _paint_lines([
            '',
            '  Terminal window too small for the Toshy menu.',
            f'  Need at least {MIN_COLUMNS}x{MIN_ROWS}, '
            f'have {columns}x{rows}.',
            '',
            '  Enlarge the window, or press Q to quit.',
        ])
        return {}, viewport_top

    list_rows = rows - _HEADER_ROWS - _FOOTER_ROWS
    viewport_top = _clamp_viewport(selected_index, viewport_top, list_rows, len(items_lst))

    lines_lst = []
    lines_lst.append(f'{BOLD}  TOSHY TERMINAL MENU{RESET}'
                     f'{DIM}   (Q or Ctrl+C to quit){RESET}')
    lines_lst.append(_status_line(config_status, sessmon_status))
    lines_lst.append(f'{DIM}{"-" * (columns - 1)}{RESET}')

    row_to_index_dct = {}
    for viewport_row in range(list_rows):
        item_index = viewport_top + viewport_row
        if item_index >= len(items_lst):
            lines_lst.append('')
            continue
        screen_row = _HEADER_ROWS + viewport_row + 1     # 1-based terminal row
        row_to_index_dct[screen_row] = item_index
        lines_lst.append(_item_line(
            items_lst[item_index], item_index == selected_index, columns))

    lines_lst.append(f'{DIM}{"-" * (columns - 1)}{RESET}')
    lines_lst.extend(_footer_lines(footer_text, footer_is_alert, columns))
    lines_lst.append(
        f'{DIM}  Arrows/click: move/activate   Space/Enter: toggle   '
        f'Left: collapse{RESET}')

    _paint_lines(lines_lst)
    return row_to_index_dct, viewport_top


def _clamp_viewport(selected_index, viewport_top, list_rows, item_count):
    if item_count <= list_rows:
        return 0
    if selected_index < viewport_top:
        viewport_top = selected_index
    if selected_index >= viewport_top + list_rows:
        viewport_top = selected_index - list_rows + 1
    max_top = max(0, item_count - list_rows)
    return max(0, min(viewport_top, max_top))


def _status_line(config_status, sessmon_status):
    config_color    = _STATUS_COLORS_DCT.get(config_status, YELLOW)
    sessmon_color   = _STATUS_COLORS_DCT.get(sessmon_status, YELLOW)
    return (f'  Config: {config_color}{BOLD}{config_status}{RESET}'
            f'    SessMon: {sessmon_color}{BOLD}{sessmon_status}{RESET}')


def _item_line(item, is_selected, columns):
    marker = '> ' if is_selected else '  '
    indent = '  ' * item.indent

    if item.kind == KIND_HEADING:
        expand_mark = '[-]' if item.expanded else '[+]'
        body = f'{expand_mark} {item.text}'
        styled = f'{BOLD}{CYAN}{body}{RESET}'
    elif item.kind == KIND_TOGGLE:
        check_mark = '[x]' if item.checked else '[ ]'
        body = f'{check_mark} {item.text}'
        styled = body
    elif item.kind == KIND_RADIO:
        radio_mark = '(*)' if item.checked else '( )'
        body = f'{radio_mark} {item.text}'
        styled = body
    elif item.kind == KIND_LABEL:
        body = item.text
        styled = f'{DIM}{body}{RESET}'
    else:                                   # KIND_ACTION
        body = f'  {item.text}'
        styled = body

    if not item.enabled and item.kind != KIND_LABEL:
        styled = f'{DIM}{body}{RESET}'

    line = f' {marker}{indent}{styled}'
    if is_selected:
        # Reverse-video the plain text so selection is visible even
        # where color output is disabled.
        line = f' {REVERSE}{marker}{indent}{body}{RESET}'
    return _truncate_visible(line, columns - 1)


def _footer_lines(footer_text, footer_is_alert, columns):
    color = YELLOW if footer_is_alert else DIM
    wrapped_lst = []
    for paragraph in (footer_text or '').split('\n'):
        if not paragraph:
            continue
        wrapped_lst.extend(textwrap.wrap(paragraph, width=columns - 4))
        if len(wrapped_lst) >= 3:
            break
    wrapped_lst = wrapped_lst[:3]
    while len(wrapped_lst) < 3:
        wrapped_lst.append('')
    return [f'  {color}{line}{RESET}' if line else '' for line in wrapped_lst]


def _truncate_visible(styled_line, max_columns):
    """Truncate to max_columns of visible characters, preserving codes.

    Walks the string tracking visible length, skipping over ESC[...m
    sequences, and appends a reset so truncation can't leak attributes.
    """
    visible_count = 0
    position = 0
    output_parts = []
    while position < len(styled_line) and visible_count < max_columns:
        char = styled_line[position]
        if char == '\x1b':
            sequence_end = styled_line.find('m', position)
            if sequence_end == -1:
                break
            output_parts.append(styled_line[position:sequence_end + 1])
            position = sequence_end + 1
            continue
        output_parts.append(char)
        visible_count += 1
        position += 1
    return ''.join(output_parts) + RESET


def _paint_lines(lines_lst):
    frame_parts = [CURSOR_HOME]
    for line in lines_lst:
        frame_parts.append(line + CLEAR_TO_EOL + '\r\n')
    frame_parts.append(CLEAR_BELOW)
    sys.stdout.write(''.join(frame_parts))
    sys.stdout.flush()

# End of file #
