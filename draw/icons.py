from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.bwt import draw_bwt

def draw_icon(dwg, element):
    x, y = element['x'], element['y']
    label = element.get('label', '')
    tipo = element.get('type', 'unknown')
    color = element.get('color', 'gray')

    tipos_validos = ['server', 'firewall', 'building', 'cloud']
    if tipo not in tipos_validos:
        draw_bwt(dwg, x, y)
    else:
        if tipo == 'cloud':
            dwg.add(dwg.ellipse(center=(x + ICON_WIDTH/2, y + ICON_HEIGHT/2),
                                r=(ICON_WIDTH/2, ICON_HEIGHT/2),
                                fill=color, stroke='black'))
        else:
            dwg.add(dwg.rect(insert=(x, y), size=(ICON_WIDTH, ICON_HEIGHT),
                             fill=color, stroke='black'))

    for i, line in enumerate(label.split('\n')):
        dwg.add(dwg.text(line,
                         insert=(x + ICON_WIDTH/2, y + ICON_HEIGHT + 20 + (i * 18)),
                         text_anchor="middle",
                         font_size="14px",
                         fill="black"))

def draw_connection(dwg, elements_by_id, connection):
    from_e = elements_by_id[connection['from']]
    to_e = elements_by_id[connection['to']]

    x1 = from_e['x'] + ICON_WIDTH / 2
    y1 = from_e['y'] + ICON_HEIGHT / 2
    x2 = to_e['x'] + ICON_WIDTH / 2
    y2 = to_e['y'] + ICON_HEIGHT / 2

    dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), stroke="black", stroke_width=2))
    if 'label' in connection:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        dwg.add(dwg.text(connection['label'], insert=(mid_x, mid_y - 10),
                         text_anchor="middle", font_size="12px", fill="gray"))
