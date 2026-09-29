"""Audita sensibilidad de la máscara y compara la regla de la primera fase."""

import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analizar_reducidas import ROOT, WIDTH, background_and_mask


OUTPUT = ROOT / "resultados/validacion_metodo_tejido.csv"
REPORT = ROOT / "resultados/validacion_metodo_tejido.json"


def old_mask(rgb):
    pixels = rgb.astype(np.float32)
    gray = pixels @ np.array([.299, .587, .114], dtype=np.float32)
    maximum = pixels.max(axis=2)
    saturation = np.divide(maximum - pixels.min(axis=2), maximum,
                           out=np.zeros_like(maximum), where=maximum != 0)
    return (gray < 230) | (saturation > .10)


def iou(first, second):
    union = np.count_nonzero(first | second)
    return float(np.count_nonzero(first & second) / union) if union else 1.0


def main():
    with (ROOT / "datos/imagenes_reducidas.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 754:
        raise ValueError("Faltan imágenes reducidas")
    results = []
    for index, row in enumerate(rows):
        with Image.open(ROOT / row["archivo_reducido"]) as image:
            preview = image.convert("RGB")
            preview.thumbnail((WIDTH, 20000), Image.Resampling.LANCZOS)
            rgb = np.asarray(preview)
        _, base, _, _ = background_and_mask(rgb)
        _, permissive, _, _ = background_and_mask(rgb, 20, 2)
        _, strict, _, _ = background_and_mask(rgb, 40, 5)
        old = old_mask(rgb)
        results.append({
            "image_id": row["image_id"], "label": row["label"],
            "center_id": row["center_id"],
            "fraccion_nueva": round(float(base.mean()), 5),
            "fraccion_anterior": round(float(old.mean()), 5),
            "fraccion_permisiva": round(float(permissive.mean()), 5),
            "fraccion_estricta": round(float(strict.mean()), 5),
            "iou_permisiva": round(iou(base, permissive), 4),
            "iou_estricta": round(iou(base, strict), 4),
            "exceso_anterior_fraccion": round(float(np.mean(old & ~base)), 5),
        })
        if (index + 1) % 200 == 0:
            print(f"Auditadas {index + 1}/754", flush=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=results[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    current = np.array([r["fraccion_nueva"] for r in results])
    old = np.array([r["fraccion_anterior"] for r in results])
    loose = np.array([r["fraccion_permisiva"] for r in results])
    strict = np.array([r["fraccion_estricta"] for r in results])
    report = {
        "imagenes": len(results),
        "umbrales": {"base": "distancia RGB >30, textura >3",
                     "permisivo": "distancia RGB >20, textura >2",
                     "estricto": "distancia RGB >40, textura >5"},
        "mediana_fraccion": {"regla_primera_fase": round(float(np.median(old)), 4),
                             "permisivo": round(float(np.median(loose)), 4),
                             "base": round(float(np.median(current)), 4),
                             "estricto": round(float(np.median(strict)), 4)},
        "mediana_iou_con_base": {
            "permisivo": round(float(np.median([r["iou_permisiva"] for r in results])), 4),
            "estricto": round(float(np.median([r["iou_estricta"] for r in results])), 4),
        },
        "anterior_excede_base_10_puntos_en_imagenes": int(np.sum(old - current > .10)),
        "anterior_excede_base_25_puntos_en_imagenes": int(np.sum(old - current > .25)),
        "imagenes_con_cambio_base_estricto_mas_5_puntos": int(np.sum(current - strict > .05)),
        "imagenes_con_cambio_permisivo_base_mas_5_puntos": int(np.sum(loose - current > .05)),
        "nota": "La comparación de reglas y umbrales no es exactitud clínica; faltan máscaras manuales de referencia.",
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    example = next(row for row in rows if row["image_id"] == "caf901_0")
    with Image.open(ROOT / example["archivo_reducido"]) as image:
        preview = image.convert("RGB")
        preview.thumbnail((WIDTH, 20000), Image.Resampling.LANCZOS)
        rgb = np.asarray(preview)
    _, new, _, _ = background_and_mask(rgb)
    old = old_mask(rgb)
    h, w = rgb.shape[:2]
    canvas = Image.new("RGB", (3 * w + 40, h + 45), "white")
    draw = ImageDraw.Draw(canvas)
    for x, title, panel in ((10, "Imagen", Image.fromarray(rgb)),
                            (w + 20, f"Regla anterior: {old.mean():.1%}",
                             Image.fromarray(np.uint8(old) * 255)),
                            (2 * w + 30, f"Método nuevo: {new.mean():.1%}",
                             Image.fromarray(np.uint8(new) * 255))):
        draw.text((x, 10), title, fill="black")
        canvas.paste(panel.convert("RGB"), (x, 35))
        draw.rectangle((x, 35, x + w - 1, 35 + h - 1), outline="black", width=1)
    canvas.save(ROOT / "resultados/figuras/reducidas_comparacion_mascaras.png")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
