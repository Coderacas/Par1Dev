import csv
import queue
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import cv2 as cv
import numpy as np
import serial

from camera_utils import (
    open_camera,
    set_camera,
    warmup_camera,
    read_frame,
    frame_to_gray,
    show_live_frame,
    get_key,
    release_camera,
)
from roi_utils import croptoroi
from main import (
    BAUDRATE,
    FEATURE_NAMES,
    LUCES_POR_EST,
    N_FEATURES,
    ROIS_POR_ESTACION,
    decodificar_paso,
    derivar_features,
    extraer_features,
    find_arduino_port,
)


OUTPUT_DIR = Path(__file__).resolve().parent / "data"
RAW_CSV = OUTPUT_DIR / "features_luces_raw.csv"
DERIVED_CSV = OUTPUT_DIR / "features_dataset_ml.csv"
WINDOW_NAME = "Dataset luces"

LABEL_COLORS = {
    None: (0, 255, 255),
    "buena": (0, 200, 0),
    "mala": (0, 0, 255),
}

DERIVED_FEATURE_NAMES = (
    [f"std_{name}" for name in FEATURE_NAMES]
    + [f"mean_{name}" for name in FEATURE_NAMES]
    + [f"max_{name}" for name in FEATURE_NAMES]
    + [f"min_{name}" for name in FEATURE_NAMES]
)

_stdin_queue: queue.Queue = queue.Queue()


def _stdin_worker():
    while True:
        try:
            _stdin_queue.put(input().strip().lower())
        except EOFError:
            break


def _leer_cmd_terminal():
    try:
        return _stdin_queue.get_nowait()
    except queue.Empty:
        return ""


def label_desde_cmd(cmd):
    if cmd in ("b", "buena", "good"):
        return "buena"

    if cmd in ("m", "mala", "bad"):
        return "mala"

    return None


def asegurar_csvs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_CSV.exists():
        with RAW_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "sample_id",
                "label",
                "estacion",
                "luz",
                "paso_global",
                "roi_x",
                "roi_y",
                "roi_w",
                "roi_h",
                *FEATURE_NAMES,
            ])

    if not DERIVED_CSV.exists():
        with DERIVED_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "sample_id",
                "label",
                "estacion",
                "roi_x",
                "roi_y",
                "roi_w",
                "roi_h",
                *DERIVED_FEATURE_NAMES,
            ])


def siguiente_sample_id():
    if not DERIVED_CSV.exists():
        return 1

    with DERIVED_CSV.open("r", newline="", encoding="utf-8") as f:
        rows = csv.DictReader(f)
        ids = [int(row["sample_id"]) for row in rows if row.get("sample_id")]

    return max(ids, default=0) + 1


def dibujar_rois(frame, estacion_actual=None, labels=None, mensaje=""):
    preview = frame.copy()

    for idx, (x, y, w, h) in enumerate(ROIS_POR_ESTACION, start=1):
        label = labels[idx - 1] if labels is not None else None
        color = LABEL_COLORS[label]
        thickness = 4 if estacion_actual == idx - 1 else 2

        cv.rectangle(preview, (x, y), (x + w, y + h), color, thickness)
        cv.putText(
            preview,
            f"E{idx} {label or ''}",
            (x, max(20, y - 8)),
            cv.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv.LINE_AA,
        )

    if mensaje:
        cv.putText(
            preview,
            mensaje,
            (20, 35),
            cv.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 255),
            2,
            cv.LINE_AA,
        )

    return preview


def pedir_label_estacion(cam, estacion, luz, paso, labels):
    print(f"\nPaso {paso:02d}: estacion {estacion + 1}, luz {luz + 1}")
    print("Marca esta pelota/estacion: b=buena, m=mala, q=salir")

    while True:
        frame = read_frame(cam)
        preview = dibujar_rois(
            frame,
            estacion_actual=estacion,
            labels=labels,
            mensaje=f"E{estacion + 1} L{luz + 1}: b=buena, m=mala",
        )
        show_live_frame(WINDOW_NAME, preview)

        key = get_key(30)
        cmd = _leer_cmd_terminal()

        if key in (ord("q"), 27) or cmd in ("q", "salir", "exit"):
            raise KeyboardInterrupt

        if key == ord("b"):
            return "buena", frame

        if key == ord("m"):
            return "mala", frame

        label = label_desde_cmd(cmd)
        if label is not None:
            return label, frame


