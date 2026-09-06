# Hallazgos calculados del EDA

## Metadatos y unidad de análisis

- Se analizaron **754 registros, 5 variables, 632 pacientes y 11 centros**.
- Por imagen: CE **547 (72.55%)** y LAA **207 (27.45%)**. Por paciente: CE **457 (72.31%)** y LAA **175 (27.69%)**. Existe desbalance descriptivo; la frecuencia de esta muestra no es prevalencia poblacional.
- Hay **89 pacientes con más de una imagen**, hasta 5 imágenes. Las observaciones del mismo paciente no son independientes. Una eventual división para modelos debe agrupar por paciente.
- Se encontraron **0 nulos** después de normalizar y se eliminaron **0 duplicados exactos**. No se imputaron etiquetas ni identificadores. Los originales se conservan.
- Los códigos de centro e identificadores no son medidas clínicas continuas: no se interpretan promedios ni correlaciones numéricas de sus códigos.

## Relaciones entre variables

- La proporción CE por paciente va de **50.00% (centro 3)** a **87.50% (centro 8)**. La tabla de conteos permite valorar los distintos tamaños por centro. Es una asociación descriptiva compatible con diferencias de selección de casos; no demuestra que el centro cause la etiología.
- La mediana de imágenes por paciente es **1**. Q1 y Q3 son 1 y 1; IQR=0 hace que la regla de Tukey marque las repeticiones como atípicas. Se conservan porque son observaciones válidas, no errores demostrados.

## Imágenes disponibles y calidad

- Se analizaron **6 archivos derivados locales**, no las WSI originales. Solo **3** coinciden con `train.csv` (**0.40%** de los identificadores del CSV); esos recortes corresponden a **3 pacientes**, todos del centro **11**.
- Los identificadores **02ebd5_0, 0412ab_0, 08b8ef_0** no aparecen en el CSV. Se mantienen sin etiqueta; no se les asigna CE, LAA, `Unknown` ni `Other` por apariencia o por similitud del nombre.
- Las vistas PNG y los recortes JPG tienen preparaciones y escalas distintas. No se considera que sean una muestra aleatoria ni comparable de toda la colección.
- La cuadrícula de 128 × 128 píxeles generó **1038 tiles candidatos**, de los que **806** superaron los filtros y **232** quedaron rechazados. No se insertan recortes de respaldo que incumplan los filtros. Las coordenadas corresponden a los archivos locales.
- La regla IQR dentro de cada imagen señala **110 tiles aceptados** en al menos una métrica de calidad. Permanecen disponibles para revisión; no se borran por ser extremos. Los bordes, la compresión y las transiciones tejido/fondo pueden producir valores altos del Laplaciano.

## Alcance de las conclusiones

Se han caracterizado el desbalance, las repeticiones por paciente, la composición por centro y la variabilidad técnica de las imágenes disponibles. Las métricas de color, entropía y nitidez describen píxeles; no miden directamente eritrocitos, plaquetas o fibrina. Las correlaciones se calculan entre tiles dentro de cada imagen y no prueban relación causal ni poder diagnóstico.

**Dos pacientes CE y uno LAA, todos del mismo centro, no permiten establecer diferencias generales entre etiologías ni validar un clasificador.** No se entrenó un modelo ni se informan métricas predictivas. Más tiles no aumentan el número de pacientes.

Los siguientes pasos son ampliar la muestra con imágenes de identificación verificable y varios centros, documentar escala y tinción, revisar manualmente las máscaras y evaluar el efecto de los filtros. Si después se pide modelado, separar pacientes y revisar sesgo por centro. Estos resultados delimitan el alcance del análisis exploratorio.
