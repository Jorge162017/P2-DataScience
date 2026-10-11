# Selección de regiones con tejido

**Tema 22 · Actualizado el 11 de octubre de 2026**

Se aplicó la máscara del EDA visual a las **754 imágenes PNG reducidas**. La máscara se calcula en una vista de 280 px de ancho y se proyecta sobre recortes de **256 × 256 px** del PNG para estimar qué fracción contiene tejido visible. Se recorren posiciones cada **128 px**, se guardan hasta **8 regiones por imagen** y se evita que dos regiones seleccionadas se superpongan en más de **0.25 IoU**. Las coordenadas se guardan en [`datos/regiones_seleccionadas.csv`](datos/regiones_seleccionadas.csv); no se duplicaron miles de imágenes recortadas.

El mínimo de selección quedó en **8 % de tejido candidato por región**. El corte provisional de 20 % dejaba fuera tejido visible de dos imágenes **de entrenamiento** (`4ded24_0` y `c31442_0`); se bajó después de revisarlas. La máscara de tejido del EDA no cambió. Las imágenes de prueba no se usaron para elegir el nuevo corte.

## Resultado

| Conjunto | Regiones seleccionadas |
|---|---:|
| Entrenamiento | 4,081 |
| Validación | 958 |
| Prueba | 894 |
| **Total** | **5,933** |

Hay regiones en **750 de 754 imágenes** y en **630 de 632 pacientes**. Las cuatro imágenes sin región son `280c26_0`, `e26a04_0`, `e72352_0` y `fd3079_0`. Los pacientes `280c26` y `e26a04` sí tienen otra imagen con regiones. Solo **dos pacientes, ambos de entrenamiento** (`e72352` y `fd3079`), no aportan regiones al modelo basado en recortes. No se cambió su grupo de la partición ni se borraron del conjunto original. Todos los pacientes de validación y prueba tienen al menos una región utilizable según este cribado.

## Revisión de las siete imágenes con menos de 1 % de tejido global

| Imagen | Grupo | Mejor región | Seleccionadas | Observación visual |
|---|---|---:|---:|---|
| `280c26_0` | Entrenamiento | 4.2 % | 0 | Fragmentos muy tenues y una marca circular; otra imagen del paciente sí aporta regiones. |
| `4ded24_0` | Entrenamiento | 13.1 % | 3 | Tejido visible en fragmentos pequeños. |
| `c31442_0` | Entrenamiento | 9.2 % | 3 | Tejido visible en fragmentos pequeños. |
| `d4c955_0` | Prueba | 38.1 % | 8 | Tejido concentrado aunque la imagen completa es mayormente fondo. |
| `e26a04_0` | Prueba | 2.7 % | 0 | Señal pequeña y borrosa; otra imagen del paciente aporta regiones. |
| `e72352_0` | Entrenamiento | 4.3 % | 0 | Fragmento pequeño junto a una marca circular. |
| `fd3079_0` | Entrenamiento | 2.6 % | 0 | Fragmentos pálidos y pequeños. |

La revisión es técnica y visual, sin anotación histológica experta. Las dos [hojas de inspección](resultados/figuras/revision_baja_cobertura/baja_cobertura_01.jpg) muestran cada imagen, su máscara y el mejor recorte. La [muestra de 22 regiones de entrenamiento](resultados/figuras/regiones_seleccionadas_muestra.jpg) cubre los 11 centros y ambas etiquetas; sirve para comprobar que los recortes contienen material visible, no para inferir diferencias CE/LAA.

## Archivos y uso posterior

- [`datos/regiones_seleccionadas.csv`](datos/regiones_seleccionadas.csv): ruta PNG, paciente, grupo, coordenadas `x`/`y`, tamaño y cobertura estimada. Los modelos deben cargar el PNG y recortar con esas coordenadas.
- [`resultados/resumen_seleccion_regiones.csv`](resultados/resumen_seleccion_regiones.csv): cobertura y número de regiones por imagen, incluidos los cuatro casos sin región.
- [`resultados/seleccion_regiones.json`](resultados/seleccion_regiones.json): parámetros y recuentos.
- [`seleccionar_regiones.py`](seleccionar_regiones.py), [`validar_regiones.py`](validar_regiones.py) y [`revisar_baja_cobertura.py`](revisar_baja_cobertura.py): generación y validación reproducibles.

Las regiones de un mismo paciente están correlacionadas. En entrenamiento, la pérdida y el muestreo deben evitar que los pacientes con más imágenes o regiones dominen; en validación y prueba, las predicciones se deben **agregar por paciente** antes de calcular las métricas principales. El conjunto de prueba permanece reservado para la evaluación final. Los dos pacientes de entrenamiento sin regiones requieren una estrategia explícita si el modelo final debe cubrir a todos los pacientes, por ejemplo una vía de imagen completa; no deben desaparecer silenciosamente de los recuentos.

```bash
python3 seleccionar_regiones.py
python3 validar_regiones.py
python3 revisar_baja_cobertura.py
```
