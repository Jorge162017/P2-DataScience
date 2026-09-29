"""Descarga TIFF oficiales del manifiesto, de forma incremental y reanudable.

Requiere haber aceptado las reglas del concurso e iniciado sesión con Kaggle CLI.
Por defecto descarga solo dos archivos para comprobar acceso y tamaños.
"""

import argparse
import csv
import os
import shutil
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEST = ROOT / "datos/originales"
MANIFEST = ROOT / "datos/muestra_piloto.csv"
CLI = ROOT / ".venv/bin/kaggle"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=2, help="Máximo de archivos nuevos (2 por defecto)")
    parser.add_argument("--simular", action="store_true", help="Mostrar rutas sin descargar")
    args = parser.parse_args()
    if args.limite < 1:
        parser.error("--limite debe ser positivo")
    if not CLI.is_file():
        parser.error("Falta .venv/bin/kaggle; instale las dependencias del proyecto")

    with MANIFEST.open(newline="", encoding="utf-8") as stream:
        manifest_rows = list(csv.DictReader(stream))
    # Primero una lámina de cada clase por centro; luego segundas láminas.
    groups = defaultdict(list)
    for row in manifest_rows:
        groups[(row["center_id"], row["label"])].append(row)
    centers = sorted({row["center_id"] for row in manifest_rows}, key=int)
    rows = [group[index]
            for index in range(max(map(len, groups.values())))
            for center in centers
            for label in ("CE", "LAA")
            if (group := groups[(center, label)]) and index < len(group)]
    env = os.environ.copy()
    env["KAGGLE_CONFIG_DIR"] = str(ROOT / ".venv/kaggle_config")
    downloaded = 0
    for row in rows:
        image_id = row["image_id"]
        expected_path = f"train/{image_id}.tif"
        if row["archivo_oficial"] != expected_path:
            raise ValueError(f"Ruta no coincide con image_id: {row}")
        target = DEST / expected_path
        if target.is_file() and target.stat().st_size > 0:
            continue
        if downloaded == args.limite:
            break
        free_gib = shutil.disk_usage(ROOT).free / 1024**3
        if free_gib < 25:
            raise RuntimeError(f"Espacio libre insuficiente para continuar: {free_gib:.1f} GiB")
        command = [str(CLI), "competitions", "download", "mayo-clinic-strip-ai",
                   "-f", expected_path, "-p", str(DEST), "-q"]
        print(f"{image_id} ({row['label']}, centro {row['center_id']}): {expected_path}", flush=True)
        if not args.simular:
            DEST.mkdir(parents=True, exist_ok=True)
            archive = DEST / f"{image_id}.tif.zip"
            if not archive.is_file() or not zipfile.is_zipfile(archive):
                subprocess.run(command, env=env, check=True)
            if archive.is_file():
                with zipfile.ZipFile(archive) as zf:
                    member = f"{image_id}.tif"
                    if member not in zf.namelist():
                        raise RuntimeError(f"El ZIP no contiene {member}: {archive}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temporary = target.with_suffix(".tif.part")
                    with zf.open(member) as source, temporary.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    if temporary.stat().st_size != zf.getinfo(member).file_size:
                        raise RuntimeError(f"Extracción incompleta: {temporary}")
                    temporary.replace(target)
            if not target.is_file() or target.stat().st_size == 0:
                raise RuntimeError(f"Kaggle terminó, pero no se encontró un TIFF válido: {target}")
            print(f"Descargado: {target.stat().st_size / 1024**2:.1f} MiB", flush=True)
        downloaded += 1
    print(f"Archivos {'previstos' if args.simular else 'nuevos descargados'}: {downloaded}")


if __name__ == "__main__":
    main()