def capturar_features_luz(cam, estacion, luz, paso, labels, frame=None):
    if frame is None:
        frame = read_frame(cam)

    x, y, w, h = ROIS_POR_ESTACION[estacion]
    gray = frame_to_gray(frame, normalize=True)
    roi = croptoroi(gray, x, y, w, h)
    return extraer_features(roi)


def guardar_raw(sample_id, label, estacion, luz, paso, vec):
    timestamp = datetime.now().isoformat(timespec="seconds")
    x, y, w, h = ROIS_POR_ESTACION[estacion]

    with RAW_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            sample_id,
            label,
            estacion + 1,
            luz + 1,
            paso,
            x,
            y,
            w,
            h,
            *[float(v) for v in vec],
        ])


def guardar_derived(sample_id, label, estacion, mat):
    timestamp = datetime.now().isoformat(timespec="seconds")
    x, y, w, h = ROIS_POR_ESTACION[estacion]
    vec = derivar_features(mat)

    with DERIVED_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            sample_id,
            label,
            estacion + 1,
            x,
            y,
            w,
            h,
            *[float(v) for v in vec],
        ])

    print(f"Guardado ML sample_id={sample_id}, E{estacion + 1}, label={label}")


def leer_linea_desde_primer_caracter(ser, primer_caracter):
    resto = ser.read_until(b"\n").decode("ascii", errors="ignore").strip()
    return (primer_caracter + resto).strip()


def pausar_si_fallo():
    try:
        input("\nPresiona ENTER para cerrar...")
    except EOFError:
        pass


