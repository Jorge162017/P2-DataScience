"""Aplicación local de exploración y clasificación del proyecto STRIP AI."""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request
from PIL import Image, UnidentifiedImageError
from sklearn.metrics import precision_recall_curve, roc_curve

from analizar_reducidas import WIDTH, background_and_mask
from extraer_caracteristicas import patch_features
from seleccionar_regiones import MAX_IOU, MAX_PER_IMAGE, MIN_TISSUE, TILE, fraction, iou, starts


ROOT = Path(__file__).resolve().parent
MODEL_FILES = {
    "Regresión logística": "regresion_logistica.joblib",
    "Bosque aleatorio": "bosque_aleatorio.joblib",
    "SVM RBF": "svm_rbf.joblib",
}
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


@lru_cache(maxsize=1)
def models():
    return {name: joblib.load(ROOT / "modelos" / filename)
            for name, filename in MODEL_FILES.items()}


@lru_cache(maxsize=1)
def overview():
    patients = pd.read_csv(ROOT / "datos/particion_pacientes.csv", dtype={"center_id": str})
    images = pd.read_csv(ROOT / "resultados/eda_reducidas.csv", dtype={"center_id": str})
    regions = pd.read_csv(ROOT / "resultados/resumen_seleccion_regiones.csv")
    return {
        "patients": int(len(patients)), "images": int(len(images)),
        "centers": int(patients.center_id.nunique()),
        "classes": patients.label.value_counts().to_dict(),
        "split": patients.groupby("particion").size().to_dict(),
        "by_center": [{"center": str(c), "label": label, "count": int(n)}
                      for (c, label), n in patients.groupby(["center_id", "label"]).size().items()],
        "features": [
            {"name": "Cobertura candidata de tejido", "value": round(float(images.fraccion_candidata_tejido.median()), 3), "unit": "mediana por imagen"},
            {"name": "Regiones seleccionadas", "value": int(regions.regiones_seleccionadas.sum()), "unit": "recortes de 256 × 256"},
            {"name": "Características del modelo", "value": 114, "unit": "color y textura agregadas por paciente"},
        ],
        "tissue_by_class": {label: [round(float(x), 4) for x in group.fraccion_candidata_tejido]
                            for label, group in images.groupby("label")},
    }


@lru_cache(maxsize=1)
def patient_features():
    data = pd.read_csv(ROOT / "resultados/modelos/caracteristicas_pacientes.csv",
                       dtype={"center_id": str, "patient_id": str})
    columns = [column for column in data.columns
               if column not in {"patient_id", "label", "center_id", "particion"}]
    if len(data) != 630 or len(columns) != 114:
        raise ValueError("La tabla de características de pacientes está incompleta.")
    return {
        "columns": columns,
        "rows": [{"label": row.label, "center": row.center_id,
                  "split": row.particion,
                  "values": [float(value) for value in row[columns]]}
                 for _, row in data.iterrows()],
    }


@lru_cache(maxsize=1)
def performance():
    metrics = pd.read_csv(ROOT / "resultados/modelos/metricas_modelos.csv")
    predictions = pd.read_csv(ROOT / "resultados/modelos/predicciones_pacientes.csv")
    curves = {}
    for name in MODEL_FILES:
        group = predictions[(predictions.modelo == name) & (predictions.particion == "prueba")]
        fpr, tpr, _ = roc_curve(group.real, group.probabilidad_laa)
        precision, recall, _ = precision_recall_curve(group.real, group.probabilidad_laa)
        curves[name] = {"roc": [[float(x), float(y)] for x, y in zip(fpr, tpr)],
                        "pr": [[float(x), float(y)] for x, y in zip(recall, precision)]}
    return {"metrics": metrics.to_dict(orient="records"), "curves": curves,
            "test_patients": 95, "selected_model": "Bosque aleatorio"}


def select_tiles(image):
    if image.width < TILE or image.height < TILE:
        raise ValueError("La imagen debe medir al menos 256 × 256 píxeles.")
    if image.width * image.height > 25_000_000:
        raise ValueError("La imagen es demasiado grande. Usa la versión PNG reducida.")
    preview = image.copy()
    preview.thumbnail((WIDTH, 20000), Image.Resampling.LANCZOS)
    _, mask, _, _ = background_and_mask(np.asarray(preview))
    candidates = [(fraction(mask, (x, y), image.size), x, y)
                  for y in starts(image.height) for x in starts(image.width)]
    candidates.sort(key=lambda item: (-item[0], item[2], item[1]))
    selected = []
    for coverage, x, y in candidates:
        if coverage < MIN_TISSUE:
            break
        if all(iou((x, y), (old_x, old_y)) <= MAX_IOU for _, old_x, old_y in selected):
            selected.append((coverage, x, y))
            if len(selected) == MAX_PER_IMAGE:
                break
    return selected


def extract_input_features(files):
    all_features = []
    used_images = 0
    for uploaded in files:
        if not uploaded.filename:
            continue
        if Path(uploaded.filename).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ValueError("Sube archivos PNG o JPG reducidos.")
        try:
            with Image.open(BytesIO(uploaded.read())) as opened:
                image = opened.convert("RGB")
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError("No se pudo abrir una de las imágenes.") from exc
        selected = select_tiles(image)
        if selected:
            used_images += 1
        for _, x, y in selected:
            all_features.append(patch_features(image.crop((x, y, x + TILE, y + TILE))))
    if not all_features:
        raise ValueError("No se detectaron regiones con suficiente tejido en las imágenes.")
    data = pd.DataFrame(all_features)
    means = data.mean().add_prefix("media_")
    deviations = data.std(ddof=0).add_prefix("desv_")
    return pd.concat([means, deviations]), len(all_features), used_images


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/overview")
def api_overview():
    return jsonify(overview())


@app.get("/api/performance")
def api_performance():
    return jsonify(performance())


@app.get("/api/features")
def api_features():
    return jsonify(patient_features())


@app.post("/api/predict")
def api_predict():
    files = [file for file in request.files.getlist("images") if file.filename]
    if not files or len(files) > 10:
        return jsonify({"error": "Selecciona entre 1 y 10 imágenes del mismo paciente."}), 400
    try:
        features, region_count, image_count = extract_input_features(files)
        outputs = []
        for name, artifact in models().items():
            columns = artifact["feature_columns"]
            if set(columns) != set(features.index):
                raise RuntimeError("Las características no coinciden con el modelo guardado.")
            row = pd.DataFrame([[features[column] for column in columns]], columns=columns)
            probability = float(artifact["pipeline"].predict_proba(row.to_numpy())[:, 1][0])
            outputs.append({"model": name, "class": "LAA" if probability >= .5 else "CE",
                            "probability_laa": probability})
        return jsonify({"predictions": outputs, "regions": region_count,
                        "images_with_regions": image_count, "images_uploaded": len(files)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("Falló la clasificación de una imagen")
        return jsonify({"error": "No se pudo completar la clasificación. Revisa la terminal de la app y vuelve a intentarlo."}), 500


@app.errorhandler(413)
def image_too_large(_error):
    return jsonify({"error": "Las imágenes superan el límite de 50 MB en total."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
