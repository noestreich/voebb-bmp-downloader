#!/bin/bash
#
# Startet den Downloader und stellt vorher sicher, dass die virtuelle
# Umgebung benutzbar ist.
#
# Hintergrund: Playwright liegt in .venv. Deren Python ist ein Symlink auf
# das Homebrew-Python (via /usr/local/opt/..., überlebt also Patch-Updates
# und "brew cleanup"). Wird die Formel aber ganz entfernt – etwa durch
# "brew autoremove" oder "brew uninstall" – ist die venv unbrauchbar.
# Dann baut dieses Skript sie automatisch neu auf, statt den Lauf scheitern
# zu lassen. launchd versucht es ohnehin stündlich erneut.

set -uo pipefail

PROJEKT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJEKT/.venv"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  SETUP    $*"; }

# Neuesten brauchbaren Python-Interpreter für den Neuaufbau finden
finde_python() {
    local kandidat
    for kandidat in $(ls -1d /usr/local/opt/python@3.* 2>/dev/null | sort -V -r); do
        local bin
        bin=$(ls -1 "$kandidat"/bin/python3.* 2>/dev/null | head -1)
        [ -x "$bin" ] && { echo "$bin"; return 0; }
    done
    for kandidat in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
        [ -x "$kandidat" ] && { echo "$kandidat"; return 0; }
    done
    return 1
}

baue_venv_neu() {
    local python_bin
    if ! python_bin=$(finde_python); then
        log "FEHLER: kein Python-Interpreter gefunden, Neuaufbau unmöglich."
        return 1
    fi
    log "Baue virtuelle Umgebung neu auf mit $python_bin …"
    rm -rf "$VENV"
    "$python_bin" -m venv "$VENV"                                     || return 1
    "$VENV/bin/python" -m pip install --quiet --upgrade pip           || return 1
    "$VENV/bin/python" -m pip install --quiet -r "$PROJEKT/requirements.txt" || return 1
    "$VENV/bin/python" -m playwright install chromium                 || return 1
    log "Neuaufbau abgeschlossen."
}

# Ist die venv benutzbar? Sonst einmalig neu aufbauen.
if ! "$VENV/bin/python" -c "import playwright" >/dev/null 2>&1; then
    log "Virtuelle Umgebung nicht benutzbar."
    baue_venv_neu || { log "Neuaufbau fehlgeschlagen – Lauf wird abgebrochen."; exit 1; }
fi

exec "$VENV/bin/python" "$PROJEKT/download_bmp.py" "$@"
