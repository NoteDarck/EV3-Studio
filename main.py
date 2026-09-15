import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSpinBox, QDoubleSpinBox, QSplitter, QVBoxLayout, QWidget,
    QComboBox
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

from ev3studio_config import load_config, save_config
from validator import validate_code, validate_project
from tutorials import BEGINNER_TUTORIAL, ABOUT_TUTORIAL

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

class Bridge(QObject):
    code_received = Signal(str)
    project_received = Signal(str, str)
    @Slot(str)
    def receive_code(self, code): self.code_received.emit(code)
    @Slot(str, str)
    def receive_project(self, xml, code): self.project_received.emit(xml, code)

class RobotDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent); self.setWindowTitle("Configuração do robô")
        form = QFormLayout(self); self.left = QComboBox(); self.left.addItems(list("ABCD")); self.left.setCurrentText(config["left_motor"])
        self.right = QComboBox(); self.right.addItems(list("ABCD")); self.right.setCurrentText(config["right_motor"])
        self.wheel = QDoubleSpinBox(); self.wheel.setRange(1,1000); self.wheel.setValue(config["wheel_diameter_mm"]); self.wheel.setSuffix(" mm")
        self.track = QDoubleSpinBox(); self.track.setRange(1,2000); self.track.setValue(config["axle_track_mm"]); self.track.setSuffix(" mm")
        self.connection = QComboBox(); self.connection.addItems(["ble", "usb"]); self.connection.setCurrentText(config["connection"])
        self.name = QLineEdit(config.get("device_name", ""))
        form.addRow("Motor esquerdo", self.left); form.addRow("Motor direito", self.right); form.addRow("Diâmetro da roda", self.wheel); form.addRow("Distância entre rodas", self.track); form.addRow("Conexão", self.connection); form.addRow("Nome do EV3", self.name)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); form.addRow(buttons)
    def values(self): return {"left_motor":self.left.currentText(),"right_motor":self.right.currentText(),"wheel_diameter_mm":self.wheel.value(),"axle_track_mm":self.track.value(),"connection":self.connection.currentText(),"device_name":self.name.text()}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("EV3 Studio"); self.resize(1320, 850); self.config=load_config(); self.current_code=""; self.process=None
        icon=BASE_DIR/"assets"/"ev3-studio.svg"; self.setWindowIcon(QIcon(str(icon))) if icon.exists() else None
        self.bridge=Bridge(); self.bridge.code_received.connect(self.on_code); self.bridge.project_received.connect(self.on_project)
        self.editor=QWebEngineView(); channel=QWebChannel(self.editor.page()); channel.registerObject("bridge",self.bridge); self.editor.page().setWebChannel(channel); self.editor.setUrl(QUrl.fromLocalFile(str(WEB_DIR/"blockly.html")))
        self.code=QPlainTextEdit(); self.code.setReadOnly(True); self.code.setStyleSheet("font-family: monospace; font-size: 13px;")
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(130); self.status=QLabel("Pronto. Configure e conecte o EV3 antes de executar.")
        self.code_panel=QWidget(); cp=QVBoxLayout(self.code_panel); cp.addWidget(QLabel("Código Python Pybricks")); cp.addWidget(self.code); cp.addWidget(QLabel("Console")); cp.addWidget(self.log); cp.addWidget(self.status); self.code_panel.hide()
        self.open_btn=self.button("Abrir projeto",self.open_project); self.save_btn=self.button("Salvar projeto",self.save_project); self.config_btn=self.button("Configurar robô",self.configure_robot); self.devices_btn=self.button("Detectar EV3",self.detect_devices); self.code_btn=self.button("Código Python (F5)",self.toggle_code); self.run_btn=self.button("▶ Executar",self.run_on_ev3); self.stop_btn=self.button("■ Parar",self.stop_program); self.stop_btn.setEnabled(False)
        top=QHBoxLayout(); top.addStretch(); [top.addWidget(x) for x in [self.open_btn,self.save_btn,self.config_btn,self.devices_btn,self.code_btn,self.run_btn,self.stop_btn]]
        self.splitter=QSplitter(Qt.Horizontal); self.splitter.addWidget(self.editor); self.splitter.addWidget(self.code_panel); self.splitter.setSizes([900,500])
        central=QWidget(); layout=QVBoxLayout(central); layout.setContentsMargins(0,0,0,0); layout.addLayout(top); layout.addWidget(self.splitter); self.setCentralWidget(central)
        QShortcut(QKeySequence(Qt.Key_F5),self).activated.connect(self.toggle_code); QShortcut(QKeySequence(Qt.Key_Escape),self).activated.connect(self.stop_program)
        self.process_timer=QTimer(self); self.process_timer.timeout.connect(self.read_process)
        self.create_menu()
    def button(self,text,slot): b=QPushButton(text); b.clicked.connect(slot); return b
    def create_menu(self):
        file=self.menuBar().addMenu("Arquivo"); file.addAction("Novo",self.new_project); file.addAction("Abrir",self.open_project); file.addAction("Salvar",self.save_project); file.addSeparator(); file.addAction("Sair",self.close)
        run=self.menuBar().addMenu("Executar"); run.addAction("Executar no EV3",self.run_on_ev3); run.addAction("Parar",self.stop_program); run.addAction("Detectar EV3",self.detect_devices)
        helpm=self.menuBar().addMenu("Ajuda")
        helpm.addAction("Tutorial para iniciantes", lambda: self.show_tutorial("Tutorial para iniciantes", BEGINNER_TUTORIAL))
        helpm.addAction("Conheça o EV3 Studio", lambda: self.show_tutorial("Conheça o EV3 Studio", ABOUT_TUTORIAL))
        helpm.addSeparator()
        helpm.addAction("Sobre",lambda: QMessageBox.information(self,"Sobre EV3 Studio","EV3 Studio — programação visual Linux para LEGO Mindstorms EV3."))
    def show_tutorial(self, title, html):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(760, 620)
        layout = QVBoxLayout(dialog)
        view = QPlainTextEdit()
        view.setReadOnly(True)
        # QTextBrowser renderiza HTML sem depender de internet.
        from PySide6.QtWidgets import QTextBrowser
        rendered = QTextBrowser()
        rendered.setOpenExternalLinks(True)
        rendered.setHtml(html)
        layout.addWidget(rendered)
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()
    def toggle_code(self): self.code_panel.setVisible(not self.code_panel.isVisible()); self.code_btn.setText("Ocultar código (F5)" if self.code_panel.isVisible() else "Código Python (F5)")
    @Slot(str)
    def on_code(self,code): self.current_code=code; self.code.setPlainText(code)
    @Slot(str,str)
    def on_project(self,xml,code): self.current_code=code; self.code.setPlainText(code)
    def append_log(self,text): self.log.appendPlainText(text.rstrip())
    def new_project(self): self.editor.page().runJavaScript("workspace.clear(); sendCodeToApp();"); self.status.setText("Novo projeto.")
    def configure_robot(self):
        d=RobotDialog(self,self.config)
        if d.exec(): self.config=d.values(); save_config(self.config); self.status.setText("Configuração do robô salva.")
    def detect_devices(self):
        try:
            r=subprocess.run(["pybricksdev","devices"],capture_output=True,text=True,check=False); out=(r.stdout or "")+(r.stderr or ""); self.append_log(out or "Nenhum dispositivo retornado."); self.status.setText("Detecção concluída.")
        except FileNotFoundError: QMessageBox.critical(self,"pybricksdev não encontrado","Instale as dependências com install.sh.")
    def save_project(self):
        path,_=QFileDialog.getSaveFileName(self,"Salvar projeto","programa.ev3proj","EV3 Studio (*.ev3proj)")
        if not path:return
        def save(xml,code):
            errors=validate_project({"xml":xml,"code":code})
            if errors: QMessageBox.warning(self,"Projeto inválido","\n".join(errors)); return
            Path(path).write_text(json.dumps({"version":2,"xml":xml,"code":code,"robot":self.config},indent=2),encoding="utf-8"); self.status.setText(f"Projeto salvo: {path}")
        self.bridge.project_received.connect(save); self.editor.page().runJavaScript("sendProjectToApp();"); QTimer.singleShot(1000,lambda: self._disconnect(save))
    def _disconnect(self,fn):
        try:self.bridge.project_received.disconnect(fn)
        except (RuntimeError,TypeError):pass
    def open_project(self):
        path,_=QFileDialog.getOpenFileName(self,"Abrir projeto","","EV3 Studio (*.ev3proj)")
        if not path:return
        try:
            data=json.loads(Path(path).read_text(encoding="utf-8")); errors=validate_project(data)
            if errors and "xml" not in data: raise ValueError("\n".join(errors))
            self.editor.page().runJavaScript(f"loadProject({json.dumps(data['xml'])});"); self.status.setText(f"Projeto aberto: {path}")
        except (OSError,json.JSONDecodeError,KeyError,ValueError) as e: QMessageBox.critical(self,"Erro ao abrir",str(e))
    def run_on_ev3(self):
        def start(code): self._disconnect(start); self._send(code)
        self.bridge.code_received.connect(start); self.editor.page().runJavaScript("sendCodeToApp();")
    def _send(self,code):
        errors=validate_code(code)
        if errors: QMessageBox.warning(self,"Corrija o programa","\n".join(errors)); return
        try:
            f=tempfile.NamedTemporaryFile(mode="w",suffix=".py",prefix="ev3studio_",delete=False,encoding="utf-8"); f.write(code); f.close(); self.temp_path=f.name
            args=["pybricksdev","run",self.config.get("connection","ble")];
            if self.config.get("device_name"): args += ["--name",self.config["device_name"]]
            args += [self.temp_path]; self.process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True); self.stop_btn.setEnabled(True); self.status.setText("Executando no EV3..."); self.process_timer.start(100)
        except FileNotFoundError: QMessageBox.critical(self,"pybricksdev não encontrado","Execute ./install.sh ou instale pybricksdev.")
    def read_process(self):
        if not self.process:return
        line=self.process.stdout.readline() if self.process.stdout else ""
        if line:self.append_log(line)
        if self.process.poll() is not None:
            self.process_timer.stop(); self.stop_btn.setEnabled(False); self.status.setText("Execução finalizada."); self.process=None; getattr(self,'temp_path',None) and os.unlink(self.temp_path)
    def stop_program(self):
        if self.process and self.process.poll() is None:
            self.process.terminate(); self.append_log("Programa interrompido pelo usuário."); self.status.setText("Programa parado."); self.stop_btn.setEnabled(False)
    def closeEvent(self,event): self.stop_program(); event.accept()

if __name__=="__main__":
    app=QApplication(sys.argv); w=MainWindow(); w.show(); sys.exit(app.exec())
