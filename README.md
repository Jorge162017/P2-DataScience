# Clasificación del origen de coágulos en ACV

**Proyecto 2 — Análisis exploratorio y resultados · Tema 22**
CC3084 Data Science · Universidad del Valle de Guatemala · 2026
**Jorge Luis Lopez — 221038**

Primera fase terminada de análisis exploratorio de los datos del reto
[Mayo Clinic — STRIP AI](https://www.kaggle.com/competitions/mayo-clinic-strip-ai/data),
orientado al estudio de las etiologías cardioembólica (CE) y ateroesclerosis de
grandes arterias (LAA) en coágulos de pacientes con accidente cerebrovascular.

El análisis de la primera fase incluye limpieza y validación de metadatos, distribución de clases,
comparaciones por paciente y centro, procesamiento de imágenes, estadísticas,
correlaciones y revisión de valores atípicos. No se entrenó un clasificador.

## Entregables

- [Notebook ejecutado](Tema22_Analisis_Exploratorio.ipynb): procedimientos, gráficos e interpretaciones.
- [Informe final](<Proyecto 2 — Data Science.pdf>).
- [Presentación PowerPoint](presentacion/Clasificacion_Coagulos_ACV.pptx).
- [Presentación PDF](presentacion/Clasificacion_Coagulos_ACV.pdf).
- [Avance de resultados de la segunda fase](AVANCE_RESULTADOS.md): cotejo con Kaggle y primeras láminas originales.
- [EDA visual completo](EDA_VISUAL_REDUCIDAS.md): las 754 imágenes reducidas y validación del cribado de tejido.
- [PDF del EDA visual](EDA_Visual_Proyecto2.pdf).
- [Partición por paciente](PARTICION_DATOS.md): entrenamiento, validación y prueba sin mezclar pacientes.

## Datos y resultados

Se estudiaron **754 registros de 632 pacientes y 11 centros**. CE representa el
72.31 % de los pacientes. El CSV no contiene nulos ni duplicados.

En la primera fase se dispuso de **seis imágenes derivadas**; solo tres tienen etiquetas
correspondientes en el CSV: dos CE y una LAA del centro 11. Esta muestra permite
explorar características visuales, pero no establecer diferencias generales entre
etiologías ni validar capacidad de clasificación.

Para la segunda fase se descargó `train.csv` directamente de Kaggle y se comprobó
que coincide byte por byte con el CSV local. Se descargaron las **754 imágenes PNG
reducidas**, que cubren los **632 pacientes** del CSV: 547 CE y 207 LAA. La
[validación](resultados/validacion_reducidas.json) verificó integridad, nombres y
etiquetas de todos los PNG, además de la proporción de 26 TIFF originales locales.
El [manifiesto](datos/imagenes_reducidas.csv) vincula cada archivo con su
`image_id` y `patient_id` oficial. Los PNG están en `datos/reducidas/` y no se
incluyen en Git por tamaño. Las imágenes reducidas provienen de una
[copia derivada en Kaggle](https://www.kaggle.com/datasets/saurabhsawhney/mayo-resized-images),
no de los TIFF originales del concurso. Ocho PNG tienen 1100 píxeles de ancho;
los demás, 1120. Los 26 TIFF originales se conservan para cotejo y el análisis
piloto se describe en [AVANCE_RESULTADOS.md](AVANCE_RESULTADOS.md).

- `datos/`: CSV, imágenes y registro de procedencia con SHA-256.
- `validar_reducidas.py`: verifica los PNG y regenera el manifiesto.
- `analizar_reducidas.py` y `validar_metodo_tejido.py`: EDA visual completo y auditoría de la máscara.
- `particionar_pacientes.py` y `validar_particion.py`: división y control de fuga entre grupos.
- `analisis.py`: carga, validación, procesamiento y exportación de resultados.
- `resultados/`: tablas, figuras y validaciones de ambas fases.
- `presentacion/`: diapositivas finales en PPTX y PDF.

Los seis archivos visuales de la primera fase procedían de la copia local del
proyecto **P2-DS, Grupo 7 (2025)**, de Davis Roldán, Andy Fuentes, Gabriel Paz y
Jose Marchena. El CSV se verificó contra Kaggle y las 754 imágenes reducidas de
la segunda fase se descargaron de la fuente indicada arriba. Las fuentes y
limitaciones de la primera fase están documentadas en el notebook y su informe.

## Ejecución

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python analisis.py
python -m jupyterlab
```

Para recuperar la copia reducida en otra máquina con acceso a Kaggle:

```bash
kaggle datasets download saurabhsawhney/mayo-resized-images -p datos/reducidas --unzip
python validar_reducidas.py
python analizar_reducidas.py
python validar_metodo_tejido.py
python exportar_eda_pdf.py
python particionar_pacientes.py
python validar_particion.py
```

En Windows, activar el entorno con `.venv\Scripts\activate`.
No se necesita GPU. El script regenera `resultados/`; el notebook también puede
ejecutarse completo. Sus interpretaciones son celdas Markdown y deben revisarse
si se cambian los datos o parámetros.
