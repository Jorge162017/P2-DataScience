"""EDA reproducible del tema 22. Solo escribe dentro del proyecto nuevo."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import laplace

ROOT = Path(__file__).resolve().parent
CLASES = ["CE", "LAA"]
COLORES = ["#167D9A", "#D97838"]
METRICAS = ["tejido_fraccion", "nitidez_laplaciano", "gris_media", "gris_std",
            "entropia_gris", "r_tejido", "g_tejido", "b_tejido"]
PARAMETROS = {"lado_tile": 128, "gris_umbral": 230, "saturacion_umbral": 0.10,
              "tejido_minimo": 0.25, "nitidez_minima": 2.0}


def guardar_tabla(df, nombre, root=ROOT, index=False):
    path = root / "resultados/tablas" / f"{nombre}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)


def guardar_figura(fig, nombre, root=ROOT):
    path = root / "resultados/figuras" / f"{nombre}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def frecuencias(serie):
    counts = serie.value_counts(dropna=False).sort_index()
    return pd.DataFrame({"frecuencia": counts, "proporcion": counts / len(serie),
                         "porcentaje": counts / len(serie) * 100})


def marcar_atipicos(serie):
    """Regla descriptiva de Tukey; señala valores, no los elimina."""
    q1, q3 = serie.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (serie < q1 - 1.5 * iqr) | (serie > q3 + 1.5 * iqr)


def cargar_metadatos(path):
    required = ["image_id", "center_id", "patient_id", "image_num", "label"]
    raw = pd.read_csv(path, dtype="string")
    if set(raw.columns) != set(required):
        raise ValueError(f"Se esperan estas cinco columnas: {required}")
    df = raw.copy()
    for col in required:
        df[col] = df[col].str.strip().replace("", pd.NA)
    df["label"] = df["label"].str.upper()
    quality = pd.DataFrame({"variable": required,
        "nulos_originales": [int(raw[c].isna().sum()) for c in required],
        "nulos_normalizados": [int(df[c].isna().sum()) for c in required],
        "celdas_normalizadas": [int((raw[c].fillna("") != df[c].fillna("")).sum()) for c in required]})
    if df.isna().any().any():
        raise ValueError("Hay valores faltantes: revisarlos antes de continuar; no se imputan IDs ni etiquetas.")
    duplicates = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()
    if df.image_id.duplicated().any():
        raise ValueError("Un image_id tiene registros conflictivos.")
    if not df.label.isin(CLASES).all():
        raise ValueError("Hay etiquetas distintas de CE/LAA.")
    for col in ["center_id", "image_num"]:
        numeric = pd.to_numeric(df[col], errors="raise")
        if ((numeric % 1 != 0) | (numeric < (1 if col == "center_id" else 0))).any():
            raise ValueError(f"Valores inválidos en {col}")
        df[col] = numeric.astype("int64")
    expected = df.patient_id + "_" + df.image_num.astype("string")
    if not df.image_id.eq(expected).all():
        raise ValueError("image_id no coincide con patient_id + image_num.")
    if df.groupby("patient_id")[["label", "center_id"]].nunique().gt(1).any().any():
        raise ValueError("Etiología o centro inconsistentes para un paciente.")
    return df, quality, duplicates


def analizar_metadatos(root=ROOT):
    df, quality, duplicates = cargar_metadatos(root / "datos/train.csv")
    patients = df.groupby("patient_id", as_index=False).agg(
        label=("label", "first"), center_id=("center_id", "first"),
        n_imagenes=("image_id", "size"))
    patients["atipico_iqr"] = marcar_atipicos(patients.n_imagenes)
    guardar_tabla(df, "metadatos_limpios", root)
    guardar_tabla(quality, "calidad_metadatos", root)
    guardar_tabla(patients, "pacientes", root)
    guardar_tabla(patients[patients.atipico_iqr], "pacientes_atipicos_iqr", root)
    for col in ["label", "center_id", "image_num"]:
        guardar_tabla(frecuencias(df[col]), f"frecuencia_{col}_imagenes", root, index=True)
    guardar_tabla(frecuencias(patients.label), "frecuencia_label_pacientes", root, index=True)
    guardar_tabla(frecuencias(patients.n_imagenes), "frecuencia_n_imagenes_paciente", root, index=True)
    guardar_tabla(patients[["n_imagenes"]].describe().T, "resumen_numerico_pacientes", root, index=True)
    guardar_tabla(patients.groupby("label").n_imagenes.describe(), "imagenes_paciente_por_clase", root, index=True)
    centers = pd.crosstab(patients.center_id, patients.label).reindex(columns=CLASES, fill_value=0)
    centers_prop = centers.div(centers.sum(axis=1), axis=0)
    guardar_tabla(centers, "centro_clase_pacientes", root, index=True)
    guardar_tabla(centers_prop, "centro_clase_proporciones", root, index=True)
    guardar_tabla(pd.crosstab(df.center_id, df.label).reindex(columns=CLASES, fill_value=0),
                  "centro_clase_imagenes", root, index=True)
    guardar_tabla(pd.crosstab(patients.n_imagenes, patients.label), "n_imagenes_clase", root, index=True)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, series, title in zip(axes, [df.label, patients.label], ["Por imagen", "Por paciente"]):
        counts = series.value_counts().reindex(CLASES, fill_value=0)
        bars = ax.bar(CLASES, counts, color=COLORES)
        ax.bar_label(bars, labels=[f"{n}\n{n/len(series):.1%}" for n in counts], padding=4)
        ax.set(title=f"{title} (n={len(series)})", ylabel="Frecuencia", ylim=(0, counts.max()*1.25))
    guardar_figura(fig, "01_balance_clases", root)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    centers.plot.bar(stacked=True, ax=axes[0], color=COLORES, rot=0)
    centers_prop.plot.bar(stacked=True, ax=axes[1], color=COLORES, rot=0)
    axes[0].set(title="Composición por centro", ylabel="Pacientes", xlabel="Centro (código nominal)")
    axes[1].set(title="Proporciones dentro de cada centro", ylabel="Proporción de pacientes", xlabel="Centro")
    for i, n in enumerate(centers.sum(axis=1)):
        axes[1].text(i, 1.02, f"n={n}", ha="center", fontsize=7)
    axes[1].set_ylim(0, 1.13)
    guardar_figura(fig, "02_centro_clase", root)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].hist(patients.n_imagenes, bins=np.arange(0.5, patients.n_imagenes.max()+1.5), color=COLORES[0], rwidth=.8)
    axes[0].set(title="Imágenes por paciente", xlabel="Número de imágenes", ylabel="Pacientes",
                xticks=range(1, int(patients.n_imagenes.max())+1))
    axes[1].boxplot([patients.loc[patients.label.eq(c), "n_imagenes"] for c in CLASES], tick_labels=CLASES)
    axes[1].set(title="Repeticiones por clase; atípicos visibles", ylabel="Imágenes por paciente")
    guardar_figura(fig, "03_imagenes_por_paciente", root)
    summary = {"observaciones": len(df), "variables_originales": len(df.columns),
               "pacientes": len(patients), "centros": int(df.center_id.nunique()),
               "clases_imagenes": {str(k): int(v) for k,v in df.label.value_counts().items()},
               "clases_pacientes": {str(k): int(v) for k,v in patients.label.value_counts().items()},
               "nulos": int(df.isna().sum().sum()), "duplicados_eliminados": duplicates,
               "pacientes_multiples_imagenes": int(patients.n_imagenes.gt(1).sum()),
               "max_imagenes_paciente": int(patients.n_imagenes.max())}
    return df, patients, summary


def mascara_tejido(rgb, gris_umbral=230, saturacion_umbral=.10):
    arr = rgb.astype(np.float64)
    gray = arr @ np.array([.299, .587, .114])
    maximum = arr.max(axis=2)
    saturation = np.divide(maximum-arr.min(axis=2), maximum,
                           out=np.zeros_like(maximum), where=maximum != 0)
    return (gray < gris_umbral) | (saturation > saturacion_umbral)


def medir_imagen(rgb):
    gray = rgb.astype(np.float64) @ np.array([.299, .587, .114])
    mask = mascara_tejido(rgb, PARAMETROS["gris_umbral"], PARAMETROS["saturacion_umbral"])
    hist = np.bincount(np.clip(np.rint(gray), 0, 255).astype(np.uint8).ravel(), minlength=256)
    p = hist[hist > 0] / gray.size
    tissue = rgb[mask]
    means = tissue.mean(axis=0) if len(tissue) else np.full(3, np.nan)
    return {"tejido_fraccion": float(mask.mean()),
            "nitidez_laplaciano": float(laplace(gray, mode="reflect").var()),
            "gris_media": float(gray.mean()), "gris_std": float(gray.std()),
            "entropia_gris": float(-(p * np.log2(p)).sum()),
            **{f"{c}_tejido": float(v) for c,v in zip("rgb", means)}}


def extraer_tiles(rgb, lado=128):
    """Cuadrícula determinista sin solapamientos; se omiten bordes incompletos."""
    rows = []
    for y in range(0, rgb.shape[0]-lado+1, lado):
        for x in range(0, rgb.shape[1]-lado+1, lado):
            metrics = medir_imagen(rgb[y:y+lado, x:x+lado])
            enough = metrics["tejido_fraccion"] >= PARAMETROS["tejido_minimo"]
            sharp = metrics["nitidez_laplaciano"] >= PARAMETROS["nitidez_minima"]
            rows.append({"x": x, "y": y, "lado": lado, **metrics,
                         "aceptado": enough and sharp,
                         "motivo": "aceptado" if enough and sharp else ("poco_tejido" if not enough else "baja_nitidez")})
    return pd.DataFrame(rows, columns=["x", "y", "lado", *METRICAS, "aceptado", "motivo"])


def analizar_imagenes(df, root=ROOT):
    manifest = json.loads((root / "datos/procedencia.json").read_text())
    inventory, tiles_list, arrays, sensitivity = [], [], {}, []
    labels = df.set_index("image_id")
    for entry in manifest["archivos"]:
        if entry["tipo"] == "metadatos":
            continue
        path, iid = root / entry["archivo"], entry["image_id"]
        with Image.open(path) as im:
            # Los archivos locales son pequeños. No se desactiva la protección de Pillow.
            original_mode = im.mode
            rgb = np.asarray(im.convert("RGB"))
        arrays[iid] = rgb
        known = iid in labels.index
        row = {"image_id": iid, "archivo": entry["archivo"], "preparacion": entry["tipo"],
               "label": labels.loc[iid, "label"] if known else pd.NA,
               "patient_id": labels.loc[iid, "patient_id"] if known else pd.NA,
               "center_id": int(labels.loc[iid, "center_id"]) if known else pd.NA,
               "estado_etiqueta": "coincide_con_csv" if known else "sin_correspondencia_en_csv",
               "ancho_px": rgb.shape[1], "alto_px": rgb.shape[0], "modo_original": original_mode,
               "tamano_mb": path.stat().st_size / 1_000_000, **medir_imagen(rgb)}
        tiles = extraer_tiles(rgb, PARAMETROS["lado_tile"])
        for col in ["image_id", "preparacion", "label", "patient_id"]:
            tiles[col] = row[col]
        row["tiles_candidatos"] = len(tiles)
        row["tiles_aceptados"] = int(tiles.aceptado.sum())
        row["tiles_rechazados"] = len(tiles)-row["tiles_aceptados"]
        row["pixeles_borde_omitidos"] = int(rgb.shape[0]*rgb.shape[1]-len(tiles)*PARAMETROS["lado_tile"]**2)
        inventory.append(row)
        tiles_list.append(tiles)
        for threshold in [.10, .25, .50]:
            sensitivity.append({"image_id": iid, "min_tejido": threshold,
                "tiles_aceptados": int(((tiles.tejido_fraccion >= threshold) &
                                        (tiles.nitidez_laplaciano >= PARAMETROS["nitidez_minima"])).sum()),
                "tiles_candidatos": len(tiles)})
    inv = pd.DataFrame(inventory)
    tiles = pd.concat(tiles_list, ignore_index=True)
    accepted = tiles[tiles.aceptado].copy()
    # IQR dentro de la imagen; no convertir regiones correlacionadas en pacientes.
    for metric in ["nitidez_laplaciano", "entropia_gris", "tejido_fraccion"]:
        accepted[f"atipico_{metric}"] = accepted.groupby("image_id")[metric].transform(marcar_atipicos)
    guardar_tabla(inv, "inventario_imagenes", root)
    guardar_tabla(tiles, "tiles_todos", root)
    guardar_tabla(accepted, "tiles_aceptados", root)
    guardar_tabla(pd.DataFrame(sensitivity), "sensibilidad_filtro_tejido", root)
    guardar_tabla(pd.crosstab(tiles.image_id, tiles.motivo), "control_tiles", root, index=True)
    guardar_tabla(inv[METRICAS + ["ancho_px", "alto_px", "tamano_mb"]].describe().T,
                  "resumen_imagenes", root, index=True)
    guardar_tabla(accepted.groupby("image_id")[METRICAS].agg(["count", "mean", "std", "min", "median", "max"]),
                  "resumen_tiles_por_imagen", root, index=True)
    flag_cols = [c for c in accepted if c.startswith("atipico_")]
    guardar_tabla(accepted[accepted[flag_cols].any(axis=1)], "tiles_atipicos_iqr", root)
    guardar_tabla(inv[inv.label.notna()].groupby("label")[METRICAS].agg(["count", "mean", "min", "max"]),
                  "descriptivo_clase_tres_recortes", root, index=True)

    fig, axes = plt.subplots(len(inv), 2, figsize=(8, len(inv)*2.4), squeeze=False)
    for (_, row), axs in zip(inv.iterrows(), axes):
        rgb = arrays[row.image_id]
        label = row.label if pd.notna(row.label) else "sin etiqueta"
        axs[0].imshow(rgb)
        axs[0].set_title(f"{row.image_id} · {label} · {row.preparacion}", fontsize=9)
        axs[1].imshow(mascara_tejido(rgb), cmap="gray", vmin=0, vmax=1)
        axs[1].set_title(f"Máscara aproximada: {row.tejido_fraccion:.1%}", fontsize=9)
        for ax in axs: ax.axis("off")
    guardar_figura(fig, "04_imagenes_y_mascaras", root)

    fig, axes = plt.subplots(len(inv), 4, figsize=(10, len(inv)*2), squeeze=False)
    for (_, row), axs in zip(inv.iterrows(), axes):
        group = accepted[accepted.image_id.eq(row.image_id)].sort_values("tejido_fraccion")
        indices = np.linspace(0, len(group)-1, min(4,len(group)), dtype=int)
        for ax in axs: ax.axis("off")
        for ax, idx in zip(axs, indices):
            tile = group.iloc[idx]
            x, y, side = int(tile.x), int(tile.y), int(tile.lado)
            ax.imshow(arrays[row.image_id][y:y+side, x:x+side])
            ax.set_title(f"{row.image_id}\n({x},{y}) · tejido {tile.tejido_fraccion:.0%}", fontsize=8)
    guardar_figura(fig, "05_mosaico_tiles", root)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, metric, title in zip(axes, ["nitidez_laplaciano", "entropia_gris"],
                                  ["Varianza del Laplaciano", "Entropía de gris (bits)"]):
        groups = [(iid, g[metric].to_numpy()) for iid,g in accepted.groupby("image_id")]
        ax.boxplot([v for _,v in groups], tick_labels=[i for i,_ in groups], showfliers=True)
        ax.tick_params(axis="x", rotation=40)
        ax.set(title=title, xlabel="Imagen; cada punto atípico es un tile")
    guardar_figura(fig, "06_cajas_por_imagen", root)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for ax, metric in zip(axes.flat, ["tejido_fraccion", "gris_media", "entropia_gris", "nitidez_laplaciano"]):
        values = accepted[metric].dropna()
        bins = np.histogram_bin_edges(values, bins=20)
        for group, g in accepted.groupby("preparacion"):
            ax.hist(g[metric], bins=bins, histtype="step", linewidth=1.8, label=f"{group} (tiles={len(g)})")
        ax.set(xlabel=metric, ylabel="Tiles", title="Distribución descriptiva; distinta preparación")
        ax.legend(fontsize=7)
    guardar_figura(fig, "07_histogramas_tiles", root)

    fig, ax = plt.subplots(figsize=(8, 5))
    for iid, group in accepted.groupby("image_id"):
        ax.scatter(group.tejido_fraccion, group.entropia_gris, s=14, alpha=.55, label=iid)
    ax.set(xlabel="Fracción aproximada de tejido", ylabel="Entropía de gris (bits)",
           title="Relación entre contenido y textura; tiles agrupados por imagen")
    ax.legend(fontsize=8)
    guardar_figura(fig, "08_dispersion_tejido_entropia", root)

    # Correlaciones por imagen: no mezclar preparación, pacientes ni etiquetas.
    corr_cols = ["tejido_fraccion", "nitidez_laplaciano", "entropia_gris", "r_tejido", "g_tejido", "b_tejido"]
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    for ax, (iid, group) in zip(axes.flat, accepted.groupby("image_id")):
        corr = group[corr_cols].corr(method="spearman")
        guardar_tabla(corr, f"correlacion_spearman_{iid}", root, index=True)
        im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set(xticks=range(len(corr_cols)), yticks=range(len(corr_cols)),
               xticklabels=corr_cols, yticklabels=corr_cols, title=f"{iid} (tiles={len(group)})")
        ax.tick_params(axis="x", rotation=65, labelsize=7)
        ax.tick_params(axis="y", labelsize=7)
        for i in range(len(corr_cols)):
            for j in range(len(corr_cols)):
                val = corr.iloc[i,j]
                ax.text(j,i,f"{val:.2f}" if pd.notna(val) else "NA",ha="center",va="center",fontsize=6,
                        color="white" if abs(val) > .65 else "black")
        fig.colorbar(im, ax=ax, fraction=.046)
    guardar_figura(fig, "09_correlaciones_por_imagen", root)

    fig, ax = plt.subplots(figsize=(8, 4))
    sens = pd.DataFrame(sensitivity)
    for iid, group in sens.groupby("image_id"):
        ax.plot(group.min_tejido, group.tiles_aceptados / group.tiles_candidatos, "o-", label=iid)
    ax.set(xlabel="Mínimo de tejido requerido", ylabel="Proporción de tiles aceptados",
           title="Sensibilidad al filtro de tejido", xticks=[.10,.25,.50], ylim=(0,1.05))
    ax.legend(fontsize=8)
    guardar_figura(fig, "10_sensibilidad_filtro", root)

    matched = inv[inv.label.notna()]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, metric in zip(axes, ["tejido_fraccion", "nitidez_laplaciano", "entropia_gris"]):
        for _, row in matched.iterrows():
            x = CLASES.index(row.label)
            ax.scatter(x, row[metric], color=COLORES[x], s=45)
            ax.annotate(row.image_id, (x,row[metric]), xytext=(4,5), textcoords="offset points", fontsize=7)
        ax.set(xticks=[0,1], xticklabels=["CE (n=2)", "LAA (n=1)"], xlim=(-.4,1.5), ylabel=metric)
    fig.suptitle("Tres recortes etiquetados: puntos individuales, sin inferencia poblacional", fontsize=10)
    guardar_figura(fig, "11_tres_recortes_etiquetados", root)
    return inv, tiles, accepted


def redactar_hallazgos(summary, patients, inv, tiles, accepted, root=ROOT):
    """Notas calculadas para el notebook; no constituye el informe final."""
    total, npat = summary["observaciones"], summary["pacientes"]
    ce = summary["clases_imagenes"]["CE"]
    cep = summary["clases_pacientes"]["CE"]
    centers = pd.crosstab(patients.center_id, patients.label)
    prop = centers.CE / centers.sum(axis=1)
    unknown = inv[inv.label.isna()].image_id.tolist()
    matched = inv[inv.label.notna()]
    count_atypical = int(accepted[[c for c in accepted if c.startswith("atipico_")]].any(axis=1).sum())
    text = f"""# Hallazgos calculados del EDA

