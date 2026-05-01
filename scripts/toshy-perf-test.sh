#!/usr/bin/env bash
#
# toshy-keymapper-perf
#
# Measure CPU cycles consumed by the running xwaykeyz keymapper during
# a fixed window of typing activity. Typing happens directly in this
# terminal — the script counts keystrokes and reports total cycles,
# cycles per character, and cycles per second.
#
# Usage:
#     toshy-keymapper-perf                # 20 sec test, 5 sec prep
#     toshy-keymapper-perf 30             # 30 sec test, 5 sec prep
#     toshy-keymapper-perf 30 10          # 30 sec test, 10 sec prep
#
# Notes:
#   - Type directly in THIS terminal during the GO window.
#   - 'perf' must be installed (linux-tools-common / perf / linux-perf).
#   - If xwaykeyz runs as root (system service), run this script with sudo.

set -u

# shellcheck disable=SC2034
VERSION='20260429'

DURATION="${1:-20}"
PREP="${2:-5}"

# How long to keep swallowing keystrokes after the test window closes,
# to absorb fingers-in-motion overrun. Counted toward neither typing
# stats nor cycle measurement.
DRAIN_SECONDS=1


# ── Color codes (only when stdout is a TTY) ───────────────────────────────
if [[ -t 1 ]]; then
    RED=$'\033[1;31m'; GRN=$'\033[1;32m'
    YLW=$'\033[1;33m'; CYN=$'\033[1;36m'
    DIM=$'\033[2m';    BLD=$'\033[1m'
    RST=$'\033[0m'
else
    RED=""; GRN=""; YLW=""; CYN=""; DIM=""; BLD=""; RST=""
fi


# ── Cleanup on exit / interrupt ──────────────────────────────────────────
TMPFILE=""
PERF_PID=""
ORIG_STTY=""

cleanup() {
    [[ -n "$ORIG_STTY" ]] && stty "$ORIG_STTY" 2>/dev/null
    if [[ -n "$PERF_PID" ]] && kill -0 "$PERF_PID" 2>/dev/null; then
        kill "$PERF_PID" 2>/dev/null || true
    fi
    [[ -n "$TMPFILE" ]] && rm -f "$TMPFILE"
}
trap cleanup EXIT INT TERM


# ── Sanity checks ────────────────────────────────────────────────────────
if [[ ! -t 0 ]]; then
    printf '%s\n' "${RED}ERROR:${RST} stdin is not a terminal. Run this script in an interactive shell."
    exit 1
fi

if ! command -v perf >/dev/null 2>&1; then
    printf '%s\n' "${RED}ERROR:${RST} 'perf' command not found."
    printf '%s\n' "  Install via: 'sudo apt install linux-tools-common'   (Debian/Ubuntu)"
    printf '%s\n' "          or:  'sudo dnf install perf'                  (Fedora/RHEL)"
    printf '%s\n' "          or:  'sudo pacman -S perf'                    (Arch)"
    exit 1
fi

mapfile -t PIDS < <(pgrep -f 'xwaykeyz')

