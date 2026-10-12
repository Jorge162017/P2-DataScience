# Clasificación del origen de coágulos en ACV

**Proyecto 2 — Análisis exploratorio y resultados · Tema 22**
CC3084 Data Science · Universidad del Valle de Guatemala · 2026
**Jorge Luis Lopez — 221038**

Análisis exploratorio y fase de modelado de los datos del reto
[Mayo Clinic — STRIP AI](https://www.kaggle.com/competitions/mayo-clinic-strip-ai/data),
orientado al estudio de las etiologías cardioembólica (CE) y ateroesclerosis de
grandes arterias (LAA) en coágulos de pacientes con accidente cerebrovascular.

La primera fase incluye limpieza y validación de metadatos, distribución de clases,
comparaciones por paciente y centro, procesamiento de imágenes, estadísticas,
correlaciones y revisión de valores atípicos. La segunda fase incluye división por
paciente, selección de tejido, extracción de características, entrenamiento de
tres clasificadores y una aplicación interactiva.

## Entregables

**Entrega final** (`entregables/final/`):

- [Informe final en PDF](entregables/final/Informe_Final_Proyecto2_Jorge_Lopez.pdf) y [fuente HTML editable](entregables/final/INFORME_FINAL_PROYECTO2.html).
- Presentación final: [PPTX editable](entregables/final/Proyecto2_Resultados_Jorge_Lopez.pptx) y [PDF](entregables/final/Proyecto2_Resultados_Jorge_Lopez.pdf). Explica el paso del piloto de seis imágenes al conjunto etiquetado completo de 754 PNG reducidos.

**Entregas anteriores** (`entregables/anteriores/`):

- [Notebook ejecutado de la primera fase](Tema22_Analisis_Exploratorio.ipynb), [informe](<entregables/anteriores/Proyecto 2 — Data Science.pdf>) y presentación ([PPTX](entregables/anteriores/Clasificacion_Coagulos_ACV.pptx), [PDF](entregables/anteriores/Clasificacion_Coagulos_ACV.pdf)).
- [PDF del EDA visual intermedio](entregables/anteriores/EDA_Visual_Proyecto2.pdf).

**Documentación técnica** (`documentacion/`): [procedencia y avance](documentacion/AVANCE_RESULTADOS.md), [EDA visual](documentacion/EDA_VISUAL_REDUCIDAS.md), [partición](documentacion/PARTICION_DATOS.md), [regiones](documentacion/SELECCION_REGIONES.md), [modelos](documentacion/RESULTADOS_MODELOS.md) y [app](documentacion/APLICACION_INTERACTIVA.md). Estos `.md` explican decisiones y controles; no son archivos que se deban entregar por separado.

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
piloto se describe en [AVANCE_RESULTADOS.md](documentacion/AVANCE_RESULTADOS.md).

- `datos/`: CSV, imágenes y registro de procedencia con SHA-256.
- `validar_reducidas.py`: verifica los PNG y regenera el manifiesto.
- `analizar_reducidas.py` y `validar_metodo_tejido.py`: EDA visual completo y auditoría de la máscara.
- `particionar_pacientes.py` y `validar_particion.py`: división y control de fuga entre grupos.
- `seleccionar_regiones.py` y `validar_regiones.py`: coordenadas de recortes y control de calidad.
- `extraer_caracteristicas.py` y `entrenar_modelos.py`: extracción, ajuste y evaluación de tres clasificadores.
- `app.py`, `templates/` y `static/`: aplicación local con Flask para explorar y clasificar.
- `analisis.py`: carga, validación, procesamiento y exportación de resultados.
- `resultados/`: tablas, figuras y validaciones de ambas fases.
- `entregables/`: informes y presentaciones separados en `final/` y `anteriores/`. `crear_presentacion_final.py` y `exportar_presentacion_pdf.py` generan la presentación final.
- `documentacion/`: notas técnicas para reproducir y auditar las decisiones del proyecto.
- `referencias/`: enunciado del curso conservado localmente; no se publica en Git.

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
python seleccionar_regiones.py
python validar_regiones.py
python extraer_caracteristicas.py
python entrenar_modelos.py
python app.py
```

En Windows, activar el entorno con `.venv\Scripts\activate`.
No se necesita GPU. El script regenera `resultados/`; el notebook también puede
ejecutarse completo. Sus interpretaciones son celdas Markdown y deben revisarse
si se cambian los datos o parámetros.
