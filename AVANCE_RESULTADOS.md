# Avance de la segunda fase — Tema 22

**Fecha:** 28 de septiembre de 2026
**Reto:** [Mayo Clinic — STRIP AI](https://www.kaggle.com/competitions/mayo-clinic-strip-ai/data)
**Estado:** CSV oficial cotejado; 754 imágenes reducidas descargadas y validadas; 26 láminas originales inspeccionadas como piloto.

**Actualización posterior:** ya se completó el [EDA visual de las 754 imágenes](EDA_VISUAL_REDUCIDAS.md) y la validación técnica del método de tejido/fondo. Los pasos pendientes listados al final de este avance eran los previstos antes de ese análisis.

## Hallazgo principal

La documentación oficial indica que `train.csv` anota las láminas de `train/`, almacenadas como `train/{image_id}.tif`. Se descargó el CSV oficial de Kaggle y se comparó con el local: **son idénticos byte por byte**, con SHA-256 `8f713e3e863417aec94083ee6f97db6849ad7bde1d9b63de2c17cb5b1db806d8`. Tiene 754 registros de 632 pacientes, 11 centros, 547 imágenes CE y 207 LAA. Por tanto, el análisis exploratorio de **metadatos** de la primera fase sí utilizó el archivo correcto.

En la primera fase había solo seis imágenes **derivadas**: tres recortes JPG con `image_id` presente en el CSV y tres vistas PNG cuyo `image_id` no aparece allí. El análisis visual de esa fase describe esos seis archivos y no el conjunto de entrenamiento completo. Las estadísticas del CSV se pueden conservar; el análisis visual se debe ampliar y rehacer con láminas verificadas.

La auditoría reproducible está en [`preparar_muestra.py`](preparar_muestra.py) y su salida en [`resultados/auditoria_datos.json`](resultados/auditoria_datos.json).

## Muestra piloto preparada

Se generó [`datos/muestra_piloto.csv`](datos/muestra_piloto.csv) con **40 pacientes distintos**, 20 CE y 20 LAA, procedentes de los **11 centros**. Se seleccionó una lámina por paciente con semilla fija (22), alternando centros dentro de cada clase. El manifiesto incluye la ruta oficial esperada de cada TIFF para descarga individual. El balance CE/LAA es deliberado para el piloto y no representa la distribución real del conjunto.

Esta muestra sirve para comprobar acceso, lectura de TIFF, selección preliminar de regiones y tiempos de procesamiento. Se descargaron e inspeccionaron **26 de las 40 láminas propuestas**: 26 pacientes distintos, 13 CE y 13 LAA. Hay al menos una lámina de cada clase en los 11 centros; los centros 1 y 2 tienen dos de cada clase. Antes de entrenar modelos y medir su rendimiento se deberá ampliar la muestra y reservar pacientes completos para evaluación, sin mezclar láminas o regiones de un mismo paciente entre entrenamiento y prueba.

**Alcance frente al conjunto completo:** estos 26 pacientes son **26 de los 632** registrados en `train.csv`. Los otros **606 pacientes aún no tienen TIFF original descargado localmente**. Todos los 632 pacientes sí tienen una imagen reducida disponible localmente, según se detalla abajo.

## Conjunto reducido completo

Se descargó la [copia reducida de Kaggle](https://www.kaggle.com/datasets/saurabhsawhney/mayo-resized-images): **754 PNG de 632 pacientes**, con las etiquetas del CSV oficial (547 CE, 207 LAA). El directorio ocupa 1,042,694,773 bytes, aproximadamente 0.97 GiB. Sus archivos están en `datos/reducidas/1120/{CE,LAA}/idx_XXXX.png`; el índice corresponde al orden de las filas de `train.csv`. Como son imágenes derivadas, no conservan la resolución de los TIFF originales.

[`validar_reducidas.py`](validar_reducidas.py) verificó que existen los 754 índices únicos, que la carpeta de cada PNG coincide con su etiqueta y que todos los PNG son legibles. Comparó la proporción de **26 PNG con sus TIFF originales**: 25 coincidieron directamente y uno tras girarlo; la discrepancia máxima de altura fue de 1 píxel. Esta prueba respalda el enlace por orden de fila, aunque no sustituye una auditoría visual de las 754 imágenes. Ocho PNG tienen 1100 píxeles de ancho y 746 tienen 1120. El [manifiesto](datos/imagenes_reducidas.csv) enlaza cada ruta con `image_id`, `patient_id`, centro y etiqueta, y la [validación](resultados/validacion_reducidas.json) guarda los recuentos.

## Láminas oficiales y análisis técnico inicial

| `image_id` | Etiqueta | Centro | Dimensiones | Tamaño TIFF |
|---|---|---:|---:|---:|
| `509042_0` | CE | 1 | 31 735 × 71 863 px | 384.0 MiB |
| `c5d171_0` | LAA | 1 | 42 889 × 46 928 px | 600.6 MiB |

Las 26 láminas corresponden a pacientes distintos y sus identificadores están en el `train.csv` oficial. Suman **7.39 GiB** extraídas; sus tamaños varían entre **7.0 y 1 641.5 MiB**. Se leen por bloques de 128 × 128 píxeles, sin cargar una imagen completa en memoria. El [registro técnico](resultados/laminas_oficiales_piloto.csv) incluye dimensiones, centro, etiqueta, tamaño y SHA-256 de cada TIFF.

En cada lámina se muestrearon **576 regiones de 128 × 128 píxeles** en una cuadrícula de 24 × 24: 14 976 regiones en total. Para localizar posibles áreas de tejido se estimó el color de fondo de cada lámina con sus regiones más uniformes y se exigió una diferencia de color y variación de intensidad. **1 752 regiones** pasaron ese cribado técnico. Estas regiones no son observaciones independientes para entrenar o evaluar modelos; pertenecen a 26 pacientes.

Se detectaron dos límites del preprocesamiento inicial. Una lámina tenía fondo verde uniforme, que la máscara de color usada en la fase 1 confundía con tejido; la estimación de fondo por lámina evita ese falso positivo. Una cuadrícula inicial de 12 × 12 pasó por alto áreas pequeñas de otra lámina; con 24 × 24 se localizaron diez regiones candidatas. El cribado sigue siendo aproximado y necesita revisión visual y validación antes de extraer características para modelado.

Las figuras descriptivas del avance son [cobertura por centro y clase](resultados/figuras/piloto_composicion.png), [resolución y tamaño de los TIFF](resultados/figuras/piloto_tamanos.png) y [regiones candidatas por lámina](resultados/figuras/piloto_regiones.png). La [vista técnica](resultados/figuras/laminas_oficiales_piloto.png) muestra cuatro regiones de `509042_0` (CE) y cuatro de `c5d171_0` (LAA); no representa una comparación clínica entre clases.

La cuadrícula examina una fracción pequeña de cada imagen y sus porcentajes no estiman la proporción total de tejido. La selección está balanceada deliberadamente por clase y centro, por lo que tampoco reproduce las frecuencias del conjunto completo. **Todavía no hay resultados de clasificación ni evidencia para afirmar diferencias generales entre CE y LAA.**

## Siguientes pasos inmediatos

1. Rehacer el análisis exploratorio de imágenes con los 754 PNG y medidas agregadas por lámina o paciente; revisar visualmente la selección de tejido.
2. Definir la partición por paciente, entrenar varios modelos y evaluarlos en pacientes no vistos.
3. Comparar, cuando sea posible, el efecto de usar imágenes reducidas frente a los TIFF originales del piloto.

La descarga completa del concurso figura en Kaggle con aproximadamente 395 GB. Después del lote se midieron aproximadamente 150 GiB libres; por eso se usa la copia reducida para cubrir todo `train.csv` y se mantiene selectiva la descarga de TIFF originales. Ambas carpetas de imágenes están excluidas de Git.

## Comandos preparados

```bash
# Tras iniciar sesión en Kaggle y aceptar las reglas del concurso:
KAGGLE_CONFIG_DIR=.venv/kaggle_config .venv/bin/kaggle auth login

# Descargar solo el CSV oficial:
KAGGLE_CONFIG_DIR=.venv/kaggle_config .venv/bin/kaggle competitions download mayo-clinic-strip-ai -f train.csv -p datos/originales

# Comprobarlo contra el CSV utilizado en la fase 1:
python3 preparar_muestra.py --oficial datos/originales/train.csv

# Continuar con hasta cuatro TIFF nuevos (omite los ya descargados):
python3 descargar_muestra.py --limite 4

# Recuperar las 754 imágenes reducidas en otra máquina:
KAGGLE_CONFIG_DIR=.venv/kaggle_config .venv/bin/kaggle datasets download saurabhsawhney/mayo-resized-images -p datos/reducidas --unzip
python3 validar_reducidas.py

# Actualizar la inspección técnica tras descargar más láminas:
.venv/bin/python inspeccionar_laminas.py
python3 graficar_piloto.py
```

**Limitación actual:** los 632 pacientes tienen PNG reducido local, pero solo 26 tienen TIFF original. Las figuras piloto describen esos 26 TIFF; todavía no existe una evaluación de modelos.
