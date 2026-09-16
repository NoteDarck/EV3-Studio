import json
import os
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSpinBox, QDoubleSpinBox, QSplitter, QVBoxLayout, QWidget,
    QComboBox, QTextBrowser
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

from ev3studio_config import load_config, save_config
from validator import validate_code, validate_project
from tutorials import BEGINNER_TUTORIAL, ABOUT_TUTORIAL
from simulator import EV3Simulator
from update_checker import check_latest, APP_VERSION

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


# ============================================================
# Ponte Qt <-> JS
# ============================================================
class Bridge(QObject):
    code_received = Signal(str)
    project_received = Signal(str, str)

    @Slot(str)
    def receive_code(self, code):
        self.code_received.emit(code)

    @Slot(str, str)
    def receive_project(self, xml, code):
        self.project_received.emit(xml, code)


# ============================================================
# Diálogo de configuração do robô
# ============================================================
class RobotDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("Robô e conexão EV3")
        self.resize(560, 520)
        form = QFormLayout(self)

        self.connection = QComboBox()
        self.connection.addItem("Bluetooth (BLE)", "ble")
        self.connection.addItem("USB", "usb")
        self.connection.setCurrentIndex(max(0, self.connection.findData(config.get("connection", "ble"))))

        self.name = QLineEdit(config.get("device_name", ""))
        self.name.setPlaceholderText("Ex.: EV3 ou nome exibido pelo pybricksdev")
        self.address = QLineEdit(config.get("device_address", ""))
        self.address.setPlaceholderText("Opcional: endereço Bluetooth")
        self.devices = QComboBox()
        self.devices.setPlaceholderText("Clique em Detectar EV3")
        self.devices.currentTextChanged.connect(self._device_selected)
        self.detect = QPushButton("🔎 Detectar EV3")
        self.detect.clicked.connect(self.detect_devices)
        self.connection.currentIndexChanged.connect(self._connection_changed)

        form.addRow("Tipo de conexão", self.connection)
        form.addRow("Nome do EV3", self.name)
        form.addRow("Endereço Bluetooth", self.address)
        form.addRow("Dispositivos", self.devices)
        form.addRow("", self.detect)

        self.left = QComboBox()
        self.left.addItems(list("ABCD"))
        self.left.setCurrentText(config["left_motor"])

        self.right = QComboBox()
        self.right.addItems(list("ABCD"))
        self.right.setCurrentText(config["right_motor"])

        self.wheel = QDoubleSpinBox()
        self.wheel.setRange(1, 1000)
        self.wheel.setValue(config["wheel_diameter_mm"])
        self.wheel.setSuffix(" mm")

        self.track = QDoubleSpinBox()
        self.track.setRange(1, 2000)
        self.track.setValue(config["axle_track_mm"])
        self.track.setSuffix(" mm")

        form.addRow("Motor esquerdo", self.left)
        form.addRow("Motor direito", self.right)
        form.addRow("Diâmetro da roda", self.wheel)
        form.addRow("Distância entre rodas", self.track)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return {
            "left_motor": self.left.currentText(),
            "right_motor": self.right.currentText(),
            "wheel_diameter_mm": self.wheel.value(),
            "axle_track_mm": self.track.value(),
            "connection": self.connection.currentData(),
            "device_name": self.name.text(),
            "device_address": self.address.text(),
        }

    def _connection_changed(self):
        self.address.setEnabled(self.connection.currentData() == "ble")

    def _device_selected(self, text):
        if text and " — " in text:
            self.name.setText(text.split(" — ", 1)[0].strip())
            self.address.setText(text.split(" — ", 1)[1].strip())

    def detect_devices(self):
        self.devices.clear()
        try:
            result = subprocess.run(["pybricksdev", "devices"], capture_output=True, text=True, check=False, timeout=15)
            output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
            found = []
            for line in output.splitlines():
                line = line.strip()
                if not line or "device" in line.lower() and len(line.split()) < 2:
                    continue
                found.append(line)
            if found:
                self.devices.addItems(found)
            else:
                self.devices.addItem("Nenhum dispositivo encontrado")
        except FileNotFoundError:
            self.devices.addItem("pybricksdev não encontrado")
        except subprocess.TimeoutExpired:
            self.devices.addItem("Tempo esgotado na detecção")


