import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QSplitter, QHBoxLayout, QVBoxLayout,
    QWidget
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


class Bridge(QObject):
    code_received = Signal(str)
    project_received = Signal(str, str)

    @Slot(str)
    def receive_code(self, code):
        self.code_received.emit(code)

    @Slot(str, str)
    def receive_project(self, xml, code):
        self.project_received.emit(xml, code)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EV3 Studio")
        self.resize(1280, 800)
        icon_path = BASE_DIR / "assets" / "ev3-studio.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.current_code = ""

        self.bridge = Bridge()
        self.bridge.code_received.connect(self.on_code_received)
        self.bridge.project_received.connect(self.on_project_received)

        self.editor = QWebEngineView()
        channel = QWebChannel(self.editor.page())
        channel.registerObject("bridge", self.bridge)
        self.editor.page().setWebChannel(channel)
        self.editor.setUrl(QUrl.fromLocalFile(str(WEB_DIR / "blockly.html")))

        self.code_view = QPlainTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setPlaceholderText("O código Python gerado aparecerá aqui...")
        self.code_view.setStyleSheet("font-family: monospace; font-size: 13px;")

        self.status = QLabel("Pronto. Conecte o EV3 antes de executar.")
        self.code_title = QLabel("Código Python Pybricks")

        self.open_button = QPushButton("Abrir projeto")
        self.open_button.clicked.connect(self.open_project)
        self.save_button = QPushButton("Salvar projeto")
        self.save_button.clicked.connect(self.save_project)
        self.run_button = QPushButton("▶ Executar no EV3")
        self.run_button.clicked.connect(self.run_on_ev3)
        self.code_button = QPushButton("Código Python (F5)")
        self.code_button.clicked.connect(self.toggle_code_panel)

        # Barra superior: os botões ficam agrupados no canto direito.
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(8, 6, 8, 6)
        top_bar.addStretch()
        top_bar.addWidget(self.open_button)
        top_bar.addWidget(self.save_button)
        top_bar.addWidget(self.code_button)
        top_bar.addWidget(self.run_button)

        self.code_panel = QWidget()
        code_layout = QVBoxLayout(self.code_panel)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.addWidget(self.code_title)
        code_layout.addWidget(self.code_view)
        code_layout.addWidget(self.status)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.code_panel)
        self.splitter.setSizes([1280, 500])
        self.code_panel.hide()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(top_bar)
        layout.addWidget(self.splitter)
        self.setCentralWidget(central)

        # F5 alterna a visualização do código Python.
        self.code_shortcut = QShortcut(QKeySequence(Qt.Key_F5), self)
        self.code_shortcut.activated.connect(self.toggle_code_panel)

    def toggle_code_panel(self):
        visible = not self.code_panel.isVisible()
        self.code_panel.setVisible(visible)
        self.code_button.setText("Ocultar código (F5)" if visible else "Código Python (F5)")
        if visible:
            self.splitter.setSizes([800, 480])
            self.status.setText("Código Python exibido. Pressione F5 novamente para ocultar.")
        else:
            self.status.setText("Código Python oculto. Pressione F5 para exibir.")

    @Slot(str)
    def on_code_received(self, code):
        self.current_code = code
        self.code_view.setPlainText(code)

    @Slot(str, str)
    def on_project_received(self, xml, code):
        self.current_code = code
        self.code_view.setPlainText(code)

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar projeto", "programa.ev3proj", "EV3 Studio (*.ev3proj)"
        )
        if not path:
            return

        def save_when_ready(xml, code):
            try:
                payload = {"version": 1, "xml": xml, "code": code}
                Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
                self.status.setText(f"Projeto salvo: {path}")
            except OSError as exc:
                QMessageBox.critical(self, "Erro ao salvar", str(exc))
            try:
                self.bridge.project_received.disconnect(save_when_ready)
            except (RuntimeError, TypeError):
                pass

        self.bridge.project_received.connect(save_when_ready)
        self.editor.page().runJavaScript("window.sendProjectToApp();")

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir projeto", "", "EV3 Studio (*.ev3proj)"
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            xml = data["xml"]
            self.editor.page().runJavaScript(
                f"window.loadProject({json.dumps(xml)});"
            )
            self.status.setText(f"Projeto aberto: {path}")
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            QMessageBox.critical(self, "Erro ao abrir projeto", str(exc))

    def run_on_ev3(self):
        def run_when_ready(code):
            try:
                self.bridge.code_received.disconnect(run_when_ready)
            except (RuntimeError, TypeError):
                pass
            self._send_code_to_ev3(code)

        self.bridge.code_received.connect(run_when_ready)
        self.editor.page().runJavaScript("window.sendCodeToApp();")

    def _send_code_to_ev3(self, code):
        if not code.strip():
            QMessageBox.warning(self, "Programa vazio", "Adicione blocos antes de executar.")
            return
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", prefix="ev3studio_", delete=False, encoding="utf-8"
            ) as temp:
                temp.write(code)
                temp_path = temp.name

            self.status.setText("Enviando programa para o EV3...")
            result = subprocess.run(
                ["pybricksdev", "run", "ble", temp_path],
                capture_output=True, text=True, check=False
            )
            output = (result.stdout or "") + (result.stderr or "")
            if result.returncode == 0:
                self.status.setText("Programa enviado e iniciado no EV3.")
            else:
                self.status.setText("Falha ao enviar o programa.")
                QMessageBox.warning(self, "Erro do pybricksdev", output[-4000:])
        except FileNotFoundError:
            QMessageBox.critical(
                self, "pybricksdev não encontrado",
                "Instale-o no ambiente virtual com: pip install pybricksdev"
            )
        except OSError as exc:
            QMessageBox.critical(self, "Erro ao executar", str(exc))
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
