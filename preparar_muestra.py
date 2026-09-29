"""Audita los metadatos y prepara una muestra piloto del reto STRIP AI.

Uso:
    python preparar_muestra.py
    python preparar_muestra.py --oficial ruta/al/train.csv
"""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COLUMNS = ("image_id", "center_id", "patient_id", "image_num", "label")


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != set(COLUMNS):
            raise ValueError(f"Columnas inesperadas en {path}: {reader.fieldnames}")
        rows = [{column: row[column].strip() for column in COLUMNS} for row in reader]
    if not rows:
        raise ValueError(f"El CSV está vacío: {path}")
    return rows


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def choose_pilot(rows, per_class, seed):
    patients = defaultdict(list)
    for row in rows:
        patients[row["patient_id"]].append(row)

    rng = random.Random(seed)
    chosen = []
    for label in ("CE", "LAA"):
        by_center = defaultdict(list)
        for patient_rows in patients.values():
            if patient_rows[0]["label"] != label:
                continue
            # Una sola lámina por paciente durante el piloto; las restantes
            # se podrán agregar después sin cambiar la unidad de análisis.
            representative = min(patient_rows, key=lambda row: (int(row["image_num"]), row["image_id"]))
            by_center[representative["center_id"]].append(representative)
        if sum(map(len, by_center.values())) < per_class:
            raise ValueError(f"No hay {per_class} pacientes de clase {label}")
        for group in by_center.values():
            rng.shuffle(group)
        centers = sorted(by_center, key=lambda center: int(center))
        count = 0
        while count < per_class:
            for center in centers:
                if by_center[center]:
                    chosen.append(by_center[center].pop())
                    count += 1
                    if count == per_class:
                        break
    return sorted(chosen, key=lambda row: (row["label"], int(row["center_id"]), row["image_id"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oficial", type=Path, help="CSV oficial descargado de Kaggle para comprobar coincidencia")
    parser.add_argument("--por-clase", type=int, default=20, help="Pacientes por clase para el piloto (20 por defecto)")
    parser.add_argument("--semilla", type=int, default=22)
    args = parser.parse_args()
    if args.por_clase < 1:
        parser.error("--por-clase debe ser positivo")

    local_csv = ROOT / "datos/train.csv"
    rows = read_csv(local_csv)
    image_ids = [row["image_id"] for row in rows]
    if len(image_ids) != len(set(image_ids)):
        raise ValueError("Hay image_id repetidos")
    patients = defaultdict(list)
    for row in rows:
        if row["label"] not in ("CE", "LAA"):
            raise ValueError(f"Etiqueta inesperada: {row['label']}")
        if row["image_id"] != f"{row['patient_id']}_{row['image_num']}":
            raise ValueError(f"image_id inconsistente: {row['image_id']}")
        patients[row["patient_id"]].append(row)
    if any(len({(r["center_id"], r["label"]) for r in group}) != 1 for group in patients.values()):
        raise ValueError("Hay pacientes con centro o etiqueta inconsistentes")

    official_match = None
    official_hash = None
    if args.oficial:
        official_rows = read_csv(args.oficial)
        official_match = Counter(tuple(r[c] for c in COLUMNS) for r in rows) == Counter(
            tuple(r[c] for c in COLUMNS) for r in official_rows
        )
        official_hash = sha256(args.oficial)

    local_images = []
    known_ids = set(image_ids)
    for path in sorted((ROOT / "datos/imagenes").iterdir()):
        if path.is_file():
            image_id = path.stem.removesuffix("_tissue2048")
            local_images.append({"archivo": path.name, "image_id": image_id, "en_train_csv": image_id in known_ids})

    pilot = choose_pilot(rows, args.por_clase, args.semilla)
    manifest = ROOT / "datos/muestra_piloto.csv"
    fields = (*COLUMNS, "archivo_oficial")
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in pilot:
            writer.writerow({**row, "archivo_oficial": f"train/{row['image_id']}.tif"})

    audit = {
        "fuente_csv_local": "datos/train.csv (copia de P2-DS)",
        "sha256_csv_local": sha256(local_csv),
        "sha256_csv_oficial": official_hash,
        "filas_csv": len(rows),
        "pacientes": len(patients),
        "etiquetas_por_imagen": dict(Counter(r["label"] for r in rows)),
        "etiquetas_por_paciente": dict(Counter(group[0]["label"] for group in patients.values())),
        "centros": len({r["center_id"] for r in rows}),
        "imagenes_locales": local_images,
        "coincide_con_csv_oficial": official_match,
        "muestra_piloto": {"pacientes": len(pilot), "por_clase": args.por_clase,
                            "centros": len({r["center_id"] for r in pilot}), "semilla": args.semilla},
    }
    output = ROOT / "resultados/auditoria_datos.json"
    output.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    print(f"Manifiesto: {manifest}")


if __name__ == "__main__":
    main()