def main():
    print("Iniciando capturador de dataset...")
    threading.Thread(target=_stdin_worker, daemon=True).start()
    asegurar_csvs()

    cam = None
    ser = None
    sample_id = siguiente_sample_id()

    matrices = [
        np.zeros((LUCES_POR_EST, N_FEATURES), dtype=np.float32)
        for _ in ROIS_POR_ESTACION
    ]
    labels = [None] * len(ROIS_POR_ESTACION)
    sample_ids = [None] * len(ROIS_POR_ESTACION)

    try:
        print("Buscando Arduino...")
        port = find_arduino_port()
        print(f"Arduino en {port}")

        print("Abriendo camara...")
        cam = open_camera()
        set_camera(cam, width=640, height=480, buffer_size=1)
        warmup_camera(cam, frames=10)
        print("Camara lista.")

        print("Abriendo puerto serial...")
        ser = serial.Serial(port, BAUDRATE, timeout=1)
        time.sleep(2)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print("Serial listo.")

        print("\nCaptura dataset con luces")
        print("1. Coloca la pelota y activa el sensor IN PLACE.")
        print("2. Primero captura automaticamente las 16 fotos/features.")
        print("3. Luego prende otra vez la luz 1 de cada estacion para etiquetar b/m.")
        print("4. El script guarda raw + dataset ML con esas etiquetas.")
        print("5. Escribe salir o presiona q para terminar.\n")
        print(f"Raw: {RAW_CSV}")
        print(f"ML : {DERIVED_CSV}\n")

        estado = "esperando_in_place"
        raw_records = [[None] * LUCES_POR_EST for _ in ROIS_POR_ESTACION]

        while True:
            cmd = _leer_cmd_terminal()
            if cmd in ("q", "salir", "exit"):
                break

            frame = read_frame(cam)
            mensaje = {
                "esperando_in_place": "Esperando IN PLACE",
                "capturando": "Capturando 16 fotos",
                "etiquetando": "Etiquetando con luz 1",
            }.get(estado, "")
            if estado != "capturando":
                preview = dibujar_rois(frame, labels=labels, mensaje=mensaje)
                show_live_frame(WINDOW_NAME, preview)
            get_key(1)

            if ser.in_waiting <= 0:
                time.sleep(0.005)
                continue

            raw = ser.read(1)
            c = raw.decode("ascii", errors="ignore")

            if c == "z":
                if estado == "capturando":
                    estado = "etiquetando"
                    labels = [None] * len(ROIS_POR_ESTACION)
                    print("[Arduino] FOTOS_LISTAS. Reiniciando luces para etiquetar...")
                    ser.reset_input_buffer()
                    ser.write(b"g")
                elif estado == "etiquetando":
                    estado = "esperando_in_place"
                    print("[Arduino] ETIQUETAS_LISTAS. Moviendo steppers...")
                    ser.reset_input_buffer()
                    ser.write(b"s")
                continue

            decoded = decodificar_paso(raw)
            if decoded is not None:
                estacion, luz, paso = decoded

                if estado == "capturando":
                    vec = capturar_features_luz(
                        cam,
                        estacion,
                        luz,
                        paso,
                        labels,
                    )

                    matrices[estacion][luz] = vec
                    raw_records[estacion][luz] = (paso, vec)

                    print(f"Capturada E{estacion + 1} L{luz + 1}")
                    ser.write(b"k")
                    continue

                if estado == "etiquetando":
                    if luz == 0:
                        print(f"Etiquetando E{estacion + 1}")
                        label, _ = pedir_label_estacion(
                            cam,
                            estacion,
                            luz,
                            paso,
                            labels,
                        )
                        labels[estacion] = label
                        sample_ids[estacion] = sample_id
                        sample_id += 1

                        for luz_idx, record in enumerate(raw_records[estacion]):
                            if record is None:
                                raise RuntimeError(
                                    f"Faltan features de E{estacion + 1} L{luz_idx + 1}"
                                )

                            paso_raw, vec_raw = record
                            guardar_raw(
                                sample_ids[estacion],
                                label,
                                estacion,
                                luz_idx,
                                paso_raw,
                                vec_raw,
                            )

                        guardar_derived(
                            sample_ids[estacion],
                            label,
                            estacion,
                            matrices[estacion],
                        )

                    ser.write(b"k")
                    continue

                if estado == "esperando_in_place":
                    ser.write(b"k")
                    continue

            if c in ("\r", "\n", ""):
                continue

            linea = leer_linea_desde_primer_caracter(ser, c)
            if linea:
                print(f"[Arduino] {linea}")

            if "IN PLACE" in linea and estado == "esperando_in_place":
                matrices = [
                    np.zeros((LUCES_POR_EST, N_FEATURES), dtype=np.float32)
                    for _ in ROIS_POR_ESTACION
                ]
                raw_records = [[None] * LUCES_POR_EST for _ in ROIS_POR_ESTACION]
                labels = [None] * len(ROIS_POR_ESTACION)
                sample_ids = [None] * len(ROIS_POR_ESTACION)

                estado = "capturando"
                ser.reset_input_buffer()
                print("IN PLACE detectado. Capturando 16 fotos...")
                ser.write(b"g")

            elif "STEPPERS_LISTOS" in linea:
                print("Steppers listos. Esperando siguiente pelota...")
                estado = "esperando_in_place"

            elif "APAGADO" in linea:
                estado = "esperando_in_place"

    except KeyboardInterrupt:
        print("\nCaptura detenida.")

    except Exception:
        print("\nERROR: el capturador se detuvo por una excepcion.")
        traceback.print_exc()
        pausar_si_fallo()

    finally:
        if ser and ser.is_open:
            try:
                ser.write(b"x")
            except Exception:
                pass
            ser.close()
            print("Puerto serial cerrado.")

        if cam:
            release_camera(cam)


if __name__ == "__main__":
    main()
