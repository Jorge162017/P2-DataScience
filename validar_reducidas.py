"""Valida y enlaza las 754 imágenes reducidas con train.csv.

La copia reducida usa idx_0000..idx_0753. Se comprueba el índice, la etiqueta,
la integridad PNG y, para los TIFF originales locales, la proporción de la lámina.
"""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "datos/reducidas/1120"
MANIFEST = ROOT / "datos/imagenes_reducidas.csv"
REPORT = ROOT / "resultados/validacion_reducidas.json"
Image.MAX_IMAGE_PIXELS = None  # Solo se leen las cabeceras de los TIFF gigantes.


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def main():
    with (ROOT / "datos/train.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 754:
        raise ValueError(f"Se esperaban 754 filas en train.csv, hay {len(rows)}")

    images = sorted(SOURCE.rglob("*.png"))
    if len(images) != len(rows):
        raise ValueError(f"Se esperaban {len(rows)} PNG, hay {len(images)}")
    expected = {SOURCE / row["label"] / f"idx_{index:04d}.png"
                for index, row in enumerate(rows)}
    if set(images) != expected:
        missing = [str(path) for path in sorted(expected - set(images))[:5]]
        extra = [str(path) for path in sorted(set(images) - expected)[:5]]
        raise ValueError(f"Archivos o etiquetas no coinciden con el CSV. Faltan: {missing}; extras: {extra}")

    checked = []
    for index, row in enumerate(rows):
        path = SOURCE / row["label"] / f"idx_{index:04d}.png"
        with Image.open(path) as image:
            if image.format != "PNG" or image.width not in (1100, 1120):
                raise ValueError(f"Formato o ancho inesperado: {path} {image.size} {image.format}")
            width, height = image.size
            image.verify()
        checked.append({**row, "archivo_reducido": str(path.relative_to(ROOT)),
                        "width": width, "height": height, "bytes": path.stat().st_size,
                        "sha256": digest(path)})

    originals = sorted((ROOT / "datos/originales/train").glob("*.tif"))
    by_id = {row["image_id"]: row for row in checked}
    ratios = []
    for path in originals:
        row = by_id.get(path.stem)
        if row is None:
            raise ValueError(f"TIFF original sin imagen reducida: {path.stem}")
        with Image.open(path) as image:
            direct_height = round(image.height * row["width"] / image.width)
            rotated_height = round(image.width * row["width"] / image.height)
        orientation = "directa" if abs(direct_height - row["height"]) <= abs(rotated_height - row["height"]) else "rotada"
        expected_height = direct_height if orientation == "directa" else rotated_height
        error = abs(expected_height - row["height"])
        ratios.append({"image_id": path.stem, "alto_esperado": expected_height,
                       "alto_png": row["height"], "diferencia_px": error,
                       "orientacion": orientation})
    if any(item["diferencia_px"] > 2 for item in ratios):
        raise ValueError("Al menos un PNG no conserva la proporción de su TIFF original")

    fields = ("image_id", "center_id", "patient_id", "image_num", "label",
              "archivo_reducido", "width", "height", "bytes", "sha256")
    with MANIFEST.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(checked)

    report = {
        "fuente": "https://www.kaggle.com/datasets/saurabhsawhney/mayo-resized-images",
        "descripcion": "Copia derivada; 746 PNG de ancho 1120 px y 8 de 1100 px; no son las láminas TIFF originales",
        "imagenes_png": len(checked),
        "pacientes": len({row["patient_id"] for row in checked}),
        "etiquetas": dict(Counter(row["label"] for row in checked)),
        "indices_unicos_y_etiquetas_coinciden": True,
        "anchos_png": dict(Counter(str(row["width"]) for row in checked)),
        "png_integridad_y_ancho_verificados": True,
        "tiff_originales_cotejados_por_proporcion": len(ratios),
        "orientaciones_cotejadas": dict(Counter(item["orientacion"] for item in ratios)),
        "max_diferencia_alto_px": max((item["diferencia_px"] for item in ratios), default=None),
        "ejemplos_cotejo": ratios[:5],
        "bytes_png": sum(row["bytes"] for row in checked),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Manifiesto: {MANIFEST}")


if __name__ == "__main__":
    main()
