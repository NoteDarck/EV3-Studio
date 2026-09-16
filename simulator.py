import math
import os
import re
import tempfile
import time
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QLabel, QPlainTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout
)

try:
    import pybullet as p
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constantes físicas / geométricas
# ---------------------------------------------------------------------------
SIM_HZ = 120
SIM_DT = 1.0 / SIM_HZ
MAX_STEPS_PER_FRAME = 10

WHEEL_RADIUS = 0.16
WHEEL_WIDTH = 0.10
WHEEL_X = 0.28
WHEEL_Y = 0.34
CHASSIS_HALF = (0.42, 0.30, 0.10)
CHASSIS_Z = 0.18

# Nome das juntas no URDF
LEFT_JOINTS = ["wheel_fl", "wheel_bl"]
RIGHT_JOINTS = ["wheel_fr", "wheel_br"]

MAX_MOTOR_FORCE = 3.0

# Mapeamento EV3: A e B = esquerda, C e D = direita.
# (assim qualquer bloco com A, B, C ou D mexe o robô)
MOTOR_TO_JOINTS = {
    "a": LEFT_JOINTS,
    "b": LEFT_JOINTS,
    "c": RIGHT_JOINTS,
    "d": RIGHT_JOINTS,
}


def _build_urdf() -> str:
    """URDF de um robô diferencial com 4 rodas (estilo EV3)."""
    cx, cy, cz = CHASSIS_HALF
    wheel_rpy = "1.5707963 0 0"

    def joint_origin(x, y):
        return f"{x} {y} {-cz}"

    parts = []
    parts.append(f"""<?xml version="1.0"?>
<robot name="ev3_bot">
  <link name="base_link">
    <inertial>
      <mass value="1.0"/>
      <inertia ixx="0.012" ixy="0" ixz="0" iyy="0.019" iyz="0" izz="0.028"/>
    </inertial>
    <visual>
      <geometry><box size="{2*cx} {2*cy} {2*cz}"/></geometry>
      <material name="orange"><color rgba="1.0 0.4 0.1 1.0"/></material>
      <origin xyz="0 0 0" rpy="0 0 0"/>
    </visual>
    <collision>
      <geometry><box size="{2*cx} {2*cy} {2*cz}"/></geometry>
      <origin xyz="0 0 0" rpy="0 0 0"/>
    </collision>
  </link>
""")

    wheels = [
        ("wheel_fl", -WHEEL_X, +WHEEL_Y, "left"),
        ("wheel_bl", -WHEEL_X, -WHEEL_Y, "left"),
        ("wheel_fr", +WHEEL_X, +WHEEL_Y, "right"),
        ("wheel_br", +WHEEL_X, -WHEEL_Y, "right"),
    ]

    for name, x, y, side in wheels:
        m = 0.18
        r = WHEEL_RADIUS
        h = WHEEL_WIDTH
        ixx = (1.0 / 12.0) * m * (3 * r * r + h * h)
        izz = 0.5 * m * r * r
        parts.append(f"""  <link name="{name}">
    <inertial>
      <mass value="{m}"/>
      <inertia ixx="{ixx:.6f}" ixy="0" ixz="0"
               iyy="{ixx:.6f}" iyz="0" izz="{izz:.6f}"/>
    </inertial>
    <visual>
      <geometry><cylinder radius="{r}" length="{h}"/></geometry>
      <material name="dark"><color rgba="0.15 0.15 0.18 1.0"/></material>
      <origin xyz="0 0 0" rpy="{wheel_rpy}"/>
    </visual>
    <collision>
      <geometry><cylinder radius="{r}" length="{h}"/></geometry>
      <origin xyz="0 0 0" rpy="{wheel_rpy}"/>
    </collision>
  </link>
  <joint name="{name}_joint" type="continuous">
    <parent link="base_link"/>
    <child link="{name}"/>
    <origin xyz="{joint_origin(x, y)}" rpy="0 0 0"/>
    <axis xyz="0 1 0"/>
    <limit effort="{MAX_MOTOR_FORCE}" velocity="50.0"/>
  </joint>
""")

    parts.append("</robot>\n")
    return "".join(parts)


