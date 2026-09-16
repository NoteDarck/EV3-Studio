import math
import re
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox

try:
    import pybullet as p
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False

class EV3Simulator(QDialog):
    """Simulador PyBullet leve: chassi físico, rodas visuais e câmera renderizada no Qt."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Simulador EV3 — PyBullet")
        self.resize(900, 650)
        self.frame = QLabel("Simulador EV3")
        self.frame.setAlignment(Qt.AlignCenter)
        self.frame.setMinimumSize(640, 360)
        self.frame.setStyleSheet("background:#18232b;color:#b9f5df;font-size:20px")
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(105)
        self.status = QLabel("Pronto")
        self.run_button = QPushButton("▶ Simular"); self.run_button.clicked.connect(self.start)
        self.reset_button = QPushButton("↺ Reiniciar"); self.reset_button.clicked.connect(self.reset_world)
        self.close_button = QPushButton("Fechar"); self.close_button.clicked.connect(self.close)
        buttons = QHBoxLayout(); buttons.addWidget(self.run_button); buttons.addWidget(self.reset_button); buttons.addWidget(self.close_button); buttons.addStretch()
        layout = QVBoxLayout(self); layout.addWidget(self.frame, 1); layout.addWidget(self.log); layout.addWidget(self.status); layout.addLayout(buttons)
        self.timer = QTimer(self); self.timer.timeout.connect(self.step)
        self.client = None; self.robot = None; self.wheels = []; self.wheel_offsets = []
        self.steps = []; self.step_index = 0; self.current_code = ""; self.motor_command = None; self.sim_time = 0.0
        self.left_port = "B"; self.right_port = "C"; self.wheel_diameter = 56.0; self.track = 120.0
        self.pose = [0.0, 0.0, 0.0]
        if not PYBULLET_AVAILABLE:
            self.frame.setText("PyBullet não está instalado.\nExecute ./install.sh")
            self.status.setText("Dependência ausente — instale PyBullet para simular")
        else:
            self.reset_world()

    def set_code(self, code): self.current_code = code

    def set_robot_config(self, config):
        self.left_port = str(config.get("left_motor", "B")).upper()
        self.right_port = str(config.get("right_motor", "C")).upper()
        self.wheel_diameter = float(config.get("wheel_diameter_mm", 56.0))
        self.track = float(config.get("axle_track_mm", 120.0))

    def box(self, half, pos, color, mass=0):
        c = p.createCollisionShape(p.GEOM_BOX, halfExtents=half, physicsClientId=self.client)
        v = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=color, physicsClientId=self.client)
        return p.createMultiBody(mass, c, v, pos, physicsClientId=self.client)

    def cylinder(self, radius, length, pos, color):
        v = p.createVisualShape(p.GEOM_CYLINDER, radius=radius, length=length, rgbaColor=color, physicsClientId=self.client)
        # Sem collision/massa: a roda é uma peça visual estável acompanhando o chassi.
        return p.createMultiBody(0, -1, v, pos, physicsClientId=self.client)

    def reset_world(self):
        if not PYBULLET_AVAILABLE: return
        if self.client is not None:
            try: p.disconnect(self.client)
            except Exception: pass
        self.client = p.connect(p.DIRECT)
        p.setGravity(0, 0, -9.81, physicsClientId=self.client)
        p.setTimeStep(1/120, physicsClientId=self.client)
        p.setPhysicsEngineParameter(numSolverIterations=20, physicsClientId=self.client)
        self.box((3.5, 3.5, .03), (0, 0, -.03), (.22, .28, .32, 1))
        self.robot = self.box((.42, .30, .10), (0, 0, .18), (.0, .66, .42, 1), 1.0)
        p.changeDynamics(self.robot, -1, lateralFriction=1.0, rollingFriction=.01, spinningFriction=.01, physicsClientId=self.client)
        self.wheels = []; self.wheel_offsets = []
        for x in (-.28, .28):
            for y in (-.34, .34):
                self.wheels.append(self.cylinder(.16, .10, (x, y, .16), (.03, .03, .04, 1)))
                self.wheel_offsets.append((x, y, -.02))
        self.steps = []; self.step_index = 0; self.sim_time = 0.0; self.motor_command = None
        self.pose = [0.0, 0.0, 0.0]
        self.render(); self.status.setText("Mundo físico pronto")

    def parse(self):
        steps = []
        for line in self.current_code.splitlines():
            line = line.strip()
            m = re.search(r"motor_([a-d]).run_time\(\s*(-?[0-9.]+),\s*([0-9.]+)\s*\)", line, re.I)
            if m: steps.append(("run", m.group(1).upper(), float(m.group(2)), float(m.group(3)) / 1000)); continue
            m = re.search(r"motor_([a-d]).run\(\s*(-?[0-9.]+)\s*\)", line, re.I)
            if m: steps.append(("run_forever", m.group(1).upper(), float(m.group(2)))); continue
            m = re.search(r"motor_([a-d]).run_angle\(\s*(-?[0-9.]+),\s*(-?[0-9.]+)\s*\)", line, re.I)
            if m: steps.append(("angle", m.group(1).upper(), float(m.group(2)), float(m.group(3)))); continue
            m = re.search(r"wait\(([0-9.]+)\)", line)
            if m: steps.append(("wait", float(m.group(1)) / 1000)); continue
        return steps

    def start(self):
        if not PYBULLET_AVAILABLE:
            QMessageBox.warning(self, "PyBullet não instalado", "Execute ./install.sh ou instale PyBullet no ambiente virtual do EV3 Studio.")
            return
        self.reset_world(); self.steps = self.parse(); self.log.clear(); self.step_index = 0
        self.log.appendPlainText(f"PyBullet: {len(self.steps)} ação(ões) encontrada(s).")
        if not self.steps: self.log.appendPlainText("Use um bloco de motor por tempo, ângulo ou contínuo.")
        self.timer.start(33); self.status.setText("Simulando em tempo real...")

    def step(self):
        if self.client is None: return
        dt = 1 / 30; self.sim_time += dt
        if self.motor_command and self.sim_time >= self.motor_command[1]: self.motor_command = None
        if self.step_index < len(self.steps) and self.motor_command is None:
            action = self.steps[self.step_index]; self.step_index += 1
            if action[0] == "run": self.motor_command = ({action[1]: action[2]}, self.sim_time + action[3]); self.log.appendPlainText(f"Motor {action[1]}: {action[2]:.0f} graus/s por {action[3]:.2f}s")
            elif action[0] == "run_forever": self.motor_command = ({action[1]: action[2]}, 999999); self.log.appendPlainText(f"Motor {action[1]} contínuo: {action[2]:.0f} graus/s")
            elif action[0] == "angle": self.motor_command = ({action[1]: action[2]}, self.sim_time + max(.15, abs(action[3]) / max(1, abs(action[2])))); self.log.appendPlainText(f"Motor {action[1]}: {action[3]:.0f} graus")
            elif action[0] == "wait": self.motor_command = ({}, self.sim_time + action[1]); self.log.appendPlainText(f"Espera: {action[1]:.2f}s")
        commands = self.motor_command[0] if self.motor_command else {}
        left_speed = commands.get(self.left_port, commands.get("A", 0))
        right_speed = commands.get(self.right_port, 0)
        if commands and right_speed == 0 and left_speed != 0: right_speed = left_speed
        radius = max(.001, self.wheel_diameter / 2000.0)
        left_linear = left_speed * radius
        right_linear = right_speed * radius
        linear = max(-1.2, min(1.2, (left_linear + right_linear) / 2.0))
        angular = (right_linear - left_linear) / max(.001, self.track / 1000.0)
        self.pose[2] += angular * dt
        self.pose[0] += linear * math.cos(self.pose[2]) * dt
        self.pose[1] += linear * math.sin(self.pose[2]) * dt
        pos, orn = p.getBasePositionAndOrientation(self.robot, physicsClientId=self.client)
        target_orn = p.getQuaternionFromEuler([0, 0, self.pose[2]])
        p.resetBasePositionAndOrientation(self.robot, [self.pose[0], self.pose[1], pos[2]], target_orn, physicsClientId=self.client)
        p.resetBaseVelocity(self.robot, [0, 0, 0], [0, 0, 0], physicsClientId=self.client)
        p.stepSimulation(physicsClientId=self.client)
        if self.sim_time > 12 or (self.step_index >= len(self.steps) and self.motor_command is None):
            self.timer.stop(); p.resetBaseVelocity(self.robot, [0, 0, 0], [0, 0, 0], physicsClientId=self.client); self.status.setText("Simulação concluída")
        self.render()

    def render(self):
        if self.client is None: return
        pos, orn = p.getBasePositionAndOrientation(self.robot, physicsClientId=self.client)
        for wheel, offset in zip(self.wheels, self.wheel_offsets):
            wheel_pos, wheel_orn = p.multiplyTransforms(pos, orn, offset, [0, 0, 0, 1], physicsClientId=self.client)
            wheel_orn = p.multiplyTransforms([0, 0, 0], wheel_orn, [0, 0, 0], p.getQuaternionFromEuler([math.pi / 2, 0, 0]), physicsClientId=self.client)[1]
            p.resetBasePositionAndOrientation(wheel, wheel_pos, wheel_orn, physicsClientId=self.client)
        view = p.computeViewMatrixFromYawPitchRoll([pos[0], pos[1], .1], 4.5, 45, -58, 0, physicsClientId=self.client)
        projection = p.computeProjectionMatrixFOV(58, max(1, self.frame.width() / max(1, self.frame.height())), .1, 20, physicsClientId=self.client)
        width, height, rgba, _, _ = p.getCameraImage(640, 400, view, projection, renderer=p.ER_TINY_RENDERER, physicsClientId=self.client)
        image = QImage(bytes(rgba), width, height, QImage.Format_RGBA8888).copy()
        self.frame.setPixmap(QPixmap.fromImage(image).scaled(self.frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def closeEvent(self, event):
        self.timer.stop()
        if self.client is not None:
            try: p.disconnect(self.client)
            except Exception: pass
        event.accept()
