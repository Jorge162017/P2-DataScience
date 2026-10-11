"""Selecciona regiones 256x256 usando la máscara de tejido ya fijada.

No cambia el detector ni sus umbrales. Las coordenadas corresponden al PNG
original reducido (1100/1120 px de ancho). La prueba no define parámetros.
"""

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from analizar_reducidas import ROOT, WIDTH, background_and_mask


INPUT = ROOT / "datos/particion_imagenes.csv"
EDA = ROOT / "resultados/eda_reducidas.csv"
REGIONS = ROOT / "datos/regiones_seleccionadas.csv"
SUMMARY = ROOT / "resultados/resumen_seleccion_regiones.csv"
REPORT = ROOT / "resultados/seleccion_regiones.json"
TILE = 256
STRIDE = 128
# Elegido al revisar únicamente ejemplos escasos de entrenamiento: 20 % dejaba
# fuera tejido visible en 4ded24_0 y c31442_0. La prueba no ajusta este corte.
MIN_TISSUE = 0.08
MAX_PER_IMAGE = 8
MAX_IOU = 0.25


def starts(length):
    last = length - TILE
    if last < 0:
        raise ValueError(f"Imagen menor de {TILE} px")
    return sorted(set(range(0, last + 1, STRIDE)) | {last})


def fraction(mask, box, image_size):
    width, height = image_size
    mh, mw = mask.shape
    x, y = box
    x0 = round(x * mw / width)
    x1 = round((x + TILE) * mw / width)
    y0 = round(y * mh / height)
    y1 = round((y + TILE) * mh / height)
    return float(mask[y0:y1, x0:x1].mean())


def iou(a, b):
    ax, ay = a
    bx, by = b
    overlap_x = max(0, min(ax + TILE, bx + TILE) - max(ax, bx))
    overlap_y = max(0, min(ay + TILE, by + TILE) - max(ay, by))
    area = overlap_x * overlap_y
    return area / (2 * TILE * TILE - area)


def inspect(row):
    path = ROOT / row["archivo_reducido"]
    with Image.open(path) as image:
        image_size = image.size
        preview = image.convert("RGB")
        preview.thumbnail((WIDTH, 20000), Image.Resampling.LANCZOS)
        rgb = np.asarray(preview)
    _, mask, _, _ = background_and_mask(rgb)
    candidates = [(fraction(mask, (x, y), image_size), x, y)
                  for y in starts(image_size[1]) for x in starts(image_size[0])]
    candidates.sort(key=lambda item: (-item[0], item[2], item[1]))
    selected = []
    for coverage, x, y in candidates:
        if coverage < MIN_TISSUE:
            break
        if all(iou((x, y), (old_x, old_y)) <= MAX_IOU for _, old_x, old_y in selected):
            selected.append((coverage, x, y))
            if len(selected) == MAX_PER_IMAGE:
                break
    return candidates, selected, float(mask.mean())


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    with INPUT.open(newline="", encoding="utf-8") as stream:
        images = list(csv.DictReader(stream))
    with EDA.open(newline="", encoding="utf-8") as stream:
        previous = {row["image_id"]: row for row in csv.DictReader(stream)}
    if len(images) != 754 or len(previous) != 754:
        raise ValueError("No están las 754 imágenes y sus resultados EDA")
    selected_rows = []
    summaries = []
    for index, row in enumerate(images):
        candidates, selected, tissue = inspect(row)
        if abs(tissue - float(previous[row["image_id"]]["fraccion_candidata_tejido"])) > 0.00001:
            raise AssertionError(f"La máscara cambió desde el EDA: {row['image_id']}")
        summaries.append({
            "image_id": row["image_id"], "patient_id": row["patient_id"],
            "center_id": row["center_id"], "label": row["label"],
            "particion": row["particion"],
            "fraccion_candidata_tejido": round(tissue, 5),
            "candidatos": len(candidates),
            "mejor_region_fraccion": round(candidates[0][0], 5),
            "regiones_sobre_umbral": sum(item[0] >= MIN_TISSUE for item in candidates),
            "regiones_seleccionadas": len(selected),
            "estado": "seleccionada" if selected else "sin_region_8pct",
        })
        for rank, (coverage, x, y) in enumerate(selected, 1):
            selected_rows.append({
                "image_id": row["image_id"], "patient_id": row["patient_id"],
                "center_id": row["center_id"], "label": row["label"],
                "particion": row["particion"], "archivo_reducido": row["archivo_reducido"],
                "region_num": rank, "x": x, "y": y, "lado_px": TILE,
                "fraccion_candidata_tejido": round(coverage, 5),
            })
        if (index + 1) % 100 == 0:
            print(f"Procesadas {index + 1}/754", flush=True)
    write_csv(REGIONS, selected_rows,
              ("image_id", "patient_id", "center_id", "label", "particion",
               "archivo_reducido", "region_num", "x", "y", "lado_px",
               "fraccion_candidata_tejido"))
    write_csv(SUMMARY, summaries,
              ("image_id", "patient_id", "center_id", "label", "particion",
               "fraccion_candidata_tejido", "candidatos", "mejor_region_fraccion",
               "regiones_sobre_umbral", "regiones_seleccionadas", "estado"))
    report = {
        "imagenes": len(images), "pacientes": len({row["patient_id"] for row in images}),
        "regiones_seleccionadas": len(selected_rows),
        "imagenes_con_regiones": sum(row["regiones_seleccionadas"] > 0 for row in summaries),
        "imagenes_sin_regiones": sum(row["regiones_seleccionadas"] == 0 for row in summaries),
        "imagenes_sin_regiones_ids": [row["image_id"] for row in summaries
                                      if row["regiones_seleccionadas"] == 0],
        "pacientes_con_regiones": len({row["patient_id"] for row in selected_rows}),
        "pacientes_sin_regiones_ids": sorted({row["patient_id"] for row in images}
                                             - {row["patient_id"] for row in selected_rows}),
        "sin_regiones_por_particion": dict(Counter(row["particion"] for row in summaries
                                           if row["regiones_seleccionadas"] == 0)),
        "regiones_por_particion": dict(Counter(row["particion"] for row in selected_rows)),
        "parametros": {"tile_px": TILE, "stride_px": STRIDE,
                       "fraccion_minima": MIN_TISSUE, "max_regiones_por_imagen": MAX_PER_IMAGE,
                       "max_iou": MAX_IOU, "ancho_mascara_px": WIDTH},
        "nota": "Las coordenadas están en el PNG reducido; no son recortes extraídos ni etiquetas histológicas.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
