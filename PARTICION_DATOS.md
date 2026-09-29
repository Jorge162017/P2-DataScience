# Partición por paciente para modelado

**Tema 22 · Mayo Clinic STRIP AI · 28 de septiembre de 2026**

Se dividieron los **632 pacientes** del entrenamiento oficial, manteniendo juntas todas las imágenes de cada paciente. La división es reproducible con semilla **22** y cuotas aproximadas de **70/15/15** por combinación de centro y etiqueta CE/LAA. El conjunto de prueba se reserva para una sola evaluación final; las decisiones de modelado se harán con entrenamiento y validación.

| Grupo | Pacientes | Imágenes | CE (pacientes) | LAA (pacientes) | Centros |
|---|---:|---:|---:|---:|---:|
| Entrenamiento | 440 | 519 | 319 | 121 | 11 |
| Validación | 97 | 121 | 69 | 28 | 11 |
| Prueba | 95 | 114 | 69 | 26 | 11 |

Las proporciones reales de pacientes son **69.6 % / 15.3 % / 15.0 %**. La clase LAA representa aproximadamente **27–29 %** de cada grupo. Las 754 imágenes aparecen exactamente una vez y ningún paciente aparece en dos grupos. No hay PNG idénticos por SHA-256 en el manifiesto.

## Cobertura por centro y clase

Ambas clases y los 11 centros están presentes en **cada** grupo. La [tabla completa](resultados/particion_centro_clase.csv) muestra los 22 estratos. Hay dos excepciones inevitables a la representación de *cada combinación* de centro y clase en los tres grupos:

- El centro **8** solo tiene **2 pacientes LAA**: uno quedó en entrenamiento y uno en validación; ninguno en prueba.
- El centro **9** solo tiene **2 pacientes LAA**: uno quedó en entrenamiento y uno en prueba; ninguno en validación.

Por ello, no se podrán calcular métricas CE/LAA fiables **por centro** para esos grupos pequeños. La comparación principal debe reportarse por paciente en el conjunto de prueba, junto con los tamaños de muestra y el intervalo de incertidumbre cuando corresponda. Las métricas por imagen o región no deben contarse como pacientes independientes.

## Archivos y reglas de uso

- [`datos/particion_pacientes.csv`](datos/particion_pacientes.csv): una fila por paciente, con centro, clase, grupo y número de imágenes.
- [`datos/particion_imagenes.csv`](datos/particion_imagenes.csv): una fila por imagen con ruta PNG y grupo heredado del paciente; usar este archivo para cargar imágenes en el modelado.
- [`resultados/particion_resumen.json`](resultados/particion_resumen.json): semilla, método, recuentos y huellas SHA-256 de los CSV de entrada.
- [`particionar_pacientes.py`](particionar_pacientes.py) genera la división. [`validar_particion.py`](validar_particion.py) comprueba cobertura, metadatos y ausencia de fuga de pacientes.

El EDA visual y su método de cribado de tejido se desarrollaron **antes** de fijar esta división y examinaron las 754 imágenes sin usar sus etiquetas para segmentar. A partir de aquí, cualquier ajuste de umbrales, selección de regiones, normalización, características, hiperparámetros o modelos debe hacerse **solo** con entrenamiento y validación. La prueba no se usa para tomar esas decisiones. Este antecedente se debe declarar al interpretar las métricas finales.

## Reproducir

```bash
python3 particionar_pacientes.py
python3 validar_particion.py
```

Si cambia `train.csv` o el manifiesto de imágenes, se debe regenerar la partición y repetir su validación antes de entrenar.
