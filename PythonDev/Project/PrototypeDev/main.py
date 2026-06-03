"""
ReplicatePic_v2_IN_PLACE_Z.py
────────────────────────────
Handshake con Arduino para inspección de pelotas.

Flujo automático:
  Arduino detecta A5 HIGH
    → manda "IN PLACE"
    → Python manda 'g' al Arduino
    → Arduino prende luces una por una
    → Python captura foto y manda 'k'
    → Arduino manda 'z' cuando ya terminó todas las fotos
    → Python clasifica
    → manda servo b/m
    → espera 0.5 s
    → manda 's' para steppers
    → al recibir STEPPERS_LISTOS:
        rota memoria
        vuelve a esperar "IN PLACE"

IMPORTANTE:
  Arduino debe mandar:
    Serial.write('z');
  cuando termine la secuencia de fotos.
"""

import os
import sys
import time
import queue
import random
import threading
import traceback
from pathlib import Path

import joblib
import numpy as np
import serial
from serial.tools import list_ports

from camera_utils  import open_camera, set_camera, warmup_camera, read_frame, capture_gray_frame, release_camera
from roi_utils     import croptoroi
from features      import basic_features
from glare         import glare_stats
from motor_calibration import (
    calibrar_motores_con_fotos,
    calibrar_motores,
    imprimir_resultado_calibracion,
    mostrar_fotos_calibracion,
    mostrar_recortes_calibracion,
    mostrar_resultado_calibracion,
)


# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────
BAUDRATE = 9600

# Un ROI por estacion: (x, y, w, h)
# Ajusta cada tupla con las coordenadas reales de cada estacion.
ROIS_POR_ESTACION = [
    (145, 70, 93, 92),  # Estacion 1
    (285, 65, 91, 88),  # Estacion 2
    (305, 290, 96, 100),  # Estacion 3
    (471, 315, 109, 98),  # Estacion 4
]


NUM_ESTACIONES = 4
LUCES_POR_EST  = 4
LUZ_CALIBRACION_POR_ESTACION = [0, 0, 1, 0]

SERVO_SETTLE_S    = 0.5
STEPPER_TIMEOUT_S = 30.0
AUTO_CALIBRATION_EVERY_CYCLES = 5
MODEL_PATH = Path(__file__).resolve().parents[3] / "golf_ball_rf_model.pkl"

CALIBRATION_ERROR_THRESHOLD_PX = 6.0
CALIBRATION_STEPS_PER_PIXEL = 0.5
CALIBRATION_MIN_STEPS = 2
CALIBRATION_MAX_STEPS = 30

CALIBRATION_PARAMS_BY_STATION = {
    1: {
        "threshold_px": 6.0,
        "steps_per_pixel": 9.0,
        "min_steps": 18,
        "max_steps": 220,
    },
    2: {
        "threshold_px": 3.0,
        "steps_per_pixel": 5.9,
        "min_steps": 18,
        "max_steps": 220,
    },
    3: {
        "threshold_px": 6.0,
        "steps_per_pixel": 8.8,
        "min_steps": 18,
        "extra_steps": 0,
        "max_steps": 220,
    },
    4: {
        "threshold_px": 6.0,
        "steps_per_pixel": 9.0,
        "min_steps": 18,
        "max_steps": 220,
    },
}

CALIBRATION_AXIS_BY_STATION = {
    1: "x",
    2: "x",
    3: "y",
    4: "x",
}

CALIBRATION_SIGN_BY_STATION = {
    1: 1,
    2: 1,
    3: 1,
    4: 1,
}

ARDUINO_KEYWORDS = ("arduino", "ch340", "wch", "usb serial", "usb-serial")

if len(ROIS_POR_ESTACION) != NUM_ESTACIONES:
    raise ValueError("ROIS_POR_ESTACION debe tener un ROI por estacion.")


# ─────────────────────────────────────────────────────────────
# FEATURES
# ─────────────────────────────────────────────────────────────
FEATURE_NAMES = [
    "mean_intensity", "std_intensity", "min_intensity", "max_intensity",
    "mean_grad",      "std_grad",      "max_grad",
    "mean_abs_lap",   "std_lap",
    "glare_pct",
]

N_FEATURES = len(FEATURE_NAMES)


def extraer_features(img_roi: np.ndarray) -> np.ndarray:
    """Imagen ROI -> vector de features brutas."""
    f = basic_features(img_roi)
    g = glare_stats(img_roi, bright_thr=0.98)

    vec = [
        f["mean_intensity"], f["std_intensity"],
        f["min_intensity"],  f["max_intensity"],
        f["mean_grad"],      f["std_grad"],       f["max_grad"],
        f["mean_abs_lap"],   f["std_lap"],
        g["glare_percentage"],
    ]

    return np.array(vec, dtype=np.float32)


