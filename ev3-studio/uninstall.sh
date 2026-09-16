#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/ev3-studio"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"

rm -rf "$INSTALL_DIR"
rm -f "$BIN_DIR/ev3-studio"
rm -f "$DESKTOP_DIR/ev3-studio.desktop"
rm -f "$ICON_DIR/ev3-studio.svg"

printf 'EV3 Studio foi desinstalado da conta do usuário.\n'
printf 'Seus arquivos de projeto .ev3proj não foram removidos.\n'