class EV3Simulator(QDialog):
    """Simulador físico visual: PyBullet em DIRECT, frame exibido no Qt."""

    # Linhas de Pybricks que NÃO geram comando (import, declaração, etc.)
    _BOILERPLATE = re.compile(
        r"^\s*(from\s+\S+\s+import\s+|import\s+|"
        r"ev3\s*=\s*EV3Brick\(|"
        r"motor_[a-d]\s*=\s*Motor\(|"
        r"motors\s*=|"
        r"ev3\.(screen|speaker|light|battery|buttons)\b|"
        r"print\(|#)",
        re.I)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Simulador EV3 — PyBullet")
        self.resize(980, 720)

        # ---- UI -----------------------------------------------------------
        self.frame = QLabel("Simulador EV3")
        self.frame.setAlignment(Qt.AlignCenter)
        self.frame.setMinimumSize(800, 480)
        self.frame.setStyleSheet("background:#18232b;color:#b9f5df;font-size:20px")

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)

        self.status = QLabel("Pronto")

        self.run_button = QPushButton("▶ Simular")
        self.run_button.clicked.connect(self.start)
        self.reset_button = QPushButton("↺ Reiniciar")
        self.reset_button.clicked.connect(self.reset_world)
        self.close_button = QPushButton("Fechar")
        self.close_button.clicked.connect(self.close)

        buttons = QHBoxLayout()
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.close_button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.frame, 1)
        layout.addWidget(self.log)
        layout.addWidget(self.status)
        layout.addLayout(buttons)

        # ---- Estado -------------------------------------------------------
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step)

        self.client = None
        self.robot = None
        self.joint_index = {}

        self.commands = []
        self.cmd_index = 0
        self.cmd_state = {}

        self.motor_speed = {"left": 0.0, "right": 0.0}

        self.sim_time = 0.0
        self.last_real_time = None
        self.accumulator = 0.0

        self.current_code = ""
        self._urdf_path = None

        if not PYBULLET_AVAILABLE:
            self.frame.setText(
                "PyBullet não está instalado.\nExecute: pip install pybullet")
            self.run_button.setEnabled(False)
            self.reset_button.setEnabled(False)
        else:
            self.reset_world()

    # ------------------------------------------------------------------
    def set_code(self, code: str):
        self.current_code = code or ""

    # ------------------------------------------------------------------
    def _load_robot(self):
        urdf = _build_urdf()
        fd, path = tempfile.mkstemp(suffix=".urdf", prefix="ev3_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(urdf)
        self._urdf_path = path

        self.robot = p.loadURDF(
            path,
            basePosition=[0, 0, CHASSIS_Z],
            useFixedBase=False,
            flags=p.URDF_USE_INERTIA_FROM_FILE,
            physicsClientId=self.client)

        self.joint_index = {}
        for j in range(p.getNumJoints(self.robot, physicsClientId=self.client)):
            info = p.getJointInfo(self.robot, j, physicsClientId=self.client)
            name = info[1].decode("utf-8")
            self.joint_index[name] = j
            p.setJointMotorControl2(
                self.robot, j, p.VELOCITY_CONTROL,
                targetVelocity=0, force=0,
                physicsClientId=self.client)

    def reset_world(self):
        if not PYBULLET_AVAILABLE:
            return

        if self.client is not None:
            try:
                p.disconnect(self.client)
            except Exception:
                pass
            self.client = None

        if self._urdf_path and os.path.exists(self._urdf_path):
            try:
                os.unlink(self._urdf_path)
            except OSError:
                pass
            self._urdf_path = None

        self.client = p.connect(p.DIRECT)
        p.setGravity(0, 0, -9.81, physicsClientId=self.client)
        p.setTimeStep(SIM_DT, physicsClientId=self.client)
        p.setPhysicsEngineParameter(
            numSolverIterations=50,
            enableConeFriction=1,
            physicsClientId=self.client)

        # Chão
        col = p.createCollisionShape(
            p.GEOM_BOX, halfExtents=(3.5, 3.5, 0.03),
            physicsClientId=self.client)
        vis = p.createVisualShape(
            p.GEOM_BOX, halfExtents=(3.5, 3.5, 0.03),
            rgbaColor=(0.25, 0.30, 0.32, 1),
            physicsClientId=self.client)
        p.createMultiBody(0, col, vis, [0, 0, -0.03],
                          physicsClientId=self.client)

        # Marcadores (dão noção de movimento)
        for i, (x, y) in enumerate([(1, 1), (-1, 1), (1, -1), (-1, -1)]):
            c = p.createCollisionShape(
                p.GEOM_BOX, halfExtents=(0.04, 0.04, 0.2),
                physicsClientId=self.client)
            v = p.createVisualShape(
                p.GEOM_BOX, halfExtents=(0.04, 0.04, 0.2),
                rgbaColor=(0.9, 0.75, 0.15, 1) if i == 0
                         else (0.5, 0.5, 0.5, 1),
                physicsClientId=self.client)
            p.createMultiBody(0, c, v, [x, y, 0.2],
                              physicsClientId=self.client)

        self._load_robot()

        self.commands = []
        self.cmd_index = 0
        self.cmd_state = {}
        self.motor_speed = {"left": 0.0, "right": 0.0}
        self.sim_time = 0.0
        self.last_real_time = None
        self.accumulator = 0.0

        self.render()
        self.status.setText("Mundo físico pronto — chassi + 4 rodas + chão")

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------
    def parse(self):
        commands = []
        errors = []
        alias = {}

        for lineno, raw in enumerate(self.current_code.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # 1) Definição de motor:  <nome> = Motor(Port.X)
            m = re.match(
                r"(\w+)\s*=\s*Motor\(\s*Port\.([A-D])\s*\)", line, re.I)
            if m:
                alias[m.group(1)] = m.group(2).lower()
                continue

            # 2) Comandos de motor: <var>.<método>(...)
            m = re.match(
                r"(\w+)\.(run_time|run_angle|run|stop)\s*\((.*)\)\s*$",
                line, re.I)
            if m:
                var = m.group(1)
                method = m.group(2).lower()
                args = [a.strip() for a in m.group(3).split(",") if a.strip()]

                port = alias.get(var)
                if port is None:
                    mm = re.match(r"motor_([a-d])$", var, re.I)
                    if mm:
                        port = mm.group(1).lower()
                if port is None:
                    errors.append(
                        f"linha {lineno}: '{var}' não é um motor conhecido")
                    continue

                if method == "run_time":
                    if len(args) < 2:
                        errors.append(
                            f"linha {lineno}: run_time precisa de (velocidade, ms)")
                        continue
                    try:
                        speed = float(args[0])
                        dur = float(args[1])
                    except ValueError:
                        errors.append(f"linha {lineno}: argumentos inválidos")
                        continue
                    dur_s = dur / 1000.0 if dur > 50 else dur
                    commands.append({"type": "run_time", "motor": port,
                                     "speed": speed, "duration": dur_s})
                    continue

                if method == "run_angle":
                    if len(args) < 2:
                        errors.append(
                            f"linha {lineno}: run_angle precisa de (velocidade, graus)")
                        continue
                    try:
                        speed = float(args[0])
                        angle = float(args[1])
                    except ValueError:
                        errors.append(f"linha {lineno}: argumentos inválidos")
                        continue
                    commands.append({"type": "run_angle", "motor": port,
                                     "speed": speed, "angle": angle})
                    continue

                if method == "run":
                    if len(args) < 1:
                        errors.append(f"linha {lineno}: run precisa de velocidade")
                        continue
                    try:
                        speed = float(args[0])
                    except ValueError:
                        errors.append(f"linha {lineno}: velocidade inválida")
                        continue
                    commands.append({"type": "run", "motor": port,
                                     "speed": speed})
                    continue

                if method == "stop":
                    commands.append({"type": "stop", "motor": port})
                    continue

            # 3) wait(ms)
            m = re.search(r"\bwait\(\s*(\d+(?:\.\d+)?)\s*\)", line)
            if m:
                v = float(m.group(1))
                dur_s = v / 1000.0 if v > 50 else v
                commands.append({"type": "wait", "duration": dur_s})
                continue

            # 4) Boilerplate do Pybricks -> ignora sem reclamar
            if self._BOILERPLATE.match(line):
                continue

            # 5) Qualquer outra coisa: reporta
            errors.append(f"linha {lineno}: não reconhecido → {line}")

        return commands, errors

    # ------------------------------------------------------------------
    def start(self):
        if not PYBULLET_AVAILABLE:
            return
        self.reset_world()

        self.commands, errors = self.parse()
        self.cmd_index = 0
        self.cmd_state = {}

        self.log.clear()
        self.log.appendPlainText(
            f"PyBullet: {len(self.commands)} comando(s) parseado(s).")
        for e in errors:
            self.log.appendPlainText(f"⚠ {e}")
        if not self.commands:
            self.log.appendPlainText(
                "Use blocos de motor (run, run_time, run_angle) ou wait().")

        self.last_real_time = time.perf_counter()
        self.timer.start(16)
        self.status.setText("Simulando física em tempo real...")

    # ------------------------------------------------------------------
    def _start_command(self, cmd):
        t = cmd["type"]

        if t == "run":
            self._set_motor_speed(cmd["motor"], cmd["speed"])
            self.cmd_state = {"finished": True}
            self.log.appendPlainText(
                f"Motor {cmd['motor'].upper()}: contínuo {cmd['speed']:.0f}°/s")

        elif t == "run_time":
            self._set_motor_speed(cmd["motor"], cmd["speed"])
            self.cmd_state = {
                "finished": False,
                "end_time": self.sim_time + max(0.0, cmd["duration"]),
            }
            self.log.appendPlainText(
                f"Motor {cmd['motor'].upper()}: {cmd['speed']:.0f}°/s "
                f"por {cmd['duration']:.2f}s")

        elif t == "run_angle":
            motor = cmd["motor"]
            speed = cmd["speed"]
            angle = cmd["angle"]
            self._set_motor_speed(motor, speed)
            start_positions = {}
            for jname in MOTOR_TO_JOINTS.get(motor, []):
                jidx = self.joint_index.get(jname)
                if jidx is None:
                    continue
                state = p.getJointState(
                    self.robot, jidx, physicsClientId=self.client)
                start_positions[jname] = state[0]
            self.cmd_state = {
                "finished": False,
                "target_rad": math.radians(angle),
                "start_pos": start_positions,
                "angle_deg": angle,
            }
            self.log.appendPlainText(
                f"Motor {motor.upper()}: {speed:.0f}°/s até girar {angle:.0f}°")

        elif t == "wait":
            self._set_all_speeds(0.0)
            self.cmd_state = {
                "finished": False,
                "end_time": self.sim_time + max(0.0, cmd["duration"]),
            }
            self.log.appendPlainText(f"Espera: {cmd['duration']:.2f}s")

        elif t == "stop":
            self._set_motor_speed(cmd["motor"], 0.0)
            self.cmd_state = {"finished": True}
            self.log.appendPlainText(f"Motor {cmd['motor'].upper()}: parar")

    def _update_command(self):
        if self.cmd_index >= len(self.commands):
            return True

        cmd = self.commands[self.cmd_index]

        if cmd["type"] == "run_angle":
            target = self.cmd_state["target_rad"]
            start = self.cmd_state["start_pos"]
            for jname, pos0 in start.items():
                jidx = self.joint_index[jname]
                state = p.getJointState(
                    self.robot, jidx, physicsClientId=self.client)
                delta = state[0] - pos0
                if abs(delta) >= abs(target):
                    self._set_motor_speed(cmd["motor"], 0.0)
                    self.log.appendPlainText(
                        f"Motor {cmd['motor'].upper()}: alvo de "
                        f"{self.cmd_state['angle_deg']:.0f}° atingido")
                    return True
            return False

        if self.cmd_state.get("finished"):
            return True

        if "end_time" in self.cmd_state:
            if self.sim_time >= self.cmd_state["end_time"]:
                if cmd["type"] == "run_time":
                    self._set_motor_speed(cmd["motor"], 0.0)
                return True
            return False

        return True

    # ------------------------------------------------------------------
    def _set_motor_speed(self, motor, speed_deg_s):
        for side in ("left", "right"):
            if motor in ("a", "b") and side == "left":
                self.motor_speed[side] = speed_deg_s
            elif motor in ("c", "d") and side == "right":
                self.motor_speed[side] = speed_deg_s

    def _set_all_speeds(self, speed_deg_s):
        self.motor_speed["left"] = speed_deg_s
        self.motor_speed["right"] = speed_deg_s

    def _apply_motor_speeds(self):
        for side, jnames in (("left", LEFT_JOINTS), ("right", RIGHT_JOINTS)):
            target = math.radians(self.motor_speed.get(side, 0.0))
            for jname in jnames:
                jidx = self.joint_index.get(jname)
                if jidx is None:
                    continue
                p.setJointMotorControl2(
                    self.robot, jidx,
                    controlMode=p.VELOCITY_CONTROL,
                    targetVelocity=target,
                    force=MAX_MOTOR_FORCE,
                    physicsClientId=self.client)

    # ------------------------------------------------------------------
    def step(self):
        if not self.client:
            return

        now = time.perf_counter()
        if self.last_real_time is None:
            self.last_real_time = now
        real_dt = now - self.last_real_time
        self.last_real_time = now
        real_dt = min(real_dt, MAX_STEPS_PER_FRAME * SIM_DT)
        self.accumulator += real_dt

        if self.cmd_index < len(self.commands):
            if not self.cmd_state:
                self._start_command(self.commands[self.cmd_index])
            if self._update_command():
                self.cmd_index += 1
                self.cmd_state = {}
        else:
            self._set_all_speeds(0.0)

        while self.accumulator >= SIM_DT:
            self._apply_motor_speeds()
            p.stepSimulation(physicsClientId=self.client)
            self.sim_time += SIM_DT
            self.accumulator -= SIM_DT

        if self.sim_time > 30.0:
            self.timer.stop()
            self.status.setText("Simulação encerrada (limite de 30s)")
        elif self.cmd_index >= len(self.commands) and self.sim_time > 0.5:
            if all(abs(v) < 1e-3 for v in self.motor_speed.values()):
                self.timer.stop()
                self.status.setText("Simulação concluída")

        self.render()

    # ------------------------------------------------------------------
    def render(self):
        if not self.client:
            return

        pos, _ = p.getBasePositionAndOrientation(
            self.robot, physicsClientId=self.client)

        w = min(max(640, self.frame.width()), 1280)
        h = min(max(360, self.frame.height()), 720)

        view = p.computeViewMatrixFromYawPitchRoll(
            cameraTargetPosition=[pos[0], pos[1], 0.15],
            distance=4.8, yaw=45, pitch=-40, roll=0, upAxisIndex=2,
            physicsClientId=self.client)
        projection = p.computeProjectionMatrixFOV(
            fov=58, aspect=w / h, nearVal=0.1, farVal=30,
            physicsClientId=self.client)

        try:
            img = p.getCameraImage(
                w, h, view, projection,
                renderer=p.ER_BULLET_HARDWARE_OPENGL,
                physicsClientId=self.client)
        except Exception:
            img = p.getCameraImage(
                w, h, view, projection,
                renderer=p.ER_TINY_RENDERER,
                physicsClientId=self.client)

        rgba = img[2]
        if not isinstance(rgba, (bytes, bytearray)):
            rgba = bytes(rgba)

        image = QImage(rgba, w, h, QImage.Format_RGBA8888).copy()
        self.frame.setPixmap(QPixmap.fromImage(image).scaled(
            self.frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self.timer.stop()
        if self.client is not None:
            try:
                p.disconnect(self.client)
            except Exception:
                pass
            self.client = None
        if self._urdf_path and os.path.exists(self._urdf_path):
            try:
                os.unlink(self._urdf_path)
            except OSError:
                pass
        event.accept()