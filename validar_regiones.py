"""Valida regiones seleccionadas y crea una muestra visual de entrenamiento."""

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from seleccionar_regiones import MAX_IOU, MAX_PER_IMAGE, MIN_TISSUE, ROOT, TILE, iou


REGIONS = ROOT / "datos/regiones_seleccionadas.csv"
SUMMARY = ROOT / "resultados/resumen_seleccion_regiones.csv"
SPLIT = ROOT / "datos/particion_imagenes.csv"
SAMPLE = ROOT / "resultados/figuras/regiones_seleccionadas_muestra.jpg"


def read(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    regions = read(REGIONS)
    summaries = read(SUMMARY)
    images = read(SPLIT)
    if len(images) != 754 or len(summaries) != 754:
        raise AssertionError("No están resumidas las 754 imágenes")
    image_map = {row["image_id"]: row for row in images}
    summary_map = {row["image_id"]: row for row in summaries}
    if len(image_map) != 754 or set(image_map) != set(summary_map):
        raise AssertionError("Identificadores de imagen inconsistentes")
    by_image = defaultdict(list)
    dimensions = {}
    for row in regions:
        image_id = row["image_id"]
        if image_id not in image_map:
            raise AssertionError(f"Imagen desconocida: {image_id}")
        source = image_map[image_id]
        for field in ("patient_id", "center_id", "label", "particion", "archivo_reducido"):
            if row[field] != source[field]:
                raise AssertionError(f"Fuga o metadato incorrecto: {image_id} {field}")
        x, y, side = (int(row[key]) for key in ("x", "y", "lado_px"))
        if side != TILE or x < 0 or y < 0:
            raise AssertionError(f"Coordenada incorrecta: {image_id}")
        if image_id not in dimensions:
            with Image.open(ROOT / row["archivo_reducido"]) as image:
                dimensions[image_id] = image.size
        width, height = dimensions[image_id]
        if x + side > width or y + side > height:
            raise AssertionError(f"Recorte fuera de imagen: {image_id}")
        if float(row["fraccion_candidata_tejido"]) < MIN_TISSUE - 0.00001:
            raise AssertionError(f"Recorte bajo umbral: {image_id}")
        by_image[image_id].append(row)
    for image_id, summary in summary_map.items():
        group = by_image[image_id]
        if int(summary["regiones_seleccionadas"]) != len(group) or len(group) > MAX_PER_IMAGE:
            raise AssertionError(f"Recuento incorrecto: {image_id}")
        if sorted(int(row["region_num"]) for row in group) != list(range(1, len(group) + 1)):
            raise AssertionError(f"Orden incorrecto: {image_id}")
        for i, first in enumerate(group):
            for second in group[i + 1:]:
                if iou((int(first["x"]), int(first["y"])),
                       (int(second["x"]), int(second["y"]))) > MAX_IOU + 1e-6:
                    raise AssertionError(f"Recortes demasiado superpuestos: {image_id}")
    patient_totals = Counter()
    for row in regions:
        patient_totals[row["patient_id"]] += 1
    no_regions = sorted({row["patient_id"] for row in images} - set(patient_totals))
    patient_split = {row["patient_id"]: row["particion"] for row in images}
    if any(patient_split[patient_id] != "entrenamiento" for patient_id in no_regions):
        raise AssertionError(f"Paciente de validación o prueba sin regiones: {no_regions}")

    training = [row for row in regions if row["particion"] == "entrenamiento"
                and row["region_num"] == "1"]
    rng = random.Random(22)
    chosen = []
    for center in sorted({row["center_id"] for row in training}, key=int):
        for label in ("CE", "LAA"):
            pool = sorted((row for row in training
                           if row["center_id"] == center and row["label"] == label),
                          key=lambda row: row["image_id"])
            if pool:
                chosen.append(rng.choice(pool))
    canvas = Image.new("RGB", (6 * 260, 4 * 290), "#f3f4f5")
    draw = ImageDraw.Draw(canvas)
    for index, row in enumerate(chosen):
        col, line = index % 6, index // 6
        x0, y0 = col * 260, line * 290
        with Image.open(ROOT / row["archivo_reducido"]) as image:
            x, y = int(row["x"]), int(row["y"])
            tile = image.convert("RGB").crop((x, y, x + TILE, y + TILE))
        canvas.paste(ImageOps.contain(tile, (250, 250)), (x0 + 5, y0 + 5))
        draw.text((x0 + 6, y0 + 263),
                  f"{row['image_id']} {row['label']} C{row['center_id']} "
                  f"{float(row['fraccion_candidata_tejido']):.0%}", fill="#16232e")
    canvas.save(SAMPLE, quality=88)
    print(f"{len(regions)} regiones válidas en "
          f"{sum(bool(group) for group in by_image.values())} imágenes; "
          f"{len(patient_totals)} pacientes con regiones; sin regiones: {no_regions}")
    print(f"Muestra de {len(chosen)} recortes de entrenamiento: {SAMPLE}")


if __name__ == "__main__":
    main()
