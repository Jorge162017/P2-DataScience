"""Exporta un resumen del EDA visual completo en PDF."""

import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
FIG = ROOT / "resultados/figuras"
OUT = ROOT / "EDA_Visual_Proyecto2.pdf"
PAGE = fitz.paper_rect("a4")
NAVY = (0.12, 0.21, 0.31)
GRAY = (0.25, 0.29, 0.32)


def write(page, x, y, width, height, content, size=10.5, bold=False, color=GRAY):
    result = page.insert_textbox(fitz.Rect(x, y, x + width, y + height), content,
                                 fontsize=size, fontname="hebo" if bold else "helv",
                                 color=color, lineheight=1.24)
    if result < 0:
        raise ValueError(f"No cabe el texto: {content[:50]}")


def image(page, name, rect):
    path = FIG / name
    page.insert_image(rect, filename=str(path), keep_proportion=True)


def footer(page, number):
    page.draw_line((45, 800), (550, 800), color=(.8, .84, .86))
    write(page, 45, 807, 450, 18, "CC3084 | Tema 22 | 28 septiembre 2026", 8.5)
    write(page, 515, 807, 35, 18, str(number), 8.5)


def main():
    eda = json.loads((ROOT / "resultados/eda_reducidas_resumen.json").read_text())
    validation = json.loads((ROOT / "resultados/validacion_metodo_tejido.json").read_text())
    doc = fitz.open()

    page = doc.new_page(width=PAGE.width, height=PAGE.height)
    page.draw_rect(fitz.Rect(0, 0, PAGE.width, 117), fill=NAVY, color=NAVY)
    write(page, 45, 34, 510, 38, "EDA visual del conjunto completo", 22, True, (1, 1, 1))
    write(page, 45, 79, 510, 22, "Mayo Clinic STRIP AI | origen de coágulos CE / LAA", 11,
          color=(.9, .94, .98))
    write(page, 45, 140, 505, 28, "Datos y método", 15, True, NAVY)
    write(page, 45, 170, 505, 105,
          "Se analizaron 754 PNG reducidos de 632 pacientes y 11 centros: 547 CE y 207 LAA. "
          "Cada imagen se vinculó con su image_id y patient_id oficial. Para localizar material "
          "visible se redujo cada imagen a 280 px de ancho, se estimó su color de fondo en "
          "zonas uniformes del borde y se exigió diferencia de color y textura local. "
          "Las medidas describen las imágenes y no son etiquetas clínicas.")
    write(page, 45, 289, 505, 28, "Resultados descriptivos", 15, True, NAVY)
    write(page, 45, 320, 505, 95,
          "La fracción mediana de píxeles candidatos a tejido fue 12.45 %; la mitad central "
          "de las imágenes se ubicó entre 8.27 % y 17.66 %. Siete imágenes quedaron por "
          "debajo de 1 % y requieren revisión antes de usarlas en un modelo. La mediana "
          "varió entre centros, de 3.74 % en el centro 8 a 21.10 % en el centro 4. "
          "Estas diferencias pueden obedecer a preparación o captura.")
    image(page, "reducidas_cobertura_tejido.png", fitz.Rect(45, 443, 550, 695))
    write(page, 45, 712, 505, 64,
          "La cobertura por clase y centro es descriptiva. Las imágenes de un mismo paciente "
          "no son observaciones independientes; estos gráficos no prueban diferencias "
          "biológicas entre CE y LAA.", 9.5)
    footer(page, 1)

    page = doc.new_page(width=PAGE.width, height=PAGE.height)
    write(page, 45, 38, 505, 32, "Variación técnica y revisión de máscaras", 18, True, NAVY)
    image(page, "reducidas_color_textura.png", fitz.Rect(45, 90, 550, 370))
    write(page, 45, 386, 505, 81,
          "Se revisaron visualmente 61 pares de imagen y máscara, seleccionados por clase, "
          "centro y valores extremos. Las masas visibles de tejido quedaron mayormente "
          "marcadas; las zonas amplias de fondo uniforme, incluso de colores, quedaron "
          "excluidas. El tejido muy pálido, los fragmentos diminutos y los bordes requieren "
          "cautela porque se trabaja con vistas reducidas.", 10.5)
    write(page, 45, 485, 505, 28, "Comparación con la regla de la primera fase", 15, True, NAVY)
    write(page, 45, 518, 505, 90,
          f"La regla anterior superó la nueva en más de 25 puntos porcentuales en "
          f"{validation['anterior_excede_base_25_puntos_en_imagenes']} imágenes, "
          "sobre todo por fondos teñidos. Con umbrales más permisivos y estrictos, "
          "la mediana de cobertura cambió de 12.80 % a 12.03 % alrededor del 12.45 % "
          "base. Esta estabilidad no mide exactitud: no hay máscaras manuales de referencia.")
    image(page, "reducidas_comparacion_mascaras.png", fitz.Rect(45, 610, 550, 752))
    write(page, 45, 760, 505, 28,
          "Ejemplo caf901_0: la regla previa marca 99.99 %; la nueva, 3.45 %.", 9)
    footer(page, 2)

    doc.set_metadata({"title": "EDA visual - Proyecto 2 - Tema 22", "author": "Jorge Luis Lopez"})
    doc.save(OUT, garbage=4, deflate=True)
    doc.close()
    print(OUT)


if __name__ == "__main__":
    main()
