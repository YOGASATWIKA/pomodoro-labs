#!/usr/bin/env bash
# Pasang / copot Pomodoro Labs untuk pengguna saat ini.
#   ./install.sh          salin ke ~/.local/bin
#   ./install.sh --link   symlink (untuk pengembangan)
#   ./install.sh --uninstall
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/pomodoro-labs"
APP="$HOME/.local/share/applications/pomodoro-labs.desktop"

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -f "$BIN" "$APP"; echo "Dicopot."; exit 0
fi

mkdir -p "$(dirname "$BIN")" "$(dirname "$APP")"
if [[ "${1:-}" == "--link" ]]; then ln -sf "$SRC/pomodoro-labs.py" "$BIN"
else install -m 755 "$SRC/pomodoro-labs.py" "$BIN"; fi
sed "s|@BIN@|$BIN|g" "$SRC/pomodoro-labs.desktop" > "$APP"
echo "Terpasang: $BIN"