def derivar_features(mat: np.ndarray) -> np.ndarray:
    """Matriz 4xN_FEATURES -> vector derivado para clasificador."""
    return np.concatenate([
        np.std(mat,  axis=0),
        np.mean(mat, axis=0),
        np.max(mat,  axis=0),
        np.min(mat,  axis=0),
    ])


def clasificar(vec_derivado: np.ndarray) -> bool:
    """
    Placeholder:
      True  = BUENA
      False = MALA

    Reemplazar después por modelo real:
      import joblib
      modelo = joblib.load("modelo.pkl")
      return bool(modelo.predict([vec_derivado])[0])
    """
    return random.choice([True, False])


_modelo_bundle = None


def cargar_modelo():
    global _modelo_bundle

    if _modelo_bundle is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"No existe el modelo entrenado: {MODEL_PATH}")

        _modelo_bundle = joblib.load(MODEL_PATH)

    return _modelo_bundle


def clasificar(vec_derivado: np.ndarray) -> bool:
    """True = BUENA, False = MALA."""
    bundle = cargar_modelo()
    modelo = bundle["model"]
    threshold = float(bundle.get("good_probability_threshold", 0.5))

    x = np.asarray(vec_derivado, dtype=np.float32).reshape(1, -1)

    if hasattr(modelo, "predict_proba"):
        proba_buena = float(modelo.predict_proba(x)[0][1])
        return proba_buena >= threshold

    return bool(modelo.predict(x)[0])


def fusionar_estado(previo, actual):
    """
    Mantiene MALA si alguna inspeccion anterior o actual fue mala.

    None  = aun no hay dato para esa posicion
    True  = BUENA
    False = MALA
    """
    if previo is False or actual is False:
        return False

    if previo is True or actual is True:
        return True

    return None


def estado_texto(estado):
    if estado is None:
        return "-"

    return "BUENA" if estado else "MALA"


# ─────────────────────────────────────────────────────────────
# LECTOR DE STDIN
# ─────────────────────────────────────────────────────────────
_stdin_queue: queue.Queue = queue.Queue()


def _stdin_worker():
    while True:
        try:
            linea = input()
            _stdin_queue.put(linea.strip().lower())
        except EOFError:
            break


def _leer_cmd() -> str:
    try:
        return _stdin_queue.get_nowait()
    except queue.Empty:
        return ""


# ─────────────────────────────────────────────────────────────
# UTILIDADES SERIAL
# ─────────────────────────────────────────────────────────────
def find_arduino_port() -> str:
    ports = list(list_ports.comports())

    for p in ports:
        desc = f"{p.description} {p.manufacturer or ''}".lower()
        if any(k in desc for k in ARDUINO_KEYWORDS):
            return p.device

    if len(ports) == 1:
        return ports[0].device

    available = ", ".join(p.device for p in ports) or "ninguno"
    raise RuntimeError(f"No se encontró Arduino. Puertos: {available}")


def decodificar_paso(byte_recibido: bytes):
    """
    Arduino manda:
      '1'-'9' para pasos 1-9
      'A'-'G' para pasos 10-16

    Orden fisico de luces:
      pasos  1-4  -> estacion 4
      pasos  5-8  -> estacion 3
      pasos  9-12 -> estacion 2
      pasos 13-16 -> estacion 1

    Devuelve:
      estacion, luz_en_estacion, paso_global
    """
    c = byte_recibido.decode("ascii", errors="ignore")

    if c.isdigit() and c != "0":
        paso = int(c)
    elif c.upper() in "ABCDEFG":
        paso = 10 + ord(c.upper()) - ord("A")
    else:
        return None

    paso_idx = paso - 1

    grupo_fisico    = paso_idx // LUCES_POR_EST
    estacion        = (NUM_ESTACIONES - 1) - grupo_fisico
    luz_en_estacion = paso_idx % LUCES_POR_EST

    return estacion, luz_en_estacion, paso


