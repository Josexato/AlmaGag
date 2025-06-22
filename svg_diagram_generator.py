import json
import os
import sys
import svgwrite

# === CONFIGURACIONES GENERALES ===
WIDTH = 1400
HEIGHT = 900
ICON_WIDTH = 80
ICON_HEIGHT = 50
# === FUNCIÓN: Dibujar el plátano con cinta adhesiva ===
def draw_bwt(dwg, x, y):
    """
    Dibuja un aleph como ícono hardcodeado.
    """
    dwg.add(dwg.path(
        d=f"M{x+10},{y+40} Q{x+40},{y} {x+70},{y+40} "
          f"Q{x+75},{y+50} {x+40},{y+55} Q{x+5},{y+50} {x+10},{y+40} Z",
        fill="yellow",
        stroke="black",
        stroke_width=2
    ))

    dwg.add(dwg.path(
        d=f"M{x+20},{y+38} Q{x+40},{y+10} {x+60},{y+38} "
          f"Q{x+62},{y+42} {x+40},{y+47} Q{x+18},{y+44} {x+20},{y+38} Z",
        fill="#eeeeee",
        stroke="black",
        stroke_width=1
    ))

    # Cinta adhesiva (más ancha y en ángulo fuerte)
    dwg.add(dwg.rect(
        insert=(x+35, y+30),
        size=(40, 14),
        fill="gray",
        stroke="black",
        transform=f"rotate(-35,{x+55},{y+37})"
    ))


# === FUNCIÓN: Dibujar un ícono ===
def draw_icon(dwg, element):
    """
    Dibuja un ícono en el SVG basado en el tipo de elemento, usando el color especificado si existe.
    Además, permite múltiples líneas en el texto del label.
    """
    x = element['x']
    y = element['y']
    label = element.get('label', '')
    elem_type = element.get('type', 'unknown')
    color = element.get('color', 'gray')  # Usa el color del JSON o gris por defecto

    # Si el tipo no es reconocido, dibujar el plátano
    tipos_validos = ['server', 'firewall', 'building', 'cloud']
    if elem_type not in tipos_validos:
        draw_bwt(dwg, x, y)
    else:
        # Si es tipo conocido, dibujar normalmente
        if elem_type == 'cloud':
            dwg.add(dwg.ellipse(center=(x + ICON_WIDTH/2, y + ICON_HEIGHT/2),
                                r=(ICON_WIDTH/2, ICON_HEIGHT/2),
                                fill=color, stroke='black'))
        else:
            dwg.add(dwg.rect(insert=(x, y),
                             size=(ICON_WIDTH, ICON_HEIGHT),
                             fill=color, stroke='black'))

    # Dibujar el texto debajo del ícono (permitiendo saltos de línea)
    lines = label.split('\n')  # Separa en varias líneas si hay "\n"
    for i, line in enumerate(lines):
        dwg.add(dwg.text(
            line,
            insert=(x + ICON_WIDTH/2, y + ICON_HEIGHT + 20 + (i * 18)),  # Desfasar cada línea hacia abajo
            text_anchor="middle",
            font_size="14px",
            fill="black"
        ))

# === FUNCIÓN: Dibujar una conexión ===
def draw_connection(dwg, elements_by_id, connection):
    from_elem = elements_by_id[connection['from']]
    to_elem = elements_by_id[connection['to']]

    x1 = from_elem['x'] + ICON_WIDTH / 2
    y1 = from_elem['y'] + ICON_HEIGHT / 2
    x2 = to_elem['x'] + ICON_WIDTH / 2
    y2 = to_elem['y'] + ICON_HEIGHT / 2

    dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), stroke="black", stroke_width=2))

    if 'label' in connection:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        dwg.add(dwg.text(connection['label'], insert=(mid_x, mid_y - 10), text_anchor="middle", font_size="12px", fill="gray"))

# === FUNCIÓN PRINCIPAL ===
def generate_diagram(json_file):
    """
    Genera el SVG tomando automáticamente el nombre del JSON como base.
    """
    if not os.path.exists(json_file):
        print(f"[ERROR] Archivo no encontrado: {json_file}")
        return

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Error al leer el JSON: {e}")
        return

    # Crear nombre de salida .svg basado en el .json
    base_name = os.path.splitext(os.path.basename(json_file))[0]
    output_svg = f"{base_name}.svg"

    # Crear SVG
    dwg = svgwrite.Drawing(output_svg, size=(WIDTH, HEIGHT))
    elements_by_id = {elem['id']: elem for elem in data.get('elements', [])}

    for conn in data.get('connections', []):
        draw_connection(dwg, elements_by_id, conn)

    for elem in data.get('elements', []):
        draw_icon(dwg, elem)

    dwg.save()
    print(f"[OK] Diagrama generado exitosamente: {output_svg}")


    # === FUNCIÓN: Dibujar el plátano con cinta adhesiva ===
    def draw_banana_placeholder(dwg, x, y):
        """
        Dibuja una caja amarilla con un plátano y una cinta adhesiva.
        Usado como placeholder cuando el tipo no es reconocido.
        """
        # Dibujar el fondo de la caja
        dwg.add(dwg.rect(insert=(x, y), size=(ICON_WIDTH, ICON_HEIGHT), fill='lightyellow', stroke='black'))

        # Dibujar el plátano (una curva dorada)
        banana = dwg.path(
            d=f'M{x+20},{y+40} Q{x+40},{y} {x+60},{y+40}',
            fill='none',
            stroke='gold',
            stroke_width=5
        )
        dwg.add(banana)

        # Dibujar la cinta adhesiva (un rectángulo gris rotado)
        tape = dwg.rect(
            insert=(x+35, y+30),
            size=(20, 10),
            fill='gray',
            stroke='black',
            transform=f"rotate(-30,{x+45},{y+35})"
        )
        dwg.add(tape)


# === EJECUCIÓN ===
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python svg_diagram_generator.py archivo.json")
    else:
        generate_diagram(sys.argv[1])
