"""Genera láminas de revisión para las siete imágenes con <1 % de tejido."""

import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from analizar_reducidas import ROOT, WIDTH, background_and_mask
from seleccionar_regiones import TILE, inspect


EDA = ROOT / "resultados/eda_reducidas.csv"
SPLIT = ROOT / "datos/particion_imagenes.csv"
OUT = ROOT / "resultados/figuras/revision_baja_cobertura"


def read(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    low = {row["image_id"] for row in read(EDA)
           if float(row["fraccion_candidata_tejido"]) < .01}
    rows = [row for row in read(SPLIT) if row["image_id"] in low]
    if len(rows) != 7:
        raise ValueError(f"Se esperaban siete imágenes: {len(rows)}")
    OUT.mkdir(parents=True, exist_ok=True)
    for page_number, start in enumerate(range(0, len(rows), 4), 1):
        canvas = Image.new("RGB", (1100, 4 * 300), "#f2f3f4")
        draw = ImageDraw.Draw(canvas)
        for j, row in enumerate(rows[start:start + 4]):
            path = ROOT / row["archivo_reducido"]
            candidates, selected, _ = inspect(row)
            coverage, x, y = candidates[0]
            with Image.open(path) as image:
                original = image.convert("RGB")
                tile = original.crop((x, y, x + TILE, y + TILE))
                preview = original.copy()
                preview.thumbnail((WIDTH, 20000), Image.Resampling.LANCZOS)
            _, mask, _, _ = background_and_mask(np.asarray(preview))
            preview_panel = ImageOps.contain(preview, (220, 250))
            mask_image = Image.fromarray(np.uint8(mask) * 255).convert("RGB")
            mask_panel = ImageOps.contain(mask_image, (220, 250))
            top = j * 300
            canvas.paste(preview_panel, (10, top + 35))
            canvas.paste(mask_panel, (240, top + 35))
            canvas.paste(tile, (480, top + 35))
            draw.text((10, top + 7),
                      f"{row['image_id']} | {row['particion']} | {row['label']} | "
                      f"mejor región: {coverage:.1%} | seleccionadas: {len(selected)}",
                      fill="#16232e")
            draw.text((755, top + 50), f"Recorte 256 x 256", fill="#16232e")
            draw.text((755, top + 75), f"x={x}, y={y}", fill="#16232e")
            draw.text((10, top + 285), "Izq: imagen completa   Centro: máscara   Der: mejor recorte",
                      fill="#4b5560")
        canvas.save(OUT / f"baja_cobertura_{page_number:02d}.jpg", quality=90)
    print(f"{len(rows)} imágenes revisables en {OUT}")


if __name__ == "__main__":
    main()
