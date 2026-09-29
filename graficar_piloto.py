"""Crea figuras descriptivas de las láminas originales ya descargadas."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import pandas as pd


COLORS = {"CE": "#31688e", "LAA": "#d88631"}
SOURCE = ROOT / "resultados/laminas_oficiales_piloto.csv"
FIGURES = ROOT / "resultados/figuras"


def main():
    data = pd.read_csv(SOURCE, dtype={"image_id": str, "label": str, "center_id": str})
    if data.empty:
        raise SystemExit("Aún no hay láminas inspeccionadas")
    FIGURES.mkdir(parents=True, exist_ok=True)
    centers = sorted(data.center_id.unique(), key=int)

    counts = pd.crosstab(data.center_id, data.label).reindex(centers, fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(centers))
    ce = counts.get("CE", pd.Series(0, index=centers))
    laa = counts.get("LAA", pd.Series(0, index=centers))
    ax.bar(x, ce, label="CE", color=COLORS["CE"])
    ax.bar(x, laa, bottom=ce, label="LAA", color=COLORS["LAA"])
    ax.set_xticks(list(x), centers)
    ax.set_xlabel("Centro")
    ax.set_ylabel("Pacientes con lámina descargada")
    ax.set_title("Cobertura actual de la muestra oficial")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "piloto_composicion.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    data["megapixeles"] = data.width * data.height / 1e6
    data["mib"] = data.tiff_bytes / 1024**2
    for label, group in data.groupby("label"):
        ax.scatter(group.megapixeles, group.mib, label=label, color=COLORS[label], s=55, alpha=0.85)
    ax.set_xlabel("Resolución (millones de píxeles)")
    ax.set_ylabel("Tamaño del TIFF (MiB)")
    ax.set_title("Variación de tamaño entre las láminas descargadas")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "piloto_tamanos.png", dpi=180)
    plt.close(fig)

    data = data.sort_values(["center_id", "label", "image_id"], key=lambda col: col.map(int) if col.name == "center_id" else col)
    fig, ax = plt.subplots(figsize=(9, max(4, 0.34 * len(data) + 1.5)))
    ax.barh(data.image_id, data.regions_25pct_and_texture / data.sampled_regions * 100,
            color=data.label.map(COLORS))
    ax.invert_yaxis()
    ax.set_xlabel("Regiones candidatas con color diferente al fondo y textura (%)")
    ax.set_title(f"Cuadrícula de {data.grid_size.iloc[0]} × {data.grid_size.iloc[0]} "
                 f"regiones de {data.sample_patch_pixels.iloc[0]} × "
                 f"{data.sample_patch_pixels.iloc[0]} px por lámina")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.text(0.16, 0.02, "Cribado técnico sobre regiones muestreadas; no estima tejido en toda la lámina.",
             fontsize=9, color="#555555")
    fig.savefig(FIGURES / "piloto_regiones.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Figuras guardadas en {FIGURES}")


if __name__ == "__main__":
    main()
