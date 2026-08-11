"""
Dibujo de ámbitos por fase (§I27), franjas de rol (§I30) y leyenda de roles.

Sólo se usa cuando el layout `hier` corrió en modo áreas (`layout.areas`).
- Cajas de fase: rectángulo punteado rotulado, de fondo.
- Rol por nodo: barra lateral de color en formas de caja, punto en rombos.
- Leyenda: franja inferior con un swatch + etiqueta por rol.
"""

from AlmaGag.config import (ICON_WIDTH, ICON_HEIGHT, FONT_SIZE_NODE,
                            FONT_SIZE_ZONE, FONT_WEIGHT_ZONE)

_DECISION_TYPES = {'decision', 'diamond'}
DEFAULT_AREA_COLOR = '#2a6fdb'
DEFAULT_ROLE_COLOR = '#7c786d'


def _svg_color(value, default=DEFAULT_ROLE_COLOR):
    """Devuelve un color SVG válido (hex o nombre CSS). svgwrite acepta ambos
    como string; los tuples de color_to_rgb NO son válidos como fill."""
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return 'rgb(%d,%d,%d)' % tuple(value)
    return value or default


def draw_area_boxes(dwg, areas):
    """Cajas de fase punteadas rotuladas (fondo). Las áreas implícitas
    (singletons sin etiqueta) no se dibujan."""
    for a in areas:
        if a.get('solo') or not a.get('label'):
            continue
        color = a.get('color') or DEFAULT_AREA_COLOR
        dwg.add(dwg.rect(
            insert=(a['x'], a['y']), size=(a['w'], a['h']),
            rx=8, ry=8, fill='#f7f9fc', fill_opacity=0.55,
            stroke=color, stroke_width=1.3, stroke_dasharray='6,4'))
        dwg.add(dwg.text(
            a['label'], insert=(a['x'] + 12, a['y'] + 18),
            font_size=f'{FONT_SIZE_ZONE}px', font_weight=FONT_WEIGHT_ZONE,
            font_family='Arial, sans-serif', fill=color))


def draw_lane_strips(dwg, lanes):
    """§I28: franjas verticales de carril (fondo) con rótulo de rol arriba.
    Alterna un tinte del color del carril para distinguir bandas."""
    for ln in lanes:
        color = _svg_color(ln.get('color'), DEFAULT_AREA_COLOR)
        dwg.add(dwg.rect(
            insert=(ln['x'], ln['y']), size=(ln['w'], ln['h']),
            fill=color, fill_opacity=0.07,
            stroke=color, stroke_width=1.0, stroke_opacity=0.5,
            stroke_dasharray='4,4'))
        if ln.get('label'):
            dwg.add(dwg.text(
                ln['label'], insert=(ln['x'] + ln['w'] / 2, ln['y'] + 18),
                text_anchor='middle', font_size=f'{FONT_SIZE_ZONE}px', font_weight=FONT_WEIGHT_ZONE,
                font_family='Arial, sans-serif', fill=color))


def draw_matrix_grid(dwg, matrix):
    """§I (matriz fase×rol): bandas de rol (filas, tinte de color) a lo ancho,
    rótulos de rol a la izquierda, rótulos de fase arriba y separadores de
    columna. El fondo se dibuja antes que los iconos."""
    left, top, w, h = matrix['left'], matrix['top'], matrix['w'], matrix['h']
    right = w - 8
    # filas (rol): banda tintada + rótulo a la izquierda
    for i, row in enumerate(matrix['rows']):
        color = _svg_color(row.get('color'), DEFAULT_AREA_COLOR)
        dwg.add(dwg.rect(
            insert=(left, row['y']), size=(right - left, row['h']),
            fill=color, fill_opacity=0.05 if i % 2 == 0 else 0.10,
            stroke=color, stroke_width=0.8, stroke_opacity=0.35))
        if row.get('label'):
            dwg.add(dwg.text(
                row['label'], insert=(left - 10, row['y'] + row['h'] / 2 + 4),
                text_anchor='end', font_size=f'{FONT_SIZE_ZONE}px', font_weight=FONT_WEIGHT_ZONE,
                font_family='Arial, sans-serif', fill=color))
    # columnas (fase): separadores + rótulo arriba
    for col in matrix['cols']:
        dwg.add(dwg.line(
            start=(col['x'], top), end=(col['x'], h - 8),
            stroke='#c9c4b6', stroke_width=1.0, stroke_dasharray='4,4'))
        if col.get('label'):
            dwg.add(dwg.text(
                col['label'], insert=(col['x'] + col['w'] / 2, top - 14),
                text_anchor='middle', font_size=f'{FONT_SIZE_ZONE}px', font_weight=FONT_WEIGHT_ZONE,
                font_family="'JetBrains Mono', monospace", fill='#2a6fdb'))
    dwg.add(dwg.line(start=(right, top), end=(right, h - 8),
                     stroke='#c9c4b6', stroke_width=1.0, stroke_dasharray='4,4'))