## Metadatos y unidad de análisis

- Se analizaron **{total} registros, {summary['variables_originales']} variables, {npat} pacientes y {summary['centros']} centros**.
- Por imagen: CE **{ce} ({ce/total:.2%})** y LAA **{total-ce} ({(total-ce)/total:.2%})**. Por paciente: CE **{cep} ({cep/npat:.2%})** y LAA **{npat-cep} ({(npat-cep)/npat:.2%})**. Existe desbalance descriptivo; la frecuencia de esta muestra no es prevalencia poblacional.
- Hay **{summary['pacientes_multiples_imagenes']} pacientes con más de una imagen**, hasta {summary['max_imagenes_paciente']} imágenes. Las observaciones del mismo paciente no son independientes. Una eventual división para modelos debe agrupar por paciente.
- Se encontraron **{summary['nulos']} nulos** después de normalizar y se eliminaron **{summary['duplicados_eliminados']} duplicados exactos**. No se imputaron etiquetas ni identificadores. Los originales se conservan.
- Los códigos de centro e identificadores no son medidas clínicas continuas: no se interpretan promedios ni correlaciones numéricas de sus códigos.

## Relaciones entre variables

- La proporción CE por paciente va de **{prop.min():.2%} (centro {prop.idxmin()})** a **{prop.max():.2%} (centro {prop.idxmax()})**. La tabla de conteos permite valorar los distintos tamaños por centro. Es una asociación descriptiva compatible con diferencias de selección de casos; no demuestra que el centro cause la etiología.
- La mediana de imágenes por paciente es **{patients.n_imagenes.median():.0f}**. Q1 y Q3 son {patients.n_imagenes.quantile(.25):.0f} y {patients.n_imagenes.quantile(.75):.0f}; IQR=0 hace que la regla de Tukey marque las repeticiones como atípicas. Se conservan porque son observaciones válidas, no errores demostrados.

