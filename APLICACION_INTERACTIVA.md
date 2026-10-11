# Aplicación interactiva de resultados

La aplicación local permite explorar los 632 pacientes y las 754 imágenes del
conjunto etiquetado, comparar los tres clasificadores y cargar nuevas imágenes
reducidas para obtener una salida CE/LAA por modelo.

## Ejecución

Desde la raíz del proyecto, instala primero las dependencias en el mismo
intérprete con el que abrirás la aplicación:

```bash
python -m pip install -r requirements.txt
python app.py
```

Si `python app.py` muestra `ModuleNotFoundError`, ese intérprete no tiene las
dependencias. En esta computadora también se puede usar el Python que ya las
tiene instaladas:

```bash
/usr/local/bin/python3 app.py
```

Abrir `http://127.0.0.1:5000` en el navegador. La aplicación usa los artefactos
`modelos/*.joblib` y los CSV de `datos/` y `resultados/` incluidos en el repositorio.
Para clasificar, seleccionar de 1 a 10 PNG/JPG reducidos del mismo paciente.
El límite de carga es 50 MB en total. La exploración y comparación de modelos
funcionan aunque los PNG de entrenamiento no estén en la máquina.

## Flujo de una imagen nueva

El servidor aplica la máscara de tejido fijada durante el EDA, selecciona hasta
ocho regiones de 256 × 256 por imagen y extrae los mismos 57 descriptores de
color y textura por región. Agrega media y desviación para formar las 114
características por paciente y ejecuta los tres modelos entrenados. Si ninguna
imagen produce regiones con suficiente tejido, informa que no puede clasificar.

La interfaz se construyó con Flask, HTML, CSS y JavaScript local. Flask permite
reutilizar directamente el procesamiento en Python y cargar los modelos de
scikit-learn. Los gráficos SVG y sus controles no requieren conexión a internet.

## Interpretación

El bosque aleatorio fue seleccionado por AUC ROC de validación. En los 95
pacientes de prueba alcanzó AUC ROC 0.522 y exactitud balanceada 0.487. Su
rendimiento es cercano al azar; las salidas de la aplicación son solo una
demostración académica y no deben usarse para decisiones clínicas. La prueba
es interna y las imágenes son una copia PNG reducida, no los TIFF originales.
El resultado de una imagen nueva puede cambiar según la reducción y tinción;
la salida LAA mostrada no equivale a una probabilidad clínica calibrada.