def procesar_fotos_listas(ser, memoria):
    """
    Cuando Arduino manda 'z':
      - imprime clasificación final
      - decide servo según posición 4
      - manda b/m
      - espera
      - manda s para steppers
    """
    print("\n══ Clasificación final ══")

    for i, e in enumerate(memoria):
        estado_txt = "—" if e is None else ("BUENA" if e else "MALA")
        print(f"  Pelota {i + 1}: {estado_txt}")

    # Pelota en posición 4 es la que sale
    estado_pos4 = memoria[NUM_ESTACIONES - 1]

    # Si no hay dato, por seguridad la tratamos como mala
    if estado_pos4 is None:
        estado_pos4 = False

    # Servo antes de steppers
    cmd_servo = b"b" if estado_pos4 else b"m"

    print(
        f"\nServo: "
        f"{'derecha (BUENA)' if estado_pos4 else 'izquierda (MALA)'}"
    )

    ser.write(cmd_servo)
    time.sleep(SERVO_SETTLE_S)

    # Ahora sí: mandar steppers
    print("Enviando 's' al Arduino para mover steppers...")
    ser.reset_input_buffer()
    ser.write(b"s")


def combinar_fotos_calibracion(frames_por_luz):
    frames_combinados = []

    for frames_luces in frames_por_luz:
        if any(frame is None for frame in frames_luces):
            frames_combinados.append(None)
            continue

        base_h, base_w = frames_luces[0].shape[:2]
        combined = np.zeros_like(frames_luces[0], dtype=np.float32)

        for frame in frames_luces:
            if frame.shape[:2] != (base_h, base_w):
                combined = None
                break

            combined += frame.astype(np.float32) * 0.25

        if combined is None:
            frames_combinados.append(None)
        else:
            frames_combinados.append(np.clip(combined, 0, 255).astype(np.uint8))

    return frames_combinados


def calcular_steps_calibracion(station, error_px):
    params = CALIBRATION_PARAMS_BY_STATION.get(station, {})
    threshold_px = params.get("threshold_px", CALIBRATION_ERROR_THRESHOLD_PX)
    steps_per_pixel = params.get("steps_per_pixel", CALIBRATION_STEPS_PER_PIXEL)
    min_steps = params.get("min_steps", CALIBRATION_MIN_STEPS)
    max_steps = params.get("max_steps", CALIBRATION_MAX_STEPS)
    extra_steps = params.get("extra_steps", 0)

    magnitude = abs(float(error_px))

    if magnitude < threshold_px:
        return 0

    steps = int(round(magnitude * steps_per_pixel)) + extra_steps
    return max(min_steps, min(max_steps, steps))


def esperar_respuesta_correccion(ser, timeout_s=8.0):
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        if ser.in_waiting > 0:
            line = ser.readline().decode("ascii", errors="ignore").strip()
            if line:
                print(f"[Arduino] {line}")
                if "CORRECCION_LISTA" in line or "CORRECCION_INVALIDA" in line:
                    return line

        time.sleep(0.01)

    print("WARNING: timeout esperando respuesta de correccion.")
    return ""