## Imágenes disponibles y calidad

- Se analizaron **{len(inv)} archivos derivados locales**, no las WSI originales. Solo **{len(matched)}** coinciden con `train.csv` (**{len(matched)/total:.2%}** de los identificadores del CSV); esos recortes corresponden a **{matched.patient_id.nunique()} pacientes**, todos del centro **{', '.join(str(x) for x in matched.center_id.unique())}**.
- Los identificadores **{', '.join(unknown)}** no aparecen en el CSV. Se mantienen sin etiqueta; no se les asigna CE, LAA, `Unknown` ni `Other` por apariencia o por similitud del nombre.
- Las vistas PNG y los recortes JPG tienen preparaciones y escalas distintas. No se considera que sean una muestra aleatoria ni comparable de toda la colección.
- La cuadrícula de 128 × 128 píxeles generó **{len(tiles)} tiles candidatos**, de los que **{len(accepted)}** superaron los filtros y **{len(tiles)-len(accepted)}** quedaron rechazados. No se insertan recortes de respaldo que incumplan los filtros. Las coordenadas corresponden a los archivos locales.
- La regla IQR dentro de cada imagen señala **{count_atypical} tiles aceptados** en al menos una métrica de calidad. Permanecen disponibles para revisión; no se borran por ser extremos. Los bordes, la compresión y las transiciones tejido/fondo pueden producir valores altos del Laplaciano.

