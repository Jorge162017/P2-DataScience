"""EDA visual reproducible de las 754 imágenes reducidas de STRIP AI.

Las medidas describen imágenes, no tejido clínicamente anotado. La máscara se
calcula en una vista de 280 px de ancho; las salidas no son etiquetas clínicas.
"""

import csv
import json
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from scipy import ndimage as ndi


SOURCE = ROOT / "datos/imagenes_reducidas.csv"
OUTPUT = ROOT / "resultados/eda_reducidas.csv"
REPORT = ROOT / "resultados/eda_reducidas_resumen.json"
FIGURES = ROOT / "resultados/figuras"
QC = FIGURES / "validacion_tejido"
WIDTH = 280
DISTANCE = 30.0
TEXTURE = 3.0
MIN_COMPONENT = 8
COLORS = {"CE": "#31688e", "LAA": "#d88631"}


def background_and_mask(rgb, distance_threshold=DISTANCE, texture_threshold=TEXTURE):
    """Detecta píxeles diferentes del fondo dominante y con textura local.

    El fondo se estima con el color modal cuantizado en la orilla de la imagen,
    usando solo píxeles de baja textura. Los componentes de menos de 8 píxeles
    de la vista reducida se consideran ruido. No se usa la etiqueta CE/LAA.
    """
    pixels = rgb.astype(np.float32)
    gray = pixels.mean(axis=2)
    mean = ndi.uniform_filter(gray, size=5, mode="reflect")
    sq = ndi.uniform_filter(gray * gray, size=5, mode="reflect")
    std = np.sqrt(np.maximum(sq - mean * mean, 0))
    height, width = gray.shape
    border = max(4, min(height, width) // 20)
    edge = np.zeros((height, width), dtype=bool)
    edge[:border] = edge[-border:] = True
    edge[:, :border] = edge[:, -border:] = True
    candidates = edge & (std < 5)
    if candidates.sum() < 100:
        candidates = edge
    quantized = (pixels[candidates].astype(np.uint8) // 16).astype(np.int32)
    codes = quantized[:, 0] * 256 + quantized[:, 1] * 16 + quantized[:, 2]
    mode = int(np.bincount(codes, minlength=4096).argmax())
    background_pixels = pixels[candidates][codes == mode]
    background = np.median(background_pixels, axis=0)
    distance = np.linalg.norm(pixels - background, axis=2)
    raw = (distance > distance_threshold) & (std > texture_threshold)
    components, count = ndi.label(raw)
    sizes = np.bincount(components.ravel())
    sizes[0] = 0
    mask = raw & (sizes[components] >= MIN_COMPONENT)
    return background, mask, std, float(background_pixels.shape[0] / candidates.sum())


def inspect(row):
    path = ROOT / row["archivo_reducido"]
    with Image.open(path) as image:
        preview = image.convert("RGB")
        preview.thumbnail((WIDTH, 20000), Image.Resampling.LANCZOS)
        rgb = np.asarray(preview)
    background, mask, texture, mode_share = background_and_mask(rgb)
    tissue = rgb[mask]
    mean_rgb = tissue.mean(axis=0) if len(tissue) else np.array([np.nan] * 3)
    gray = rgb.mean(axis=2)
    details = {
        "image_id": row["image_id"], "patient_id": row["patient_id"],
        "center_id": row["center_id"], "label": row["label"],
        "width": int(row["width"]), "height": int(row["height"]),
        "preview_width": rgb.shape[1], "preview_height": rgb.shape[0],
        "fraccion_candidata_tejido": round(float(mask.mean()), 5),
        "fondo_r": round(float(background[0]), 1),
        "fondo_g": round(float(background[1]), 1),
        "fondo_b": round(float(background[2]), 1),
        "fondo_moda_borde_fraccion": round(mode_share, 4),
        "tejido_r_media": round(float(mean_rgb[0]), 2),
        "tejido_g_media": round(float(mean_rgb[1]), 2),
        "tejido_b_media": round(float(mean_rgb[2]), 2),
        "tejido_gris_media": round(float(gray[mask].mean()), 2) if len(tissue) else None,
        "tejido_textura_mediana": round(float(np.median(texture[mask])), 2) if len(tissue) else None,
    }
    return details, preview, mask


def qc_indices(rows, results):
    rng = np.random.default_rng(22)
    selected = set()
    for center in sorted({row["center_id"] for row in rows}, key=int):
        for label in ("CE", "LAA"):
            pool = [i for i, row in enumerate(rows)
                    if row["center_id"] == center and row["label"] == label]
            selected.update(rng.choice(pool, size=min(2, len(pool)), replace=False).tolist())
    fractions = np.array([result["fraccion_candidata_tejido"] for result in results])
    selected.update(np.argsort(fractions)[:6].tolist())
    selected.update(np.argsort(fractions)[-6:].tolist())
    shares = np.array([result["fondo_moda_borde_fraccion"] for result in results])
    selected.update(np.argsort(shares)[:6].tolist())
    return sorted(selected)


def draw_qc(rows, results, selected):
    QC.mkdir(parents=True, exist_ok=True)
    for page_number, start in enumerate(range(0, len(selected), 8), 1):
        indices = selected[start:start + 8]
        sheet = Image.new("RGB", (1100, 1200), "#f4f5f6")
        draw = ImageDraw.Draw(sheet)
        for j, index in enumerate(indices):
            result, preview, mask = inspect(rows[index])
            x = (j % 2) * 550 + 10
            y = (j // 2) * 300 + 5
            width, height = preview.size
            original = ImageOps.contain(preview, (240, 255))
            overlay = np.asarray(preview).copy()
            overlay[mask] = (0.65 * overlay[mask] + 0.35 * np.array([0, 220, 150])).astype(np.uint8)
            overlay = ImageOps.contain(Image.fromarray(overlay), (240, 255))
            sheet.paste(original, (x, y + 28))
            sheet.paste(overlay, (x + 250, y + 28))
            draw.text((x, y + 4),
                      f"{result['image_id']} {result['label']} C{result['center_id']} "
                      f"mask={result['fraccion_candidata_tejido']:.1%} "
                      f"bg=({result['fondo_r']:.0f},{result['fondo_g']:.0f},{result['fondo_b']:.0f})",
                      fill="#17212b")
        sheet.save(QC / f"muestra_{page_number:02d}.jpg", quality=88)


def figures(results):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for label in ("CE", "LAA"):
        group = [r["fraccion_candidata_tejido"] for r in results if r["label"] == label]
        axes[0].hist(group, bins=np.linspace(0, 1, 21), alpha=.62, color=COLORS[label], label=label)
    axes[0].set(xlabel="Fracción de píxeles candidatos a tejido", ylabel="Imágenes",
                title="Cobertura estimada en las 754 imágenes")
    axes[0].legend(frameon=False)
    centers = sorted({r["center_id"] for r in results}, key=int)
    data = [[r["fraccion_candidata_tejido"] for r in results if r["center_id"] == c]
            for c in centers]
    axes[1].boxplot(data, tick_labels=centers, showfliers=False)
    axes[1].set(xlabel="Centro", ylabel="Fracción candidata a tejido",
                title="Variación entre centros")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "reducidas_cobertura_tejido.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for label in ("CE", "LAA"):
        group = [r for r in results if r["label"] == label]
        axes[0].scatter([r["width"] * r["height"] / 1e6 for r in group],
                        [r["fraccion_candidata_tejido"] for r in group],
                        s=14, alpha=.35, label=label, color=COLORS[label])
        axes[1].scatter([r["tejido_gris_media"] for r in group],
                        [r["tejido_textura_mediana"] for r in group],
                        s=14, alpha=.35, label=label, color=COLORS[label])
    axes[0].set(xlabel="Resolución PNG (megapíxeles)", ylabel="Fracción candidata a tejido",
                title="Tamaño y contenido estimado")
    axes[1].set(xlabel="Intensidad gris media candidata", ylabel="Textura local mediana",
                title="Variación técnica de color y textura")
    for ax in axes:
        ax.legend(frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "reducidas_color_textura.png", dpi=170)
    plt.close(fig)


def main():
    with SOURCE.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 754 or len({row["image_id"] for row in rows}) != 754:
        raise ValueError("El manifiesto debe contener las 754 imágenes únicas")
    results = []
    for index, row in enumerate(rows):
        result, _, _ = inspect(row)
        results.append(result)
        if (index + 1) % 100 == 0:
            print(f"Procesadas {index + 1}/{len(rows)}", flush=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=results[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    fractions = np.array([r["fraccion_candidata_tejido"] for r in results])
    selected = qc_indices(rows, results)
    draw_qc(rows, results, selected)
    figures(results)
    summary = {
        "imagenes": len(results),
        "pacientes": len({r["patient_id"] for r in results}),
        "clases_imagenes": dict(Counter(r["label"] for r in results)),
        "centros": len({r["center_id"] for r in results}),
        "ancho_analisis_px": WIDTH,
        "metodo": {"distancia_rgb_minima": DISTANCE, "textura_local_minima": TEXTURE,
                   "componente_minimo_px": MIN_COMPONENT},
        "fraccion_candidata_cuantiles": {str(q): round(float(np.quantile(fractions, q)), 4)
                                         for q in (0, .05, .25, .5, .75, .95, 1)},
        "imagenes_casi_vacias_menos_1pct": int((fractions < .01).sum()),
        "imagenes_casi_llenas_mas_95pct": int((fractions > .95).sum()),
        "imagenes_revision_visual": len(selected),
        "seleccion_revision_indices": selected,
    }
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
