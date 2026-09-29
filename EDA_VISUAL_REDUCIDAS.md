# Análisis exploratorio visual — conjunto reducido completo

**Tema 22 · Mayo Clinic STRIP AI · 28 de septiembre de 2026**

## Datos y alcance

Se analizaron las **754 imágenes PNG reducidas** vinculadas con el `train.csv` oficial: **632 pacientes**, **11 centros**, **547 imágenes CE** y **207 LAA**. Cada resultado se conserva por `image_id` y `patient_id` en [`resultados/eda_reducidas.csv`](resultados/eda_reducidas.csv). El enlace de imagen, paciente y etiqueta se validó previamente en [`datos/imagenes_reducidas.csv`](datos/imagenes_reducidas.csv). La copia reducida tiene 746 PNG de ancho 1120 px y 8 de 1100 px; no equivale a los TIFF originales en resolución o detalle.

Este EDA describe **propiedades técnicas de las imágenes**. No ofrece diagnóstico, rendimiento de un clasificador ni una prueba de diferencia biológica entre CE y LAA. Las imágenes repetidas de un paciente se mantienen vinculadas; las 754 imágenes no se tratan como 754 pacientes independientes.

## Método para distinguir tejido y fondo

Para hacer viable el barrido completo, cada PNG se reduce a **280 px de ancho**. En esa vista se identifica el color de fondo más frecuente entre píxeles de baja textura situados en el borde. Un píxel es candidato a tejido cuando su distancia de color RGB al fondo supera **30** y la desviación local de intensidad en una ventana de **5 × 5** supera **3**. Se eliminan componentes conectados menores de **8 píxeles**. El procedimiento no utiliza la etiqueta CE/LAA.

La máscara es un **cribado técnico aproximado**: sirve para localizar áreas con material visible y comparar cobertura, no para delimitar tejido a escala celular. Los umbrales están fijados en [`analizar_reducidas.py`](analizar_reducidas.py). Las cifras corresponden a la vista de 280 px; fragmentos pequeños y tejido muy pálido pueden desaparecer al reducir la imagen.

## Resultados descriptivos

- Fracción mediana de píxeles candidatos a tejido: **12.45 %**. Cuartiles: **8.27 %** y **17.66 %**; percentiles 5 y 95: **3.44 %** y **27.08 %**.
- **7 imágenes** quedaron por debajo de 1 % de área candidata; la revisión visual muestra que contienen fragmentos muy pequeños o tenues. Se deben revisar antes de excluirlas de cualquier entrenamiento.
- Las medianas por centro varían: por ejemplo, **21.10 % en el centro 4** y **3.74 % en el centro 8**. Esto puede reflejar preparación, recorte o captura, además de cantidad visible de material; no demuestra diferencias etiológicas.
- Las medianas descriptivas por imagen fueron **12.80 % para CE** y **11.27 % para LAA**. No se interpreta esta diferencia como biomarcador porque clase, centro, paciente y adquisición pueden confundirse.

Figuras: [cobertura y centros](resultados/figuras/reducidas_cobertura_tejido.png) y [tamaño, color y textura](resultados/figuras/reducidas_color_textura.png). El [resumen JSON](resultados/eda_reducidas_resumen.json) permite comprobar los recuentos y parámetros.

## Validación del cribado

Se inspeccionaron visualmente **61 pares de imagen y máscara**, seleccionados con semilla fija (22): hasta dos imágenes por combinación de los 11 centros y ambas clases, más casos con cobertura mínima, máxima y fondo difícil. Las [ocho hojas de revisión](resultados/figuras/validacion_tejido/muestra_01.jpg) muestran la imagen original junto a la superposición verde de su máscara. En los ejemplos revisados, las masas visibles de tejido quedan mayormente marcadas y las zonas amplias de fondo uniforme, incluidas las rosadas, violetas y verdosas, quedan sin marcar. También se observan fragmentos pálidos, trazos de montaje y bordes para los que la decisión es incierta; por ello no se declara exactitud de segmentación.

Se hizo una auditoría de sensibilidad en las 754 imágenes con umbrales más permisivos (distancia de color 20, textura 2) y más estrictos (40 y 5). La cobertura mediana fue **12.80 %, 12.45 % y 12.03 %**, respectivamente. La mediana de intersección sobre unión con la máscara base fue **0.982** para el ajuste permisivo y **0.975** para el estricto. Solo **1** imagen cambió más de 5 puntos porcentuales con el ajuste permisivo y **4** con el estricto. Esto indica estabilidad frente a esos cambios concretos, no exactitud frente a una referencia manual.

La regla de la primera fase marcaba tejido si gris < 230 **o** saturación > 0.10. Su cobertura mediana en el conjunto completo es **14.36 %**, pero en **116 imágenes** marca al menos 25 puntos porcentuales más que el método nuevo. En una imagen con fondo coloreado (`caf901_0`) marca **99.99 %** frente a **3.45 %** con la máscara nueva; la [comparación de máscaras](resultados/figuras/reducidas_comparacion_mascaras.png) permite ver el motivo. Por eso la regla anterior no se reutiliza para el EDA completo. El [detalle por imagen](resultados/validacion_metodo_tejido.csv) y el [resumen de validación](resultados/validacion_metodo_tejido.json) documentan esta comparación.

**Límite de validación:** no existe una máscara de tejido dibujada por una persona experta para estas 754 imágenes. La revisión visual y la prueba de sensibilidad respaldan el cribado descriptivo, pero no permiten calcular sensibilidad, especificidad o Dice reales. Antes de usar las máscaras como etiquetas de entrenamiento o para una afirmación clínica, se necesita una pequeña muestra anotada a mano, idealmente revisada por alguien con experiencia en histopatología.

## Reproducir

```bash
python3 validar_reducidas.py
python3 analizar_reducidas.py
python3 validar_metodo_tejido.py
```

Las imágenes reducidas están en `datos/reducidas/` y se excluyen de Git por tamaño. Los CSV, informes y figuras sí quedan en el proyecto.
