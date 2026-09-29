"""Divide STRIP AI por paciente, estratificando por centro y etiqueta.

Desde esta división, la prueba se reserva para la evaluación final. Semilla y
reglas fijas en este archivo.
"""

import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "datos/imagenes_reducidas.csv"
TRAIN_CSV = ROOT / "datos/train.csv"
PATIENTS_OUT = ROOT / "datos/particion_pacientes.csv"
IMAGES_OUT = ROOT / "datos/particion_imagenes.csv"
COUNTS_OUT = ROOT / "resultados/particion_centro_clase.csv"
REPORT_OUT = ROOT / "resultados/particion_resumen.json"
SEED = 22
SPLITS = ("entrenamiento", "validacion", "prueba")
RATIOS = (0.70, 0.15, 0.15)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def allocation(n, center):
    """Cuotas de mayor residuo; asegura una plaza por grupo si n >= 3."""
    if n == 1:
        return [1, 0, 0]
    if n == 2:
        # Se reparte la escasez de LAA entre validación (C8) y prueba (C9).
        return [1, 1, 0] if center == "8" else [1, 0, 1]
    ideal = [n * ratio for ratio in RATIOS]
    counts = [math.floor(value) for value in ideal]
    remainder = n - sum(counts)
    order = sorted(range(3), key=lambda i: (-(ideal[i] - counts[i]), i))
    for index in order[:remainder]:
        counts[index] += 1
    for index in range(3):
        if counts[index] == 0:
            donor = max(range(3), key=lambda i: counts[i])
            counts[donor] -= 1
            counts[index] += 1
    return counts


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    with MANIFEST.open(newline="", encoding="utf-8") as stream:
        images = list(csv.DictReader(stream))
    with TRAIN_CSV.open(newline="", encoding="utf-8") as stream:
        official = list(csv.DictReader(stream))
    if len(images) != 754 or len(official) != 754:
        raise ValueError("Se esperaban 754 imágenes anotadas")
    by_image = {row["image_id"]: row for row in official}
    if len(by_image) != 754 or {row["image_id"] for row in images} != set(by_image):
        raise ValueError("El manifiesto y train.csv no cubren las mismas imágenes")
    if len({row["sha256"] for row in images}) != 754:
        raise ValueError("Hay PNG duplicados por SHA-256; revisar antes de dividir")
    patients = {}
    groups = defaultdict(list)
    for row in images:
        source = by_image[row["image_id"]]
        if any(row[key] != source[key] for key in ("patient_id", "center_id", "label")):
            raise ValueError(f"Metadatos inconsistentes para {row['image_id']}")
        patient_id = row["patient_id"]
        meta = (row["center_id"], row["label"])
        if patient_id in patients and patients[patient_id] != meta:
            raise ValueError(f"Paciente con más de un centro o etiqueta: {patient_id}")
        patients[patient_id] = meta
    if len(patients) != 632:
        raise ValueError(f"Se esperaban 632 pacientes; hay {len(patients)}")
    for patient_id, meta in patients.items():
        groups[meta].append(patient_id)

    assignments = {}
    for (center, label), pool in sorted(groups.items(), key=lambda item: (int(item[0][0]), item[0][1])):
        shuffled = sorted(pool)
        random.Random(f"{SEED}:{center}:{label}").shuffle(shuffled)
        counts = allocation(len(shuffled), center)
        if sum(counts) != len(shuffled):
            raise AssertionError("Cuotas incorrectas")
        start = 0
        for split, count in zip(SPLITS, counts):
            for patient_id in shuffled[start:start + count]:
                assignments[patient_id] = split
            start += count

    patient_rows = [
        {"patient_id": patient_id, "center_id": patients[patient_id][0],
         "label": patients[patient_id][1], "particion": assignments[patient_id],
         "n_imagenes": sum(row["patient_id"] == patient_id for row in images)}
        for patient_id in sorted(patients)
    ]
    image_rows = [
        {"image_id": row["image_id"], "patient_id": row["patient_id"],
         "center_id": row["center_id"], "label": row["label"],
         "particion": assignments[row["patient_id"]],
         "archivo_reducido": row["archivo_reducido"]}
        for row in images
    ]
    # Pruebas de fuga y cobertura antes de guardar la partición.
    if len(assignments) != 632 or len(image_rows) != 754:
        raise AssertionError("La partición no cubre el conjunto completo")
    for split in SPLITS:
        subset = [row for row in patient_rows if row["particion"] == split]
        if {row["label"] for row in subset} != {"CE", "LAA"}:
            raise AssertionError(f"Falta una clase en {split}")
        if len({row["center_id"] for row in subset}) != 11:
            raise AssertionError(f"Falta un centro en {split}")
    if any(row["particion"] != assignments[row["patient_id"]] for row in image_rows):
        raise AssertionError("Una imagen quedó fuera de la partición de su paciente")

    counts_rows = []
    for center in sorted({meta[0] for meta in patients.values()}, key=int):
        for label in ("CE", "LAA"):
            group = [row for row in patient_rows if row["center_id"] == center and row["label"] == label]
            counts_rows.append({"center_id": center, "label": label, "total_pacientes": len(group),
                                **{split: sum(row["particion"] == split for row in group)
                                   for split in SPLITS}})
    write_csv(PATIENTS_OUT, patient_rows,
              ("patient_id", "center_id", "label", "particion", "n_imagenes"))
    write_csv(IMAGES_OUT, image_rows,
              ("image_id", "patient_id", "center_id", "label", "particion", "archivo_reducido"))
    write_csv(COUNTS_OUT, counts_rows,
              ("center_id", "label", "total_pacientes", *SPLITS))

    report = {
        "semilla": SEED, "proporciones_objetivo": dict(zip(SPLITS, RATIOS)),
        "metodo": "Cuotas por centro y clase; asignación aleatoria reproducible de pacientes completos",
        "sha256_train_csv": sha256(TRAIN_CSV),
        "sha256_manifiesto": sha256(MANIFEST),
        "pacientes_total": len(patient_rows), "imagenes_total": len(image_rows),
        "pacientes_por_particion": dict(Counter(row["particion"] for row in patient_rows)),
        "imagenes_por_particion": dict(Counter(row["particion"] for row in image_rows)),
        "pacientes_clase_por_particion": {
            split: dict(Counter(row["label"] for row in patient_rows if row["particion"] == split))
            for split in SPLITS},
        "centros_por_particion": {
            split: len({row["center_id"] for row in patient_rows if row["particion"] == split})
            for split in SPLITS},
        "pacientes_sin_fuga": True,
        "imagenes_sin_sha256_duplicado": True,
        "estratos_imposibles_de_representar_en_tres_particiones": [
            {"center_id": row["center_id"], "label": row["label"],
             "pacientes": row["total_pacientes"]}
            for row in counts_rows if row["total_pacientes"] < 3],
    }
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
