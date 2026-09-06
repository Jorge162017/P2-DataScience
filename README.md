# Clasificación del origen de coágulos en ACV

**Proyecto 2 — Análisis exploratorio · Tema 22**  
CC3084 Data Science · Universidad del Valle de Guatemala · 2026  
**Jorge Luis Lopez — 221038**

Proyecto finalizado de análisis exploratorio de los datos del reto
[Mayo Clinic — STRIP AI](https://www.kaggle.com/competitions/mayo-clinic-strip-ai/data),
orientado al estudio de las etiologías cardioembólica (CE) y ateroesclerosis de
grandes arterias (LAA) en coágulos de pacientes con accidente cerebrovascular.

El análisis incluye limpieza y validación de metadatos, distribución de clases,
comparaciones por paciente y centro, procesamiento de imágenes, estadísticas,
correlaciones y revisión de valores atípicos. No se entrenó un clasificador.

## Entregables

- [Notebook ejecutado](Tema22_Analisis_Exploratorio.ipynb): procedimientos, gráficos e interpretaciones.
- [Informe final](<Proyecto 2 — Data Science.pdf>).
- [Presentación PowerPoint](presentacion/Clasificacion_Coagulos_ACV.pptx).
- [Presentación PDF](presentacion/Clasificacion_Coagulos_ACV.pdf).

## Datos y resultados

Se estudiaron **754 registros de 632 pacientes y 11 centros**. CE representa el
72.31 % de los pacientes. El CSV no contiene nulos ni duplicados.

Localmente se dispone de **seis imágenes derivadas**; solo tres tienen etiquetas
correspondientes en el CSV: dos CE y una LAA del centro 11. Esta muestra permite
explorar características visuales, pero no establecer diferencias generales entre
etiologías ni validar capacidad de clasificación.

- `datos/`: CSV, imágenes y registro de procedencia con SHA-256.
- `analisis.py`: carga, validación, procesamiento y exportación de resultados.
- `resultados/`: 30 tablas, 11 figuras, hallazgos, parámetros y versiones utilizadas.
- `presentacion/`: diapositivas finales en PPTX y PDF.

Los archivos de datos se obtuvieron de la copia local del proyecto **P2-DS, Grupo 7
(2025)**, de Davis Roldán, Andy Fuentes, Gabriel Paz y Jose Marchena. Se rehízo el
análisis; las fuentes y limitaciones están documentadas en el notebook y el informe.

## Ejecución

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python analisis.py
python -m jupyterlab
```

En Windows, activar el entorno con `.venv\Scripts\activate`.
No se necesita GPU. El script regenera `resultados/`; el notebook también puede
ejecutarse completo. Sus interpretaciones son celdas Markdown y deben revisarse
si se cambian los datos o parámetros.
