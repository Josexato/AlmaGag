"""
AlmaGag.draw.icons

Este módulo centraliza la lógica para renderizar íconos SVG en el sistema GAG.
Permite dibujar diferentes tipos de elementos de red basados en su `type`,
delegando la representación gráfica a módulos individuales (uno por tipo).

Si el tipo no se encuentra o el dibujo falla, se renderiza un plátano con cinta
(ícono por defecto que indica ambigüedad o tipo no reconocido).

Autor: José + ALMA 🧠
Fecha: 2025-07-06
"""

import importlib


def draw_icon(dwg, element):
    """
    Dibuja un ícono en el canvas SVG a partir de los datos del elemento.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto de dibujo SVG.
        element (dict): Elemento con las claves:
            - 'x' (int): coordenada X del ícono.
            - 'y' (int): coordenada Y del ícono.
            - 'type' (str): tipo del ícono ('server', 'cloud', etc).
            - 'label' (str, opcional): texto a mostrar debajo.
            - 'color' (str, opcional): color de relleno (por defecto: 'gray').

    Comportamiento:
        - Si el tipo es válido y el módulo correspondiente existe:
            → llama a draw_<type>(dwg, x, y, color).
        - Si el tipo no existe o hay error:
            → se dibuja el ícono por defecto (plátano con cinta).

    Ejemplo de uso:
        draw_icon(dwg, {
            "type": "server",
            "x": 100,
            "y": 150,
            "label": "Servidor 1",
            "color": "lightblue"
        })
    """
    x = element['x']
    y = element['y']
    label = element.get('label', '')
    elem_type = element.get('type', 'unknown')
    color = element.get('color', 'gray')

    try:
        # Intentar importar el módulo de dibujo específico según tipo
        module = importlib.import_module(f'AlmaGag.draw.{elem_type}')
        draw_func = getattr(module, f'draw_{elem_type}')
        draw_func(dwg, x, y, color)
    except Exception as e:
        print(f"[WARN] No se pudo dibujar '{elem_type}', se usará ícono por defecto. Error: {e}")
        from AlmaGag.draw.bwt import draw_bwt
        draw_bwt(dwg, x, y)

    # Renderizar texto debajo del ícono (admite múltiples líneas)
    lines = label.split('\n')
    for i, line in enumerate(lines):
        dwg.add(dwg.text(
            line,
            insert=(x + 40, y + 70 + (i * 18)),  # Posición centrada
            text_anchor="middle",
            font_size="14px",
            fill="black"
        ))
