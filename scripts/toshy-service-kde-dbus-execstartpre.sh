#!/usr/bin/env bash

# Function to check if KWin is responding to DBus
kwin_responding() {
    # Use gdbus instead of qdbus (always available on nearly all Linux distros)
    gdbus call --session --dest org.kde.KWin --object-path /KWin \
        --method org.kde.KWin.currentDesktop &>/dev/null
}

# Wait for KWin to be ready
while true; do
    if kwin_responding; then
        sleep 1
        break
    else
        sleep 1
    fi
done
