# Entrenamiento y comparación de modelos

**Tema 22 · Mayo Clinic STRIP AI · 11 de octubre de 2026**

## Datos y protocolo

Se partió de las **754 imágenes de entrenamiento oficiales en versión PNG reducida**, vinculadas con **632 pacientes**. De ellas, 750 aportaron **5,933 recortes**. Dos pacientes de **entrenamiento** (`e72352` y `fd3079`) no tenían regiones suficientes; por eso los modelos regionales emplearon **438 pacientes para entrenar**, **97 para validar** y **95 para prueba**. Todos los pacientes de validación y prueba están representados. La partición original por paciente no se modificó.

De cada recorte se calcularon **57 características** de color, histogramas, intensidad y textura. Sus medias y desviaciones se agregaron por paciente para obtener **114 predictores**. `patient_id`, `center_id`, etiqueta y grupo no entraron como predictores. Esta agregación evita contar regiones correlacionadas como casos independientes.

Se ajustaron tres modelos: regresión logística, bosque aleatorio y SVM con núcleo RBF. La búsqueda de hiperparámetros usó **4 particiones estratificadas dentro del entrenamiento**, optimizando AUC ROC. Se probaron `C = 0.01, 0.1, 1, 10` para regresión logística; `min_samples_leaf = 2, 5, 10` para bosque; y `C = 0.1, 1, 10` para SVM. Se compararon los modelos ajustados en validación y se eligió el de **mayor AUC de validación** antes de evaluar prueba. También se incluyó una línea base que siempre predice CE.

## Comparación por paciente

**Clase positiva: LAA.** El umbral de clasificación fue 0.5 para todos los modelos. La exactitud balanceada promedia la sensibilidad de ambas clases; AUC ROC mide ordenamiento de probabilidades.

| Modelo | AUC validación | Exactitud balanceada validación | AUC prueba | Exactitud balanceada prueba | F1 LAA prueba |
|---|---:|---:|---:|---:|---:|
| Regresión logística | 0.608 | 0.565 | 0.528 | 0.549 | 0.405 |
| **Bosque aleatorio (elegido)** | **0.641** | 0.559 | **0.522** | 0.487 | 0.217 |
| SVM RBF | 0.575 | 0.500 | 0.461 | 0.500 | 0.000 |
| Siempre CE | 0.500 | 0.500 | 0.500 | 0.500 | 0.000 |

El bosque eligió `min_samples_leaf = 10` y alcanzó AUC medio **0.587** en validación cruzada de entrenamiento. Ganó por AUC en validación (0.641); en prueba su AUC fue **0.522**, con intervalo bootstrap del 95 % aproximado **0.391–0.654**. Su exactitud balanceada en prueba fue **0.487** (intervalo aproximado **0.401–0.579**). Entre los **69 pacientes CE y 26 LAA** de prueba, clasificó correctamente **54 CE y 5 LAA**; produjo **15 falsos positivos y 21 falsos negativos**. La sensibilidad LAA fue **19.2 %**.

Aunque la regresión logística obtuvo mejores F1 y exactitud balanceada en prueba, **no se cambia el ganador después de ver prueba**. Esa comparación es descriptiva. La exactitud total del bosque (62.1 %) incluso fue inferior a predecir siempre CE (72.6 %), razón por la que no debe presentarse como un clasificador eficaz ni como apoyo clínico. Estos resultados muestran que las características simples de color y textura de PNG reducidos **no generalizaron bien** al conjunto reservado.

Figuras: [comparación de métricas](resultados/figuras/modelos/comparacion_modelos.png), [curvas ROC](resultados/figuras/modelos/roc_prueba.png), [curvas precisión–sensibilidad](resultados/figuras/modelos/precision_recall_prueba.png) y [matriz de confusión](resultados/figuras/modelos/confusion_modelo_elegido.png). Los [valores completos](resultados/modelos/metricas_modelos.csv), [predicciones por paciente](resultados/modelos/predicciones_pacientes.csv) y [ajuste y límites](resultados/modelos/entrenamiento_resumen.json) permiten auditar la comparación. El [modelo guardado](modelos/modelo_elegido.joblib) es un prototipo exploratorio para la aplicación, con advertencia visible sobre su rendimiento.

## Límites que deben aparecer en la entrega final

- Son imágenes **reducidas**; el detalle fino de los TIFF originales no está disponible para los 632 pacientes.
- La máscara y el EDA visual examinaron las 754 imágenes antes de fijar la partición. Después de fijarla, la selección del modelo y los ajustes se hicieron con entrenamiento y validación; este antecedente debe declararse.
- La prueba contiene solo 26 pacientes LAA y no hay validación externa. Los intervalos de incertidumbre son amplios.
- Los dos pacientes de entrenamiento sin recortes quedaron excluidos únicamente de estos modelos regionales; siguen contabilizados en los datos originales.
- Las métricas se calcularon **por paciente**. No se deben reportar 5,933 regiones como si fueran 5,933 pacientes.

## Reproducir

```bash
python3 extraer_caracteristicas.py
python3 entrenar_modelos.py
```

La extracción lee los PNG locales en `datos/reducidas/`, que se descargan siguiendo el README. No se modificó el PDF de avance ya entregado.
