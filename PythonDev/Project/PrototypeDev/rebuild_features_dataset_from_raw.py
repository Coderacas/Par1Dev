import csv
from datetime import datetime
from pathlib import Path

import numpy as np

from main import DERIVED_FEATURE_NAMES, FEATURE_NAMES, ROIS_POR_ESTACION, derivar_features


DATA_DIR = Path(__file__).resolve().parent / "data"
RAW_CSV = DATA_DIR / "features_luces_raw.csv"
DERIVED_CSV = DATA_DIR / "features_dataset_ml.csv"


META_COLUMNS = {
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
}


def cargar_raw():
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"No existe raw CSV: {RAW_CSV}")

    with RAW_CSV.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError("features_luces_raw.csv esta vacio.")

    return rows


def reconstruir():
    rows = cargar_raw()
    grupos = {}

    for row in rows:
        label = row.get("label", "").strip().lower()
        if label not in ("buena", "mala"):
            continue

        sample_id = int(row["sample_id"])
        estacion = int(row["estacion"])
        luz = int(row["luz"])
        key = (sample_id, label, estacion)

        grupos.setdefault(key, {})[luz] = row

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    escritos = 0
    saltados = 0
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

        for (sample_id, label, estacion), luces in sorted(grupos.items()):
            if any(luz not in luces for luz in (1, 2, 3, 4)):
                saltados += 1
                continue

            mat = []
            for luz in (1, 2, 3, 4):
                mat.append([float(luces[luz][name]) for name in FEATURE_NAMES])

            mat = np.asarray(mat, dtype=np.float32)
            vec = derivar_features(mat, estacion=estacion)

            x, y, w, h = ROIS_POR_ESTACION[estacion - 1]
            writer.writerow([
                datetime.now().isoformat(timespec="seconds"),
                sample_id,
                label,
                estacion,
                x,
                y,
                w,
                h,
                *[float(v) for v in vec],
            ])
            escritos += 1

    print(f"Reconstruido: {DERIVED_CSV}")
    print(f"Filas escritas: {escritos}")
    print(f"Grupos saltados por luces incompletas: {saltados}")
    print(f"Features derivadas por fila: {len(DERIVED_FEATURE_NAMES)}")


if __name__ == "__main__":
    reconstruir()
