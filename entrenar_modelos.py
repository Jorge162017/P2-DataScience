"""Ajusta tres clasificadores por paciente y evalúa la prueba una sola vez.

La selección del modelo usa validación; la búsqueda de hiperparámetros usa
únicamente validación cruzada dentro del entrenamiento.
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
os.environ.setdefault("MPLBACKEND", "Agg")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score,
                             average_precision_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


SOURCE = ROOT / "resultados/modelos/caracteristicas_pacientes.csv"
RESULTS = ROOT / "resultados/modelos"
FIGURES = ROOT / "resultados/figuras/modelos"
MODEL_DIR = ROOT / "modelos"
SEED = 22
POSITIVE = "LAA"
COLORS = {"Regresión logística": "#31688e", "Bosque aleatorio": "#d88631",
          "SVM RBF": "#6a51a3", "Mayoría CE": "#777777"}


def metrics(y_true, probabilities):
    prediction = (probabilities >= .5).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, prediction)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "average_precision": float(average_precision_score(y_true, probabilities)),
        "f1_laa": float(f1_score(y_true, prediction, zero_division=0)),
        "precision_laa": float(precision_score(y_true, prediction, zero_division=0)),
        "recall_laa": float(recall_score(y_true, prediction, zero_division=0)),
        "specificity_ce": float(recall_score(1 - y_true, 1 - prediction, zero_division=0)),
        "tn": int(confusion_matrix(y_true, prediction, labels=[0, 1])[0, 0]),
        "fp": int(confusion_matrix(y_true, prediction, labels=[0, 1])[0, 1]),
        "fn": int(confusion_matrix(y_true, prediction, labels=[0, 1])[1, 0]),
        "tp": int(confusion_matrix(y_true, prediction, labels=[0, 1])[1, 1]),
    }


def uncertainty(y, probability, repetitions=1000):
    rng = np.random.default_rng(SEED)
    ce = np.flatnonzero(y == 0)
    laa = np.flatnonzero(y == 1)
    aucs, balanced = [], []
    for _ in range(repetitions):
        sample = np.concatenate((rng.choice(ce, len(ce), replace=True),
                                 rng.choice(laa, len(laa), replace=True)))
        aucs.append(roc_auc_score(y[sample], probability[sample]))
        balanced.append(balanced_accuracy_score(y[sample], probability[sample] >= .5))
    return {"roc_auc_95pct": [float(value) for value in np.quantile(aucs, [.025, .975])],
            "balanced_accuracy_95pct": [float(value) for value in np.quantile(balanced, [.025, .975])]}


def charts(metric_rows, predictions, winner, test_y):
    FIGURES.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(metric_rows)
    names = list(COLORS)
    x = np.arange(len(names))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, metric, title in zip(axes, ("roc_auc", "balanced_accuracy"),
                                 ("AUC ROC", "Exactitud balanceada")):
        for offset, split, color in ((-.18, "validacion", "#6baed6"),
                                     (.18, "prueba", "#fdae6b")):
            values = [float(table[(table.modelo == name) & (table.particion == split)][metric].iloc[0])
                      for name in names]
            ax.bar(x + offset, values, width=.34, label=split, color=color)
        ax.set_xticks(x, [name.replace(" ", "\n") for name in names], fontsize=9)
        ax.set_ylim(0, 1)
        ax.set_title(title)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False)
    fig.suptitle("Comparación por paciente (modelo elegido con validación)")
    fig.tight_layout()
    fig.savefig(FIGURES / "comparacion_modelos.png", dpi=180)
    plt.close(fig)

    test = predictions[predictions.particion == "prueba"]
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for name in names:
        group = test[test.modelo == name]
        fpr, tpr, _ = roc_curve(group.real, group.probabilidad_laa)
        auc = roc_auc_score(group.real, group.probabilidad_laa)
        ax.plot(fpr, tpr, label=f"{name}: {auc:.3f}", color=COLORS[name], linewidth=2)
    ax.plot([0, 1], [0, 1], "--", color="#aaaaaa", linewidth=1)
    ax.set(xlabel="Tasa de falsos positivos", ylabel="Sensibilidad LAA",
           title="Curvas ROC en pacientes de prueba")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "roc_prueba.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for name in names:
        group = test[test.modelo == name]
        precision, recall, _ = precision_recall_curve(group.real, group.probabilidad_laa)
        ap = average_precision_score(group.real, group.probabilidad_laa)
        ax.plot(recall, precision, label=f"{name}: AP {ap:.3f}",
                color=COLORS[name], linewidth=2)
    ax.axhline(test_y.mean(), linestyle="--", color="#aaaaaa", linewidth=1)
    ax.set(xlabel="Sensibilidad LAA", ylabel="Precisión LAA",
           title="Precisión–sensibilidad en pacientes de prueba")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "precision_recall_prueba.png", dpi=180)
    plt.close(fig)

    chosen = test[test.modelo == winner]
    matrix = confusion_matrix(chosen.real, chosen.prediccion, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5.5, 4.8))
    ConfusionMatrixDisplay(matrix, display_labels=["CE", "LAA"]).plot(
        ax=ax, cmap="Blues", colorbar=False, values_format="d")
    ax.set_title(f"Matriz de confusión en prueba: {winner}")
    ax.set_xlabel("Predicción")
    ax.set_ylabel("Etiqueta real")
    fig.tight_layout()
    fig.savefig(FIGURES / "confusion_modelo_elegido.png", dpi=180)
    plt.close(fig)


def main():
    data = pd.read_csv(SOURCE, dtype={"patient_id": str, "center_id": str})
    feature_columns = [column for column in data.columns
                       if column not in ("patient_id", "label", "center_id", "particion")]
    if len(data) != 630 or len(feature_columns) == 0:
        raise ValueError("Características faltantes")
    subsets = {name: data[data.particion == name].copy()
               for name in ("entrenamiento", "validacion", "prueba")}
    if {name: len(group) for name, group in subsets.items()} != {
            "entrenamiento": 438, "validacion": 97, "prueba": 95}:
        raise ValueError("La partición por paciente cambió")
    arrays = {name: (group[feature_columns].to_numpy(dtype=np.float64),
                     (group.label == POSITIVE).to_numpy(dtype=np.int32))
              for name, group in subsets.items()}
    if not all(np.isfinite(x).all() for x, _ in arrays.values()):
        raise ValueError("Características no finitas")
    x_train, y_train = arrays["entrenamiento"]
    cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=SEED)
    specifications = {
        "Regresión logística": (
            Pipeline([("escala", StandardScaler()),
                      ("modelo", LogisticRegression(class_weight="balanced", max_iter=3000,
                                                   random_state=SEED))]),
            {"modelo__C": [.01, .1, 1, 10]}),
        "Bosque aleatorio": (
            Pipeline([("modelo", RandomForestClassifier(n_estimators=300,
                                                        class_weight="balanced_subsample",
                                                        max_features="sqrt", n_jobs=2,
                                                        random_state=SEED))]),
            {"modelo__min_samples_leaf": [2, 5, 10]}),
        "SVM RBF": (
            Pipeline([("escala", StandardScaler()),
                      ("modelo", SVC(kernel="rbf", class_weight="balanced",
                                     probability=True, random_state=SEED))]),
            {"modelo__C": [.1, 1, 10]}),
    }
    fitted = {}
    tuning = {}
    metric_rows = []
    prediction_rows = []
    for name, (pipeline, grid) in specifications.items():
        search = GridSearchCV(pipeline, grid, scoring="roc_auc", cv=cv,
                              n_jobs=1, refit=True)
        search.fit(x_train, y_train)
        fitted[name] = search.best_estimator_
        tuning[name] = {"parametros": search.best_params_,
                        "auc_cv_media": float(search.best_score_),
                        "auc_cv_desv": float(search.cv_results_["std_test_score"][search.best_index_])}
        print(f"{name}: CV AUC={search.best_score_:.3f} {search.best_params_}", flush=True)
        x_val, y_val = arrays["validacion"]
        probabilities = search.best_estimator_.predict_proba(x_val)[:, 1]
        metric_rows.append({"modelo": name, "particion": "validacion",
                            **metrics(y_val, probabilities)})
        for patient_id, real, probability in zip(subsets["validacion"].patient_id,
                                                 y_val, probabilities):
            prediction_rows.append({"modelo": name, "particion": "validacion",
                                    "patient_id": patient_id, "real": int(real),
                                    "probabilidad_laa": float(probability),
                                    "prediccion": int(probability >= .5)})

    # Se fija el ganador con validación antes de mirar métricas de prueba.
    validation = [row for row in metric_rows if row["particion"] == "validacion"]
    winner = max(validation, key=lambda row: (row["roc_auc"],
                                              row["balanced_accuracy"], row["modelo"]))["modelo"]
    print(f"Modelo elegido por AUC de validación: {winner}", flush=True)

    # Solo después de fijar el ganador se evalúa la prueba reservada.
    x_test, y_test = arrays["prueba"]
    for name, model in fitted.items():
        probabilities = model.predict_proba(x_test)[:, 1]
        metric_rows.append({"modelo": name, "particion": "prueba",
                            **metrics(y_test, probabilities)})
        for patient_id, real, probability in zip(subsets["prueba"].patient_id,
                                                 y_test, probabilities):
            prediction_rows.append({"modelo": name, "particion": "prueba",
                                    "patient_id": patient_id, "real": int(real),
                                    "probabilidad_laa": float(probability),
                                    "prediccion": int(probability >= .5)})

    prior = float(y_train.mean())
    for split in ("validacion", "prueba"):
        _, y = arrays[split]
        probabilities = np.full(len(y), prior)
        metric_rows.append({"modelo": "Mayoría CE", "particion": split,
                            **metrics(y, probabilities)})
        for patient_id, real in zip(subsets[split].patient_id, y):
            prediction_rows.append({"modelo": "Mayoría CE", "particion": split,
                                    "patient_id": patient_id, "real": int(real),
                                    "probabilidad_laa": prior, "prediccion": 0})

    RESULTS.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(metric_rows).to_csv(RESULTS / "metricas_modelos.csv", index=False,
                                     float_format="%.6g", lineterminator="\n")
    predictions = pd.DataFrame(prediction_rows)
    predictions.to_csv(RESULTS / "predicciones_pacientes.csv", index=False,
                       float_format="%.6g", lineterminator="\n")
    joblib.dump({"pipeline": fitted[winner], "feature_columns": feature_columns,
                 "positive_class": POSITIVE, "selection_rule": "max AUC validacion"},
                MODEL_DIR / "modelo_elegido.joblib", compress=3)
    test_chosen = predictions[(predictions.modelo == winner) &
                              (predictions.particion == "prueba")]
    confidence = uncertainty(y_test, test_chosen.probabilidad_laa.to_numpy())
    charts(metric_rows, predictions, winner, y_test)
    report = {
        "modelo_elegido": winner, "criterio_seleccion": "Máximo AUC ROC de validación",
        "clase_positiva": POSITIVE, "umbral_clasificacion": .5,
        "pacientes": {name: len(group) for name, group in subsets.items()},
        "caracteristicas": len(feature_columns), "semilla": SEED,
        "cv": "4 folds estratificados dentro de entrenamiento, optimizando AUC ROC",
        "ajuste": tuning,
        "metricas": metric_rows,
        "incertidumbre_modelo_elegido_prueba": confidence,
        "sklearn_version": sklearn.__version__,
        "limitaciones": ["Imágenes PNG reducidas, no TIFF originales",
                         "Dos pacientes de entrenamiento sin regiones",
                         "Máscara y EDA inspeccionaron todas las imágenes antes de fijar la partición",
                         "Evaluación interna; no hay validación clínica externa"],
    }
    (RESULTS / "entrenamiento_resumen.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"elegido": winner,
                      "prueba": next(row for row in metric_rows
                                     if row["modelo"] == winner and row["particion"] == "prueba"),
                      "intervalos": confidence}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
