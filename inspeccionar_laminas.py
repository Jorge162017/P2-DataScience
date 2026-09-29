"""Inspección técnica por regiones de TIFF oficiales, sin cargar la lámina completa."""

import csv
import hashlib
from pathlib import Path

import imagecodecs
import numpy as np
import tifffile
import zarr


ROOT = Path(__file__).resolve().parent
SLIDES = ROOT / "datos/originales/train"
RESULTS = ROOT / "resultados"
PATCH = 128
PREVIEW = 256
GRID = 24


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def difference_fraction(rgb, background):
    delta = rgb.astype(np.float32) - background
    return float(np.mean(np.sum(delta * delta, axis=2) > 30**2))


def inspect(path, metadata):
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        height, width, channels = page.shape
        if channels != 3:
            raise ValueError(f"Se esperaban tres canales RGB: {path}")
        array = zarr.open(page.aszarr(), mode="r")
        patches = []
        for gy in range(GRID):
            y = round((height - PATCH) * (gy + 0.5) / GRID)
            for gx in range(GRID):
                x = round((width - PATCH) * (gx + 0.5) / GRID)
                crop = array[y:y + PATCH, x:x + PATCH, :]
                gray_std = float(np.std(crop.mean(axis=2)))
                patches.append((gray_std, x, y, crop))
        # Fondo aproximado de la lámina: mediana de las regiones más uniformes.
        # Evita tratar un fondo teñido como tejido solo por no ser blanco.
        low_texture = sorted(patches, key=lambda item: item[0])[:max(1, len(patches) // 5)]
        background = np.median(
            [item[3].mean(axis=(0, 1)) for item in low_texture], axis=0
        ).astype(np.float32)
        samples = [(difference_fraction(crop, background), std, x, y, crop)
                   for std, x, y, crop in patches]
        samples.sort(key=lambda item: (item[0] >= 0.25 and item[1] >= 8, item[0], item[1]), reverse=True)
        coverages = np.array([item[0] for item in samples])
        textured = np.array([item[1] >= 8 for item in samples])
        summary = {
            "image_id": path.stem,
            "label": metadata["label"],
            "patient_id": metadata["patient_id"],
            "center_id": metadata["center_id"],
            "width": width,
            "height": height,
            "tile_width": page.tilewidth,
            "tile_height": page.tilelength,
            "tiff_bytes": path.stat().st_size,
            "sha256": sha256(path),
            "sampled_regions": len(samples),
            "sample_patch_pixels": PATCH,
            "grid_size": GRID,
            "background_rgb_estimate": ",".join(str(round(float(channel))) for channel in background),
            "regions_25pct_color_difference": int(np.sum(coverages >= 0.25)),
            "regions_25pct_and_texture": int(np.sum((coverages >= 0.25) & textured)),
            "sampled_median_difference_fraction": round(float(np.median(coverages)), 4),
            "sampled_max_difference_fraction": round(float(coverages.max()), 4),
        }
        # Estas cuatro regiones sirven solo como vista técnica, no como muestra clínica.
        previews = []
        for _, _, x, y, _ in samples[:4]:
            px = min(max(0, x - (PREVIEW - PATCH) // 2), width - PREVIEW)
            py = min(max(0, y - (PREVIEW - PATCH) // 2), height - PREVIEW)
            previews.append(array[py:py + PREVIEW, px:px + PREVIEW, :])
        return summary, previews


def main():
    with (ROOT / "datos/train.csv").open(newline="", encoding="utf-8") as stream:
        metadata = {row["image_id"]: row for row in csv.DictReader(stream)}
    paths = sorted(SLIDES.glob("*.tif"))
    if not paths:
        raise SystemExit("No se encontraron TIFF oficiales en datos/originales/train")
    summaries = []
    previews = {}
    for path in paths:
        if path.stem not in metadata:
            raise ValueError(f"La lámina no está en train.csv: {path.name}")
        summary, patches = inspect(path, metadata[path.stem])
        summaries.append(summary)
        samples_dir = RESULTS / "figuras/muestras_por_lamina"
        samples_dir.mkdir(parents=True, exist_ok=True)
        (samples_dir / f"{path.stem}.png").write_bytes(imagecodecs.png_encode(np.concatenate(patches, axis=1)))
        preferred = {"CE": "509042_0", "LAA": "c5d171_0"}
        if summary["label"] not in previews or path.stem == preferred[summary["label"]]:
            previews[summary["label"]] = patches
        print(summary)

    output = RESULTS / "laminas_oficiales_piloto.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=summaries[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)

    if "CE" in previews and "LAA" in previews:
        margin = 8
        canvas = np.full((2 * PREVIEW + 3 * margin, 4 * PREVIEW + 5 * margin, 3), 245, dtype=np.uint8)
        for row_index, label in enumerate(("CE", "LAA")):
            for col_index, patch in enumerate(previews[label]):
                y = margin + row_index * (PREVIEW + margin)
                x = margin + col_index * (PREVIEW + margin)
                canvas[y:y + PREVIEW, x:x + PREVIEW] = patch
        figure = RESULTS / "figuras/laminas_oficiales_piloto.png"
        figure.parent.mkdir(parents=True, exist_ok=True)
        figure.write_bytes(imagecodecs.png_encode(canvas))
        print(f"Vista técnica: {figure} (fila 1 CE; fila 2 LAA)")
    print(f"Resumen: {output}")


if __name__ == "__main__":
    main()
