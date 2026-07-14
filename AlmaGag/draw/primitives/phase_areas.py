"""
Dibujo de ámbitos por fase (§I27), franjas de rol (§I30) y leyenda de roles.

Sólo se usa cuando el layout `hier` corrió en modo áreas (`layout.areas`).
- Cajas de fase: rectángulo punteado rotulado, de fondo.
- Rol por nodo: barra lateral de color en formas de caja, punto en rombos.
- Leyenda: franja inferior con un swatch + etiqueta por rol.
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

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
            font_size='12px', font_weight='700',
            font_family='Arial, sans-serif', fill=color))


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
                font_size='11.5px', font_family='Arial, sans-serif',
                fill='#1a1a1a', filter='url(#text-glow)'))


def draw_role_legend(dwg, roles, used_roles, canvas_width, canvas_height):
    """Leyenda de responsables en la franja inferior (solo roles usados)."""
    if not roles:
        return
    order = [k for k in roles if k in used_roles]
    if not order:
        return
    y = canvas_height - 30
    x = 24
    dwg.add(dwg.text('Responsable:', insert=(x, y + 11),
                     font_size='11px', font_weight='700',
                     font_family='Arial, sans-serif', fill='#5a5648'))
    x += 96
    for k in order:
        spec = roles[k]
        color = _svg_color(spec.get('color'))
        dwg.add(dwg.rect(insert=(x, y), size=(14, 14), rx=2, ry=2, fill=color))
        label = spec.get('label', k)
        dwg.add(dwg.text(label, insert=(x + 20, y + 11),
                         font_size='10.5px', font_family='Arial, sans-serif',
                         fill='#3a362c'))
        x += 40 + len(label) * 6.4