# ============================================================
# Janela principal
# ============================================================
class MainWindow(QMainWindow):
    update_result = Signal(object)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EV3 Studio")
        self.resize(1320, 850)

        self.config = load_config()
        self.current_code = ""
        self.process = None
        self.project_path = None

        # Flags anti-duplicação (uma requisição por vez)
        self._code_pending = False
        self._project_pending = False

        icon = BASE_DIR / "assets" / "ev3-studio.svg"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        # ----- Ponte -----
        self.bridge = Bridge()
        self.bridge.code_received.connect(self.on_code)
        self.bridge.project_received.connect(self.on_project)

        # ----- Editor Blockly -----
        self.editor = QWebEngineView()
        channel = QWebChannel(self.editor.page())
        channel.registerObject("bridge", self.bridge)
        self.editor.page().setWebChannel(channel)
        self.editor.setUrl(QUrl.fromLocalFile(str(WEB_DIR / "blockly.html")))
        # Redimensiona o Blockly quando a página terminar de carregar
        self.editor.loadFinished.connect(self._on_editor_loaded)

        # ----- Painel de código/console -----
        self.code = QPlainTextEdit()
        self.code.setReadOnly(True)
        self.code.setStyleSheet("font-family: monospace; font-size: 13px;")

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)

        self.status = QLabel("Pronto. Configure e conecte o EV3 antes de executar.")

        self.code_panel = QWidget()
        cp = QVBoxLayout(self.code_panel)
        cp.addWidget(QLabel("Código Python Pybricks"))
        cp.addWidget(self.code)
        cp.addWidget(QLabel("Console"))
        cp.addWidget(self.log)
        cp.addWidget(self.status)
        self.code_panel.hide()

        # ----- Botões -----
        self.open_btn = self.button("📂 Abrir", self.open_project)
        self.save_btn = self.button("💾 Salvar", self.save_project)
        self.config_btn = self.button("⚙ Robô", self.configure_robot)
        self.devices_btn = self.button("🔌 EV3", self.detect_devices)
        self.code_btn = self.button("🐍 Código (F5)", self.toggle_code)
        self.sim_btn = self.button("🧪 Simular", self.simulate)
        self.run_btn = self.button("▶ Executar", self.run_on_ev3)
        self.stop_btn = self.button("■ Parar", self.stop_program)
        self.stop_btn.setEnabled(False)

        top = QHBoxLayout()
        top.addStretch()
        for x in [self.open_btn, self.save_btn, self.config_btn, self.devices_btn,
                  self.code_btn, self.sim_btn, self.run_btn, self.stop_btn]:
            top.addWidget(x)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.code_panel)
        self.splitter.setSizes([900, 500])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self.splitter)
        self.setCentralWidget(central)

        self.shortcuts = []
        self.add_shortcut("Ctrl+N", self.new_project)
        self.add_shortcut("Ctrl+O", self.open_project)
        self.add_shortcut("Ctrl+S", self.save_project)
        self.add_shortcut("F5", self.toggle_code)
        self.add_shortcut("F6", self.run_on_ev3)
        self.add_shortcut("Shift+F6", self.stop_program)
        self.add_shortcut("F7", self.simulate)
        self.add_shortcut("F8", self.detect_devices)
        self.add_shortcut("F1", lambda: self.show_tutorial("Tutorial para iniciantes", BEGINNER_TUTORIAL))
        self.add_shortcut("Ctrl+R", self.configure_robot)
        self.add_shortcut("Escape", self.stop_program)
        self.add_shortcut("Ctrl+Q", self.close)

        self.process_timer = QTimer(self)
        self.process_timer.timeout.connect(self.read_process)

        self.create_menu()
        self.update_result.connect(self._show_update_result)

    # --------------------------------------------------------
    # Utilidades
    # --------------------------------------------------------
    def button(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def add_shortcut(self, sequence, callback):
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.setContext(Qt.ApplicationShortcut)
        shortcut.activated.connect(callback)
        self.shortcuts.append(shortcut)

    def _on_editor_loaded(self, ok):
        """Quando a página do Blockly terminar de carregar, força resize."""
        if not ok:
            return
        QTimer.singleShot(100, lambda: self.editor.page().runJavaScript(
            "if (window.Blockly && workspace) Blockly.svgResize(workspace);"))

    def create_menu(self):
        file = self.menuBar().addMenu("Arquivo")
        new_action = file.addAction("Novo", self.new_project); new_action.setShortcut(QKeySequence("Ctrl+N"))
        open_action = file.addAction("Abrir", self.open_project); open_action.setShortcut(QKeySequence("Ctrl+O"))
        save_action = file.addAction("Salvar", self.save_project)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        file.addSeparator()
        file.addAction("Sair", self.close)

        run = self.menuBar().addMenu("Executar")
        simulate_action = run.addAction("Simular", self.simulate); simulate_action.setShortcut(QKeySequence("F7"))
        execute_action = run.addAction("Executar no EV3", self.run_on_ev3); execute_action.setShortcut(QKeySequence("F6"))
        stop_action = run.addAction("Parar", self.stop_program); stop_action.setShortcut(QKeySequence("Shift+F6"))
        detect_action = run.addAction("Detectar EV3", self.detect_devices); detect_action.setShortcut(QKeySequence("F8"))

        helpm = self.menuBar().addMenu("Ajuda")
        helpm.addAction("Tutorial para iniciantes",
                        lambda: self.show_tutorial("Tutorial para iniciantes", BEGINNER_TUTORIAL))
        helpm.addAction("Conhecer o EV3 Studio",
                        lambda: self.show_tutorial("Conhecendo o EV3 Studio", ABOUT_TUTORIAL))
        helpm.addSeparator()
        helpm.addAction("Verificar atualizações", self.check_for_updates)
        helpm.addSeparator()
        helpm.addAction("Sobre", lambda: QMessageBox.information(
            self, "Sobre EV3 Studio",
            f"EV3 Studio — programação visual Linux para LEGO Mindstorms EV3.\nVersão {APP_VERSION}"))

    def check_for_updates(self):
        self.status.setText("Verificando atualizações no GitHub...")
        threading.Thread(target=lambda: self.update_result.emit(check_latest()), daemon=True).start()

    def _show_update_result(self, result):
        self.status.setText(result.message)
        if not result.ok:
            QMessageBox.warning(self, "Atualizações", result.message)
            return
        if result.message == "Nova versão disponível.":
            box = QMessageBox(QMessageBox.Information, "Nova versão disponível", f"Instalada: {result.current}\nDisponível: {result.latest}\n\nAbrir a página do Release para baixar?", parent=self)
            download = box.addButton("Abrir download", QMessageBox.AcceptRole)
            box.addButton("Depois", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is download:
                webbrowser.open(result.url)
        else:
            QMessageBox.information(self, "Atualizações", f"Você está usando a versão {result.current}.\nRelease mais recente: {result.latest or 'nenhum'}.")

    def show_tutorial(self, title, html):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(760, 620)
        layout = QVBoxLayout(dialog)
        rendered = QTextBrowser()
        rendered.setOpenExternalLinks(True)
        rendered.setHtml(html)
        layout.addWidget(rendered)
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    # --------------------------------------------------------
    # Requisições one-shot para o Blockly
    # (evita acumular conexões de sinal — bug das janelas em loop)
    # --------------------------------------------------------
    def _request_code_once(self, callback):
        """Pede o código ao Blockly UMA vez e chama callback(code)."""
        if self._code_pending:
            return
        self._code_pending = True

        def handler(code):
            try:
                self.bridge.code_received.disconnect(handler)
            except (RuntimeError, TypeError):
                pass
            self._code_pending = False
            try:
                callback(code)
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

        self.bridge.code_received.connect(handler)
        self.editor.page().runJavaScript("sendCodeToApp && sendCodeToApp();")
        QTimer.singleShot(3000, lambda: self._release_pending("code", handler))

    def _request_project_once(self, callback):
        """Pede o projeto (xml+code) ao Blockly UMA vez."""
        if self._project_pending:
            return
        self._project_pending = True

        def handler(xml, code):
            try:
                self.bridge.project_received.disconnect(handler)
            except (RuntimeError, TypeError):
                pass
            self._project_pending = False
            try:
                callback(xml, code)
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

        self.bridge.project_received.connect(handler)
        self.editor.page().runJavaScript("sendProjectToApp && sendProjectToApp();")
        QTimer.singleShot(3000, lambda: self._release_pending("project", handler))

    def _release_pending(self, kind, handler):
        if kind == "code" and self._code_pending:
            try:
                self.bridge.code_received.disconnect(handler)
            except (RuntimeError, TypeError):
                pass
            self._code_pending = False
        if kind == "project" and self._project_pending:
            try:
                self.bridge.project_received.disconnect(handler)
            except (RuntimeError, TypeError):
                pass
            self._project_pending = False

    # --------------------------------------------------------
    # UI principal
    # --------------------------------------------------------
    def toggle_code(self):
        self.code_panel.setVisible(not self.code_panel.isVisible())
        self.code_btn.setText("Ocultar código (F5)" if self.code_panel.isVisible()
                              else "Código Python (F5)")
        # Força o Blockly a recalcular o layout
        QTimer.singleShot(60, lambda: self.editor.page().runJavaScript(
            "if (window.Blockly && workspace) Blockly.svgResize(workspace);"))

    def simulate(self):
        def open_sim(code):
            dialog = EV3Simulator(self)
            dialog.set_code(code)
            dialog.set_robot_config(self.config)
            dialog.exec()
        self._request_code_once(open_sim)

    @Slot(str)
    def on_code(self, code):
        self.current_code = code
        self.code.setPlainText(code)

    @Slot(str, str)
    def on_project(self, xml, code):
        self.current_code = code
        self.code.setPlainText(code)

    def append_log(self, text):
        self.log.appendPlainText(text.rstrip())

    def new_project(self):
        self.project_path = None
        self.editor.page().runJavaScript(
            "workspace.clear(); sendCodeToApp && sendCodeToApp();")
        self.status.setText("Novo projeto.")

    def configure_robot(self):
        d = RobotDialog(self, self.config)
        if d.exec():
            self.config = d.values()
            save_config(self.config)
            self.status.setText("Configuração do robô salva.")

    def detect_devices(self):
        try:
            r = subprocess.run(["pybricksdev", "devices"],
                               capture_output=True, text=True, check=False)
            out = (r.stdout or "") + (r.stderr or "")
            self.append_log(out or "Nenhum dispositivo retornado.")
            self.status.setText("Detecção concluída.")
        except FileNotFoundError:
            QMessageBox.critical(self, "pybricksdev não encontrado",
                                 "Instale as dependências com install.sh.")

    # --------------------------------------------------------
    # Projeto: salvar / abrir
    # --------------------------------------------------------
    def save_project(self):
        path = self.project_path
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Salvar projeto", "programa.ev3proj", "EV3 Studio (*.ev3proj)")
        if not path:
            return

        def save(xml, code):
            errors = validate_project({"xml": xml, "code": code})
            if errors:
                QMessageBox.warning(self, "Projeto inválido", "\n".join(errors))
                return
            Path(path).write_text(json.dumps(
                {"version": 2, "xml": xml, "code": code, "robot": self.config},
                indent=2), encoding="utf-8")
            self.project_path = path
            self.status.setText(f"Projeto salvo: {path}")

        self._request_project_once(save)

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir projeto", "", "EV3 Studio (*.ev3proj)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.project_path = path
            errors = validate_project(data)
            if errors and "xml" not in data:
                raise ValueError("\n".join(errors))
            # Usa json.dumps para escapar com segurança
            xml_js = json.dumps(data["xml"])
            self.editor.page().runJavaScript(f"loadProject({xml_js});")
            self.status.setText(f"Projeto aberto: {path}")
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            QMessageBox.critical(self, "Erro ao abrir", str(e))

    # --------------------------------------------------------
    # Execução no EV3
    # --------------------------------------------------------
    def run_on_ev3(self):
        self._request_code_once(self._send)

    def _send(self, code):
        errors = validate_code(code)
        if errors:
            QMessageBox.warning(self, "Corrija o programa", "\n".join(errors))
            return
        try:
            f = tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", prefix="ev3studio_",
                delete=False, encoding="utf-8")
            f.write(code)
            f.close()
            self.temp_path = f.name

            args = ["pybricksdev", "run", self.config.get("connection", "ble")]
            if self.config.get("device_name"):
                args += ["--name", self.config["device_name"]]
            args += [self.temp_path]

            self.process = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.stop_btn.setEnabled(True)
            self.status.setText("Executando no EV3...")
            self.process_timer.start(100)
        except FileNotFoundError:
            QMessageBox.critical(self, "pybricksdev não encontrado",
                                 "Execute ./install.sh ou instale pybricksdev.")

    def read_process(self):
        proc = self.process
        if not proc:
            self.process_timer.stop()
            return
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            self.append_log(line)
        if proc.poll() is not None:
            self.process_timer.stop()
            self.stop_btn.setEnabled(False)
            self.status.setText("Execução finalizada.")
            self.process = None
            temp = getattr(self, "temp_path", None)
            if temp and os.path.exists(temp):
                try:
                    os.unlink(temp)
                except OSError:
                    pass

    def stop_program(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.append_log("Programa interrompido pelo usuário.")
            self.status.setText("Programa parado.")
            self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        self.stop_program()
        event.accept()


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
