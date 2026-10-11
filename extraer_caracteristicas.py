"""Extrae color y textura de las regiones y agrega por paciente.

Los dos pacientes de entrenamiento sin regiones permanecen en la partición
original, pero no aparecen en esta tabla de características regionales.
"""

import csv
import json
from collections import defaultdict

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage as ndi


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "datos/regiones_seleccionadas.csv"
OUTPUT = ROOT / "resultados/modelos/caracteristicas_pacientes.csv"
REPORT = ROOT / "resultados/modelos/caracteristicas_resumen.json"
SIDE = 128


def patch_features(tile):
    small = tile.resize((SIDE, SIDE), Image.Resampling.BILINEAR)
    rgb = np.asarray(small.convert("RGB"), dtype=np.float32) / 255.0
    hsv = np.asarray(small.convert("HSV"), dtype=np.float32) / 255.0
    gray = rgb @ np.array([.299, .587, .114], dtype=np.float32)
    result = {}
    for name, array in (("r", rgb[:, :, 0]), ("g", rgb[:, :, 1]),
                        ("b", rgb[:, :, 2]), ("h", hsv[:, :, 0]),
                        ("s", hsv[:, :, 1]), ("v", hsv[:, :, 2])):
        result[f"{name}_media"] = float(array.mean())
        result[f"{name}_desv"] = float(array.std())
    for channel, name in ((rgb[:, :, 0], "r"), (rgb[:, :, 1], "g"),
                          (rgb[:, :, 2], "b"), (gray, "gris"),
                          (hsv[:, :, 1], "saturacion")):
        hist = np.histogram(channel, bins=8, range=(0, 1))[0] / channel.size
        for index, value in enumerate(hist):
            result[f"hist_{name}_{index}"] = float(value)
    result["gris_desv"] = float(gray.std())
    histogram = np.histogram(gray, bins=32, range=(0, 1))[0].astype(np.float64)
    probability = histogram[histogram > 0] / histogram.sum()
    result["gris_entropia"] = float(-(probability * np.log2(probability)).sum())
    gradient = np.hypot(ndi.sobel(gray, axis=0), ndi.sobel(gray, axis=1))
    result["gradiente_media"] = float(gradient.mean())
    result["gradiente_desv"] = float(gradient.std())
    result["laplaciano_var"] = float(ndi.laplace(gray).var())
    return result


def main():
    with SOURCE.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 5933:
        raise ValueError(f"Se esperaban 5933 regiones, hay {len(rows)}")
    by_image = defaultdict(list)
    for row in rows:
        by_image[row["image_id"]].append(row)
    records = []
    for index, (image_id, regions) in enumerate(by_image.items(), 1):
        path = ROOT / regions[0]["archivo_reducido"]
        with Image.open(path) as image:
            rgb_image = image.convert("RGB")
            for region in regions:
                x, y, side = (int(region[key]) for key in ("x", "y", "lado_px"))
                tile = rgb_image.crop((x, y, x + side, y + side))
                features = patch_features(tile)
                records.append({"patient_id": region["patient_id"],
                                "image_id": image_id, "label": region["label"],
                                "center_id": region["center_id"],
                                "particion": region["particion"], **features})
        if index % 100 == 0:
            print(f"Imágenes procesadas: {index}/{len(by_image)}", flush=True)
    data = pd.DataFrame.from_records(records)
    metadata = data.groupby("patient_id")[["label", "center_id", "particion"]].nunique()
    if (metadata != 1).any().any():
        raise ValueError("Un paciente tiene metadatos o partición inconsistentes")
    feature_columns = [column for column in data.columns
                       if column not in ("patient_id", "image_id", "label", "center_id", "particion")]
    grouped = data.groupby("patient_id", sort=True)
    means = grouped[feature_columns].mean().add_prefix("media_")
    deviations = grouped[feature_columns].std(ddof=0).add_prefix("desv_")
    patient_meta = grouped[["label", "center_id", "particion"]].first()
    out = pd.concat([patient_meta, means, deviations], axis=1).reset_index()
    if len(out) != 630 or not np.isfinite(out.select_dtypes(include="number").to_numpy()).all():
        raise ValueError("Características incompletas o no finitas")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, float_format="%.6g", lineterminator="\n")
    report = {
        "regiones": len(data), "imagenes_con_regiones": len(by_image),
        "pacientes": len(out), "caracteristicas_regionales": len(feature_columns),
        "caracteristicas_por_paciente": 2 * len(feature_columns),
        "pacientes_por_particion": out["particion"].value_counts().to_dict(),
        "pacientes_entrenamiento_sin_regiones": ["e72352", "fd3079"],
        "nota": "Características de color y textura descriptivas, agregadas por paciente; centro y etiqueta no son predictores.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
