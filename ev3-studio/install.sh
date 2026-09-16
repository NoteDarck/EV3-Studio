#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ev3-studio"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/ev3-studio"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"

command -v python3 >/dev/null || { echo "Erro: Python 3 não encontrado."; exit 1; }
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

# Copia o programa sem carregar a própria pasta de instalação dentro dela.
if [[ "$SOURCE_DIR" != "$INSTALL_DIR" ]]; then
  rm -rf "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
  cp -a "$SOURCE_DIR"/. "$INSTALL_DIR"/
fi

python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
if ! "$INSTALL_DIR/.venv/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"; then
  echo
  echo "Erro ao instalar as dependências, provavelmente durante a compilação do PyBullet."
  echo "Ubuntu/Debian: sudo apt install build-essential"
  echo "Arch/CachyOS:  sudo pacman -S --needed base-devel"
  echo "Depois execute novamente: ./install.sh"
  exit 1
fi

cp "$INSTALL_DIR/assets/ev3-studio.svg" "$ICON_DIR/ev3-studio.svg"
cat > "$BIN_DIR/ev3-studio" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/ev3-studio"

cat > "$DESKTOP_DIR/ev3-studio.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=EV3 Studio
Comment=Programação visual do LEGO Mindstorms EV3
Exec=$BIN_DIR/ev3-studio
Icon=ev3-studio
Terminal=false
Categories=Education;Development;Science;
Keywords=EV3;LEGO;Robótica;Blockly;Python;
StartupWMClass=EV3 Studio
EOF
chmod +x "$DESKTOP_DIR/ev3-studio.desktop"

printf '\nInstalação concluída.\n'
printf 'Abra pelo menu de aplicativos ou execute: %s\n' "$BIN_DIR/ev3-studio"
printf 'Se o comando não for encontrado, adicione ~/.local/bin ao PATH.\n'
