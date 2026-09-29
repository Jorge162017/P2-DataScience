"""Comprueba cobertura, estratos y ausencia de fuga en los CSV de partición."""

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPLITS = {"entrenamiento", "validacion", "prueba"}


def read(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    manifest = read(ROOT / "datos/imagenes_reducidas.csv")
    patients = read(ROOT / "datos/particion_pacientes.csv")
    images = read(ROOT / "datos/particion_imagenes.csv")
    if len(manifest) != 754 or len(images) != 754 or len(patients) != 632:
        raise AssertionError("Recuentos incompletos")
    ids = [row["patient_id"] for row in patients]
    image_ids = [row["image_id"] for row in images]
    if len(set(ids)) != 632 or len(set(image_ids)) != 754:
        raise AssertionError("Identificadores duplicados")
    if {row["particion"] for row in patients} != SPLITS:
        raise AssertionError("Particiones desconocidas o ausentes")
    by_patient = {row["patient_id"]: row for row in patients}
    original = {row["image_id"]: row for row in manifest}
    if set(image_ids) != set(original):
        raise AssertionError("Imágenes omitidas o adicionales")
    if {row["patient_id"] for row in manifest} != set(ids):
        raise AssertionError("Pacientes omitidos o adicionales")
    counts = Counter()
    by_split = defaultdict(set)
    for row in images:
        reference = original[row["image_id"]]
        patient = by_patient[row["patient_id"]]
        for key in ("patient_id", "center_id", "label", "archivo_reducido"):
            if row[key] != reference[key]:
                raise AssertionError(f"Dato de imagen inconsistente: {row['image_id']} {key}")
        for key in ("center_id", "label"):
            if row[key] != patient[key]:
                raise AssertionError(f"Dato de paciente inconsistente: {row['patient_id']} {key}")
        if row["particion"] != patient["particion"]:
            raise AssertionError(f"Fuga de paciente: {row['patient_id']}")
        counts[row["patient_id"]] += 1
        by_split[row["particion"]].add(row["patient_id"])
    if any(int(row["n_imagenes"]) != counts[row["patient_id"]] for row in patients):
        raise AssertionError("Número de imágenes por paciente inconsistente")
    if any(by_split[a] & by_split[b] for a in SPLITS for b in SPLITS if a != b):
        raise AssertionError("Pacientes en dos particiones")
    for split in sorted(SPLITS):
        group = [row for row in patients if row["particion"] == split]
        if {row["label"] for row in group} != {"CE", "LAA"}:
            raise AssertionError(f"Falta una clase en {split}")
        if len({row["center_id"] for row in group}) != 11:
            raise AssertionError(f"Falta un centro en {split}")
        classes = Counter(row["label"] for row in group)
        print(f"{split}: {len(group)} pacientes, "
              f"{sum(counts[row['patient_id']] for row in group)} imágenes, "
              f"CE={classes['CE']}, LAA={classes['LAA']}, 11 centros")
    print("Sin fuga por paciente; cobertura completa de 754 imágenes.")


if __name__ == "__main__":
    main()
