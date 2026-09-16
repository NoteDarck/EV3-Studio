import re

MOTOR_PORTS = set("ABCD")
SENSOR_PORTS = {"S1", "S2", "S3", "S4"}

def validate_code(code):
    errors = []
    if not code.strip() or code.strip().startswith("# Adicione blocos"):
        errors.append("O programa está vazio.")
    for port in re.findall(r"Port\.([A-Z][0-9]?)", code):
        valid = port in MOTOR_PORTS or port in SENSOR_PORTS
        if not valid:
            errors.append(f"Porta inválida: {port}")
    if "drive_left" in code and "drive_right" not in code:
        errors.append("Movimento de robô precisa dos dois motores configurados.")
    return list(dict.fromkeys(errors))

def validate_project(data):
    errors = []
    if not isinstance(data, dict):
        return ["O projeto não é um objeto JSON válido."]
    if "xml" not in data:
        errors.append("O projeto não possui XML do Blockly.")
    if "code" in data:
        errors.extend(validate_code(data["code"]))
    return errors