if (( ${#PIDS[@]} == 0 )); then
    printf '%s\n' "${RED}ERROR:${RST} No xwaykeyz process found. Is Toshy running?"
    exit 1
fi

if (( ${#PIDS[@]} > 1 )); then
    printf '%s\n' "${RED}ERROR:${RST} Multiple xwaykeyz processes found, refusing to guess:"
    for p in "${PIDS[@]}"; do
        ps -p "$p" -o pid=,cmd= 2>/dev/null | sed 's/^/    /'
    done
    exit 1
fi

PID="${PIDS[0]}"


# ── Banner ────────────────────────────────────────────────────────────────
printf '\n'
printf '%s\n' "${CYN}━━━━━━━━━ Toshy Keymapper CPU Cycle Test ━━━━━━━━━${RST}"
printf '  %-18s %s\n'   "Target PID:"        "$PID"
printf '  %-18s %s\n'   "Command:"           "$(ps -p "$PID" -o cmd= | head -c 60)"
printf '  %-18s %s s\n' "Prep countdown:"    "$PREP"
printf '  %-18s %s s\n' "Measurement time:"  "$DURATION"
printf '%s\n' "${CYN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
printf '\n'
printf '%s\n' "${YLW}>>> Type in THIS terminal during the GO window. <<<${RST}"
printf '\n'


# ── Prep countdown ────────────────────────────────────────────────────────
for ((i=PREP; i>0; i--)); do
    printf "\r  Starting in ${YLW}%2d${RST} seconds... " "$i"
    sleep 1
done
printf "\r%-50s\r" ""

printf '\n'
printf '%s\n' "${GRN}━━━━━ GO! TYPE NOW for ${DURATION} seconds ━━━━━${RST}"
printf '\n'
printf '> '


# ── Measurement ───────────────────────────────────────────────────────────
TMPFILE=$(mktemp)

# Switch terminal to raw-ish mode: char-by-char input, no terminal echo
# (we'll echo manually so we have control over backspace behavior, etc.)
ORIG_STTY=$(stty -g)
stty -icanon -echo min 0 time 0

# Start perf in background
perf stat -e cycles,instructions -p "$PID" sleep "$DURATION" 2>"$TMPFILE" &
PERF_PID=$!

CHARS=0
SECONDS=0

while (( SECONDS < DURATION )); do
    if IFS= read -t 0.05 -r -n 1 ch; then
        ((CHARS++))
        case "$ch" in
            $'\x7f'|$'\b')
                # Backspace: visually erase the previous character
                printf '\b \b'
                ;;
            *)
                printf '%s' "$ch"
                ;;
        esac
    fi
done

# Drain any in-flight keystrokes from finger overrun.
# Terminal stays in raw mode and we silently consume (don't echo, don't count)
# anything that arrives during this grace period.
DRAIN_END=$((SECONDS + DRAIN_SECONDS))
while (( SECONDS < DRAIN_END )); do
    IFS= read -t 0.05 -r -n 1 _ || true
done

# Restore terminal settings
stty "$ORIG_STTY"
ORIG_STTY=""

wait "$PERF_PID" 2>/dev/null
PERF_EXIT=$?
PERF_PID=""

printf '\n\n'
printf '%s\n' "${RED}━━━━━━━━━━━━━━ STOP ━━━━━━━━━━━━━━${RST}"
printf '\n'


# ── Parse perf output ────────────────────────────────────────────────────
if (( PERF_EXIT != 0 )); then
    printf '%s\n' "${RED}ERROR:${RST} perf exited with code $PERF_EXIT."
    printf '%s\n' "Captured output:"
    cat "$TMPFILE"
    printf '\n'
    printf '%s\n' "${DIM}If permission denied, try sudo, or check kernel.perf_event_paranoid.${RST}"
    exit 1
fi

# Match 'cycles' or 'cycles:u' or 'cycles:k' (perf may add :u/:k suffix
# when restricted to user-only or kernel-only counter access).
CYCLES=$(awk '$2 ~ /^cycles(:[uk])?$/ {gsub(",","",$1); print $1; exit}' "$TMPFILE")
INSTRUCTIONS=$(awk '$2 ~ /^instructions(:[uk])?$/ {gsub(",","",$1); print $1; exit}' "$TMPFILE")

if [[ -z "$CYCLES" ]]; then
    printf '%s\n' "${RED}ERROR:${RST} Could not parse cycles from perf output:"
    cat "$TMPFILE"
    exit 1
fi


# ── Compute and display results ──────────────────────────────────────────

# Locale-aware number formatting with thousands separators; fall back gracefully
fmt_num() {
    LC_NUMERIC=en_US.UTF-8 printf "%'d" "$1" 2>/dev/null || printf "%d" "$1"
}

if (( CHARS > 0 )); then
    CYCLES_PER_CHAR=$((CYCLES / CHARS))
else
    CYCLES_PER_CHAR=0
fi

CYCLES_PER_SEC=$((CYCLES / DURATION))

# IPC (instructions per cycle) needs float division, use awk
if [[ -n "$INSTRUCTIONS" ]] && (( CYCLES > 0 )); then
    IPC=$(awk "BEGIN{printf \"%.2f\", $INSTRUCTIONS / $CYCLES}")
else
    IPC="n/a"
fi

printf '%s\n' "${CYN}━━━━━━━━━━━━━━━━━━ Results ━━━━━━━━━━━━━━━━━━${RST}"
printf '  %-24s %s\n'    "Characters typed:"      "$(fmt_num "$CHARS")"
printf '  %-24s %s s\n'  "Time elapsed:"          "$DURATION"
printf '  %-24s %s\n'    "Total cycles:"          "$(fmt_num "$CYCLES")"
if [[ -n "$INSTRUCTIONS" ]]; then
    printf '  %-24s %s\n'    "Total instructions:"    "$(fmt_num "$INSTRUCTIONS")"
fi
printf '  %-24s %s\n'    "IPC (instr/cycle):"     "$IPC"
printf '%s\n' "  ${DIM}─────────────────────────────────${RST}"
printf '  %-24s %s\n'    "Cycles per character:"  "${BLD}$(fmt_num "$CYCLES_PER_CHAR")${RST}"
printf '  %-24s %s\n'    "Cycles per second:"     "${BLD}$(fmt_num "$CYCLES_PER_SEC")${RST}"
printf '%s\n' "${CYN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
printf '\n'
printf '%s\n' "${DIM}Note: each keystroke produces both a press and release event for${RST}"
printf '%s\n' "${DIM}the keymapper, so 'cycles per character' counts work for ~2 events.${RST}"
printf '%s\n' "${DIM}For relative comparison across config revisions, this is fine —${RST}"
printf '%s\n' "${DIM}just aim for similar typing rate and content across runs.${RST}"
printf '\n'

# End of file #