def enviar_correcciones_calibracion(ser, result):
    print("\n=== Correcciones Arduino ===")
    any_sent = False

    for detection in result.detections:
        station = detection.station

        if station not in CALIBRATION_AXIS_BY_STATION:
            continue

        if not detection.ok or detection.error_px is None:
            print(f"  E{station}: sin deteccion, no corrijo.")
            continue

        axis = CALIBRATION_AXIS_BY_STATION[station]
        error_value = detection.error_px[0] if axis == "x" else detection.error_px[1]
        steps = calcular_steps_calibracion(station, error_value)

        if steps == 0:
            print(f"  E{station}: error {axis}={error_value:+.1f}px dentro de umbral.")
            continue

        direction = 1 if error_value > 0 else -1
        signed_steps = direction * steps * CALIBRATION_SIGN_BY_STATION[station]
        command = f"R {station} {signed_steps}\n"

        print(
            f"  E{station}: error {axis}={error_value:+.1f}px "
            f"-> motor {station}, steps {signed_steps:+d}"
        )
        ser.write(command.encode("ascii"))
        esperar_respuesta_correccion(ser)
        any_sent = True

    if not any_sent:
        print("  Sin correcciones necesarias.")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    t = threading.Thread(target=_stdin_worker, daemon=True)
    t.start()

    cam = None
    ser = None

    try:
        port = find_arduino_port()
        print(f"Arduino en {port}")

        cam = open_camera()
        set_camera(cam, width=640, height=480, buffer_size=1)
        warmup_camera(cam, frames=10)

        ser = serial.Serial(port, BAUDRATE, timeout=1)
        time.sleep(2)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        matrices = [
            np.zeros((LUCES_POR_EST, N_FEATURES), dtype=np.float32)
            for _ in range(NUM_ESTACIONES)
        ]

        memoria = [None] * NUM_ESTACIONES

        esperando_steppers = False
        t_inicio_steppers = None
        calibrando_con_luces = False
        calibracion_auto_pendiente = False
        ciclos_completados = 0
        frames_calibracion_luces = [
            [None] * LUCES_POR_EST for _ in range(NUM_ESTACIONES)
        ]

        def reset_ciclo():
            nonlocal matrices, esperando_steppers, t_inicio_steppers

            matrices = [
                np.zeros((LUCES_POR_EST, N_FEATURES), dtype=np.float32)
                for _ in range(NUM_ESTACIONES)
            ]

            esperando_steppers = False
            t_inicio_steppers = None

        print("\nListo.")
        print("  Esperando IN PLACE desde Arduino")
        print("  Arduino debe mandar 'z' al terminar fotos")
        print("  salir → apagar y cerrar\n")

        while True:
            # ─────────────────────────────────────────────
            # COMANDOS DE TERMINAL
            # ─────────────────────────────────────────────
            cmd = _leer_cmd()

            if cmd == "salir":
                print("Saliendo. Mandando 'o' al Arduino...")
                ser.write(b"o")
                break

            if cmd == "calibrar":
                frame = read_frame(cam)
                resultado_cal = calibrar_motores(
                    frame,
                    ROIS_POR_ESTACION,
                    expand_scale=1.25,
                    tolerance_px=8.0,
                )
                imprimir_resultado_calibracion(resultado_cal)
                mostrar_resultado_calibracion(frame, resultado_cal)
                mostrar_recortes_calibracion(frame, resultado_cal)

            if cmd == "calibrar_luces":
                calibrando_con_luces = True
                frames_calibracion_luces = [
                    [None] * LUCES_POR_EST for _ in range(NUM_ESTACIONES)
                ]
                ser.reset_input_buffer()
                print("Calibracion con luces: enviando 'g'.")
                print("Capturare L1-L4 por estacion, sin desplegar fotos.")
                ser.write(b"g")

            # ─────────────────────────────────────────────
            # DATOS DEL ARDUINO
            # ─────────────────────────────────────────────
            if ser.in_waiting > 0:
                raw = ser.read(1)
                c = raw.decode("ascii", errors="ignore")

                # ─────────────────────────────────────
                # FIN DE FOTOS: Arduino manda 'z'
                # ─────────────────────────────────────
                if c == "z":
                    if calibrando_con_luces:
                        print("[Arduino] Fotos de calibracion listas.")
                        frames_combinados = combinar_fotos_calibracion(frames_calibracion_luces)
                        faltantes = [
                            idx + 1
                            for idx, frame in enumerate(frames_combinados)
                            if frame is None
                        ]
                        if faltantes:
                            print(
                                "Faltaron fotos de calibracion en: "
                                + ", ".join(f"E{idx}" for idx in faltantes)
                            )
                            calibrando_con_luces = False
                            ser.write(b"o")
                            continue

                        resultado_cal = calibrar_motores_con_fotos(
                            frames_combinados,
                            ROIS_POR_ESTACION,
                            expand_scale=1.25,
                            tolerance_px=8.0,
                        )
                        imprimir_resultado_calibracion(resultado_cal)
                        enviar_correcciones_calibracion(ser, resultado_cal)

                        calibrando_con_luces = False
                        calibracion_auto_pendiente = False
                        reset_ciclo()
                        ser.reset_input_buffer()
                        print("Calibracion lista. Iniciando captura normal de esta pelota...")
                        ser.write(b"g")
                        continue

                    print("[Arduino] FOTOS_LISTAS")

                    procesar_fotos_listas(ser, memoria)

                    esperando_steppers = True
                    t_inicio_steppers = time.time()

                # ─────────────────────────────────────
                # PASOS DE LUZ: 1-9, A-G
                # ─────────────────────────────────────
                elif c in "123456789ABCDEFG":
                    decoded = decodificar_paso(raw)

                    if decoded is None:
                        continue

                    estacion, luz, paso = decoded

                    if calibrando_con_luces:
                        print(
                            f"[Calibracion] Capturando E{estacion + 1} "
                            f"L{luz + 1} (paso {paso:02d})"
                        )
                        frames_calibracion_luces[estacion][luz] = read_frame(cam)

                        ser.write(b"k")
                        continue

                    print(
                        f"[Paso {paso:02d}] "
                        f"Estación {estacion + 1}, cara {luz + 1} — capturando..."
                    )

                    roi_x, roi_y, roi_w, roi_h = ROIS_POR_ESTACION[estacion]

                    gray = capture_gray_frame(cam, normalize=True)
                    roi  = croptoroi(gray, roi_x, roi_y, roi_w, roi_h)
                    vec  = extraer_features(roi)

                    matrices[estacion][luz] = vec

                    print(f"  features: {vec.round(3)}")

                    # ACK para que Arduino avance a la siguiente luz
                    ser.write(b"k")

                    # Cuando termina las 4 caras de una estación, clasificar
                    if luz == LUCES_POR_EST - 1:
                        vec_rf = derivar_features(matrices[estacion])
                        resultado = clasificar(vec_rf)

                        previo = memoria[estacion]
                        memoria[estacion] = fusionar_estado(previo, resultado)
                        print(
                            f"     carry previo={estado_texto(previo)} "
                            f"actual={estado_texto(resultado)} "
                            f"final={estado_texto(memoria[estacion])}"
                        )

                        print(
                            f"  → Estación {estacion + 1}: "
                            f"{'BUENA' if memoria[estacion] else 'MALA'}"
                        )

                elif c in ("\r", "\n", ""):
                    pass

                else:
                    # Leer resto de línea de Arduino
                    rest = ser.read_until(b"\n").decode("ascii", errors="ignore").strip()
                    linea = (c + rest).strip()

                    if linea:
                        print(f"[Arduino] {linea}")

                    if (
                        "IN PLACE" in linea
                        and calibrando_con_luces
                    ):
                        print("IN PLACE recibido durante calibracion; lo ignoro.")
                        continue

                    if (
                        "IN PLACE" in linea
                        and not esperando_steppers
                        and calibracion_auto_pendiente
                    ):
                        reset_ciclo()
                        calibrando_con_luces = True
                        frames_calibracion_luces = [
                            [None] * LUCES_POR_EST for _ in range(NUM_ESTACIONES)
                        ]
                        ser.reset_input_buffer()
                        print("IN PLACE detectado. Ejecutando calibracion automatica antes del ciclo normal...")
                        ser.write(b"g")
                        continue

                    # ─────────────────────────────────────
                    # SENSOR IN PLACE → INICIAR CICLO
                    # ─────────────────────────────────────
                    if "IN PLACE" in linea:
                        if esperando_steppers:
                            print("IN PLACE recibido, pero todavía espero que terminen los steppers.")
                        else:
                            reset_ciclo()
                            ser.reset_input_buffer()
                            print("IN PLACE detectado. Enviando 'g' al Arduino para iniciar luces/fotos...")
                            ser.write(b"g")

                    # ─────────────────────────────────────
                    # FIN DE STEPPERS
                    # ─────────────────────────────────────
                    elif "STEPPERS_LISTOS" in linea:
                        esperando_steppers = False
                        t_inicio_steppers = None

                        # Rotar memoria:
                        # pos 4 sale, 3→4, 2→3, 1→2, nueva pos 1 = None
                        memoria.pop()
                        memoria.insert(0, None)

                        print("\nSteppers terminados.")
                        print("Memoria actualizada:")

                        for i, e in enumerate(memoria):
                            estado_txt = "—" if e is None else ("BUENA" if e else "MALA")
                            print(f"  Pos {i + 1}: {estado_txt}")

                        ciclos_completados += 1
                        if ciclos_completados % AUTO_CALIBRATION_EVERY_CYCLES == 0:
                            calibracion_auto_pendiente = True
                            print(
                                f"\nCalibracion automatica pendiente "
                                f"({ciclos_completados} ciclos)."
                            )

                        print("\nEsperando nuevo IN PLACE...")

                    elif "APAGADO" in linea:
                        esperando_steppers = False
                        t_inicio_steppers = None

            # ─────────────────────────────────────────────
            # TIMEOUT STEPPERS
            # ─────────────────────────────────────────────
            if esperando_steppers and t_inicio_steppers is not None:
                if time.time() - t_inicio_steppers > STEPPER_TIMEOUT_S:
                    print("WARNING: timeout esperando STEPPERS_LISTOS.")
                    print("Mandando 'o' por seguridad.")
                    ser.write(b"o")

                    esperando_steppers = False
                    t_inicio_steppers = None

            time.sleep(0.005)

    except serial.SerialException as e:
        print(f"Error serial: {e}")

    except KeyboardInterrupt:
        print("\nInterrumpido.")

    except Exception:
        traceback.print_exc()

    finally:
        if ser and ser.is_open:
            try:
                ser.write(b"o")
            except Exception:
                pass

            ser.close()
            print("Puerto serial cerrado.")

        if cam:
            release_camera(cam)


if __name__ == "__main__":
    main()