def draw_role_markers(dwg, elements, roles):
    """Marca el rol de cada nodo: barra lateral izq. en cajas, punto en rombos."""
    for e in elements:
        role = e.get('role')
        if not role or 'x' not in e:
            continue
        spec = (roles or {}).get(role, {})
        color = _svg_color(spec.get('color'))
        x, y = e['x'], e['y']
        if e.get('type') in _DECISION_TYPES:
            cx = x + ICON_WIDTH / 2
            dwg.add(dwg.circle(center=(cx - ICON_WIDTH * 0.28, y + ICON_HEIGHT / 2),
                               r=4, fill=color, stroke='white', stroke_width=0.8))
        else:
            dwg.add(dwg.rect(insert=(x, y), size=(6, ICON_HEIGHT),
                             rx=1, ry=1, fill=color))


def draw_area_node_labels(dwg, elements):
    """§I27: etiqueta CENTRADA bajo cada icono (multilínea por '\\n'), sin
    optimizador ni callouts — placement predecible dentro de la caja de fase."""
    for e in elements:
        lbl = e.get('label')
        if not lbl or 'x' not in e:
            continue
        cx = e['x'] + ICON_WIDTH / 2
        top = e['y'] + ICON_HEIGHT + 14
        for i, line in enumerate(lbl.split('\n')):
            dwg.add(dwg.text(
                line, insert=(cx, top + i * 16), text_anchor='middle',
                font_size=f'{FONT_SIZE_NODE}px', font_family='Arial, sans-serif',
                fill='#1a1a1a'))


def draw_role_legend(dwg, roles, used_roles, canvas_width, canvas_height):
    """Leyenda de responsables en la franja inferior (solo roles usados)."""
    if not roles:
        return
    order = [k for k in roles if k in used_roles]
    if not order:
        return
    # §O51: anclada al borde inferior del canvas — el grupo se excluye del
    # bbox de recorte del viewBox y se reancla tras contraer.
    legend = dwg.g(class_='ag-bottom-anchored')
    y = canvas_height - 30
    x = 24
    legend.add(dwg.text('Responsable:', insert=(x, y + 11),
                        font_size=f'{FONT_SIZE_ZONE}px', font_weight='700',
                        font_family='Arial, sans-serif', fill='#5a5648'))
    x += 96
    for k in order:
        spec = roles[k]
        color = _svg_color(spec.get('color'))
        legend.add(dwg.rect(insert=(x, y), size=(14, 14), rx=2, ry=2, fill=color))
        label = spec.get('label', k)
        legend.add(dwg.text(label, insert=(x + 20, y + 11),
                            font_size=f'{FONT_SIZE_ZONE}px', font_family='Arial, sans-serif',
                            fill='#3a362c'))
        x += 40 + len(label) * 6.8
    dwg.add(legend)


def draw_near_zones(dwg, elements):
    """§N46: caja sutil alrededor de cada zona `near` (grupo clusterizado).

    El bbox se calcula de las posiciones FINALES de los miembros (icono +
    espacio de etiqueta), así la caja sobrevive a cualquier ajuste posterior
    del pipeline. Estilo discreto de la misma familia que las cajas de fase.
    """
    from AlmaGag.layout.considerations import near_zone_boxes

    # §O54: la geometría (caja + banda de rótulo de 18px) viene del helper
    # compartido con el detector de colisiones — una sola verdad. El rótulo:
    # 11px bold #6b6558 (5.1:1 sobre el fondo de zona, AA; #8a8577 daba
    # 3.7:1), anclado al borde superior-izquierdo de SU caja, centrado
    # ópticamente en la banda reservada.
    for zone in near_zone_boxes(elements):
        x1, y1, x2, y2 = zone['bbox']
        dwg.add(dwg.rect(
            insert=(x1, y1), size=(x2 - x1, y2 - y1),
            rx=10, ry=10, fill='#f7f6f2', fill_opacity=0.5,
            stroke='#c9c4b6', stroke_width=1.2, stroke_dasharray='4,4'))
        if zone['label']:
            dwg.add(dwg.text(
                zone['label'], insert=(x1 + 10, y1 + 14),
                font_size=f'{FONT_SIZE_ZONE}px', font_weight=FONT_WEIGHT_ZONE,
                font_family='Arial, sans-serif', fill='#6b6558'))
