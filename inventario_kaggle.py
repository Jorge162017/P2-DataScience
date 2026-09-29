"""Lista tamaños oficiales del concurso y de la copia reducida de 754 imágenes."""

import csv
import os
from collections import defaultdict
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parent
os.environ.setdefault("KAGGLE_CONFIG_DIR", str(ROOT / ".venv/kaggle_config"))
api = KaggleApi()
api.authenticate()


def collect(fetch):
    files = []
    token = None
    while True:
        response = fetch(page_token=token, page_size=200)
        files.extend(response.files)
        token = response.next_page_token
        if not token:
            break
    return files


files = collect(lambda **kwargs: api.competition_list_files("mayo-clinic-strip-ai", **kwargs))
output = ROOT / "resultados/inventario_concurso.csv"
with output.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("archivo", "bytes"))
    writer.writerows((f.name, f.total_bytes) for f in files)
groups = defaultdict(lambda: [0, 0])
for file in files:
    group = file.name.split("/", 1)[0] if "/" in file.name else "CSV"
    groups[group][0] += 1
    groups[group][1] += file.total_bytes or 0
print("Concurso Mayo Clinic - STRIP AI:")
for group, (count, size) in sorted(groups.items()):
    print(f"  {group}: {count} archivos, {size / 1024**3:.2f} GiB")
print(f"Inventario guardado: {output}")

files = collect(lambda **kwargs: api.dataset_list_files("saurabhsawhney/mayo-resized-images", **kwargs))
output = ROOT / "resultados/inventario_reducido.csv"
with output.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("archivo", "bytes"))
    writer.writerows((f.name, f.total_bytes) for f in files)
print("Copia reducida:", len(files), "archivos,",
      round(sum((f.total_bytes or 0) for f in files) / 1024**3, 2), "GiB")
print(f"Inventario guardado: {output}")