## Alcance de las conclusiones

Se han caracterizado el desbalance, las repeticiones por paciente, la composición por centro y la variabilidad técnica de las imágenes disponibles. Las métricas de color, entropía y nitidez describen píxeles; no miden directamente eritrocitos, plaquetas o fibrina. Las correlaciones se calculan entre tiles dentro de cada imagen y no prueban relación causal ni poder diagnóstico.

**Dos pacientes CE y uno LAA, todos del mismo centro, no permiten establecer diferencias generales entre etiologías ni validar un clasificador.** No se entrenó un modelo ni se informan métricas predictivas. Más tiles no aumentan el número de pacientes.

Los siguientes pasos son ampliar la muestra con imágenes de identificación verificable y varios centros, documentar escala y tinción, revisar manualmente las máscaras y evaluar el efecto de los filtros. Si después se pide modelado, separar pacientes y revisar sesgo por centro. Estos resultados delimitan el alcance del análisis exploratorio.
"""
    (root / "resultados/hallazgos.md").write_text(text, encoding="utf-8")


def verificar_procedencia(root=ROOT):
    manifest = json.loads((root / "datos/procedencia.json").read_text())
    for entry in manifest["archivos"]:
        path = root / entry["archivo"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"El archivo cambió respecto de su procedencia: {path}")


def ejecutar(root=ROOT):
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold", "font.size": 10})
    verificar_procedencia(root)
    df, patients, summary = analizar_metadatos(root)
    inv, tiles, accepted = analizar_imagenes(df, root)
    summary.update({"imagenes_locales": len(inv), "imagenes_con_etiqueta": int(inv.label.notna().sum()),
                    "tiles_candidatos": len(tiles), "tiles_aceptados": len(accepted)})
    (root / "resultados/resumen.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n")
    versions = {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "matplotlib", "Pillow", "scipy"]}
    (root / "resultados/configuracion.json").write_text(json.dumps({"parametros": PARAMETROS, "versiones": versions}, indent=2)+"\n")
    redactar_hallazgos(summary, patients, inv, tiles, accepted, root)
    return {"metadatos": df, "pacientes": patients, "imagenes": inv,
            "tiles": tiles, "tiles_aceptados": accepted, "resumen": summary}


if __name__ == "__main__":
    result = ejecutar()
    print(json.dumps(result["resumen"], indent=2, ensure_ascii=False))
    print("Resultados guardados en", ROOT / "resultados")
