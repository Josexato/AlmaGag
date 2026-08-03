"""
Primitivas SVG agnósticas al algoritmo.

Funciones de bajo nivel para construir SVG: crear el canvas, markers de
flecha, palette de colores, helper de wrapping de groups. No saben nada
sobre AUTO ni LAF ni qué representan los elementos a dibujar.

Cada algoritmo de layout tiene su propio renderer (AutoSVGRenderer,
LAFSVGRenderer) y orquesta estas primitivas a su manera.
"""

import colorsys
import copy
import logging
import xml.etree.ElementTree as ET

import svgwrite

from AlmaGag.config import FONT_SIZE_CONNECTION, FONT_SIZE_ZONE
from AlmaGag.draw.primitives.connections import draw_connection_line, draw_connection_label

logger = logging.getLogger('AlmaGag')


class DrawingGroupProxy:
    """Proxy que redirige add() a un Group manteniendo factory methods en Drawing.

    Se usa para envolver elementos SVG en <g> groups con <desc> metadata para
    etiquetas NdFn. Los factory methods (rect, text, linearGradient, defs, etc.)
    van al Drawing real, mientras que add() pone elementos en el group.
    """

    def __init__(self, dwg, group):
        self._dwg = dwg
        self._group = group

    def add(self, element):
        return self._group.add(element)

    def __getattr__(self, name):
        return getattr(self._dwg, name)


# §O50: atributos del halo blanco que lleva la copia inferior de cada <text>.
# Mismo trazo que tenía la regla `paint-order:stroke` global, pero como
# geometría SVG 1.1 (funciona en cairosvg/librsvg/Office, no sólo navegadores).
TEXT_HALO_ATTRS = {
    'class': 'ag-text-halo',
    'stroke': '#ffffff',
    'stroke-width': '3',
    'stroke-linejoin': 'round',
    'stroke-linecap': 'round',
    'fill': '#ffffff',
}

_SVG_NS = 'http://www.w3.org/2000/svg'


def _inject_text_halos_tree(root):
    """§O50 sobre un árbol ElementTree ya parseado (ver inject_text_halos)."""
    text_tag = f'{{{_SVG_NS}}}text'
    defs_tag = f'{{{_SVG_NS}}}defs'
    for parent in list(root.iter()):
        if parent.tag in (defs_tag, text_tag):
            continue
        for idx in range(len(parent) - 1, -1, -1):
            child = parent[idx]
            if child.tag != text_tag:
                continue
            halo = copy.deepcopy(child)
            halo.attrib.pop('id', None)
            halo.attrib.update(TEXT_HALO_ATTRS)
            parent.insert(idx, halo)


def inject_text_halos(svg_string):
    """§O50: materializa el halo de texto como geometría SVG 1.1.

    Por cada <text> del documento inserta, inmediatamente antes y en el mismo
    padre, una copia con trazo blanco (TEXT_HALO_ATTRS). El apilado resultante
    es idéntico al de `paint-order:stroke` (halo bajo el glifo, ambos sobre lo
    ya dibujado), pero sin depender de SVG2: cairosvg y librsvg —que pintan el
    stroke ENCIMA del fill— ya no borran las etiquetas al rasterizar.
    """
    root = ET.fromstring(svg_string)
    _inject_text_halos_tree(root)
    return _tostring_svg_default_ns(root)


def finalize_svg(svg_string):
    """Post-proceso único de emisión: halo portable (§O50) + viewBox al
    contenido (§O51). Parsea una sola vez y devuelve el XML final."""
    from AlmaGag.draw.primitives.viewbox import crop_viewbox
    root = ET.fromstring(svg_string)
    crop_viewbox(root)                 # antes del halo: menos nodos que medir
    _inject_text_halos_tree(root)
    return _tostring_svg_default_ns(root)


def _tostring_svg_default_ns(root):
    """Serializa con SVG como namespace por defecto SIN dejar estado global.

    `register_namespace` muta el mapa global de ElementTree; svgwrite también
    serializa con ElementTree y, con '' → SVG registrado de forma permanente,
    su root saldría con `xmlns` duplicado cuando el diagrama embebe iconos SVG
    (atributo literal + declaración inyectada). Registrar → serializar →
    restaurar mantiene el efecto local a esta llamada.
    """
    from xml.etree.ElementTree import _namespace_map
    saved = dict(_namespace_map)
    ET.register_namespace('', _SVG_NS)
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    ET.register_namespace('ev', 'http://www.w3.org/2001/xml-events')
    try:
        return ET.tostring(root, encoding='unicode')
    finally:
        _namespace_map.clear()
        _namespace_map.update(saved)


class PortableHaloDrawing(svgwrite.Drawing):
    """Drawing cuyo XML final pasa por el post-proceso de emisión: halo de
    texto §O50 + recorte de viewBox §O51.

    `save()`/`write()` de svgwrite pasan por `tostring()`, así que basta
    interceptarlo aquí: todo el pipeline dibuja normalmente y el post-proceso
    corre una única vez al emitir."""

    def tostring(self):
        return finalize_svg(super().tostring())


def create_canvas(output_path, canvas_width, canvas_height):
    """Crea el Drawing SVG con halo blanco universal para TODO el texto (H5+O50).

    En vez de un filtro gaussiano por-elemento (blur suave, y que había que
    recordar aplicar en cada `dwg.text` — los labels de contenedor y callout se
    quedaban sin él), el halo se materializa al emitir: cada <text> recibe una
    copia inferior con trazo blanco (ver `inject_text_halos`). Es geometría
    SVG 1.1 pura — antes era una regla `paint-order:stroke` global (SVG2) que
    cairosvg/librsvg no entienden y que volvía ilegibles las etiquetas en PNG.
    El id `text-glow` se conserva como filtro no-op por retrocompatibilidad
    (algún SVG viejo/embebido podía referenciarlo)."""
    dwg = PortableHaloDrawing(output_path, size=(canvas_width, canvas_height), debug=False)
    dwg.viewbox(0, 0, canvas_width, canvas_height)

    # Filtro heredado: neutro (feMerge de la fuente sola). Mantiene válidas las
    # referencias `url(#text-glow)` que aún queden sin duplicar el halo.
    text_glow = dwg.filter(id='text-glow', x='-20%', y='-20%', width='140%', height='140%')
    text_glow.feMerge(layernames=['SourceGraphic'])
    dwg.defs.add(text_glow)

    return dwg


def _generate_color_palette(n):
    """Genera N colores distinguibles vía HSL con hue uniformemente distribuido."""
    colors = []
    for i in range(n):
        hue = i / max(n, 1)
        r, g, b = colorsys.hls_to_rgb(hue, 0.45, 0.70)
        colors.append(f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}')
    return colors


# WISH-LAYOUT-007: paleta de colores por tipo semántico de conexión.
# El SDJF puede declarar `connection.semantic_type` y el color se asigna
# automáticamente. `connection.color` (hex/nombre CSS) tiene precedencia.
SEMANTIC_CONNECTION_COLORS = {
    'data_flow':    '#e8820c',  # naranja — flujo de datos
    'control_flow': '#1f6fd0',  # azul — flujo de control
    'sync':         '#1aa64b',  # verde — sincronización / bidireccional
    'event':        '#8e44ad',  # púrpura — eventos
    'callback':     '#0e8a8a',  # teal — callbacks
    'dependency':   '#888888',  # gris — dependencias
    'error':        '#cc2222',  # rojo — caminos de error
}


# §N48: etiquetas cortas para la leyenda de tipos de conexión.
SEMANTIC_TYPE_LABELS = {
    'data_flow':    'datos',
    'control_flow': 'control',
    'sync':         'sincronización',
    'event':        'eventos',
    'callback':     'callback',
    'dependency':   'dependencia',
    'error':        'error',
}


def draw_connection_type_legend(dwg, connections, canvas_width, canvas_height,
                                y_offset=0):
    """§N48: leyenda de tipos de conexión en la franja inferior.

    La semántica visual del .gag es CONTRATO: cuando un diagrama usa ≥3
    `semantic_type` distintos, el lector necesita el mapa tipo→color/estilo al
    pie. Cada swatch es una línea corta con el color efectivo del tipo (si
    todas sus conexiones comparten un override, ese; si no, el del mapa
    semántico) y su patrón de guiones si es uniforme. Con <3 tipos es un no-op
    (la leyenda estorbaría más de lo que aporta).
    """
    from AlmaGag.draw.primitives.connections import _dash_for

    by_type = {}
    for conn in connections:
        st = conn.get('semantic_type')
        if st:
            by_type.setdefault(st, []).append(conn)
    if len(by_type) < 3:
        return

    # Orden estable: primero los del mapa canónico, luego desconocidos (alfabético).
    known = [t for t in SEMANTIC_CONNECTION_COLORS if t in by_type]
    unknown = sorted(t for t in by_type if t not in SEMANTIC_CONNECTION_COLORS)
    order = known + unknown

    # §O51: la leyenda va anclada al borde inferior del CANVAS; el grupo con
    # esta clase se excluye del bbox de recorte y se reancla tras contraer.
    legend = dwg.g(class_='ag-bottom-anchored')
    y = canvas_height - 30 - y_offset
    x = 24
    legend.add(dwg.text('Enlaces:', insert=(x, y + 4),
                        font_size='11px', font_weight='700',
                        font_family='Arial, sans-serif', fill='#5a5648'))
    x += 66
    for st in order:
        conns = by_type[st]
        colors = {resolve_connection_color(c) for c in conns}
        color = colors.pop() if len(colors) == 1 else SEMANTIC_CONNECTION_COLORS.get(st)
        dashes = {_dash_for(c) for c in conns}
        dash = dashes.pop() if len(dashes) == 1 else None

        # start/end posicionales: svgwrite.Line SOBRESCRIBE x1..y2 pasados como
        # extra con sus defaults (0,0) — pasarlos sueltos deja el swatch en el
        # origen con longitud cero (invisible).
        line_attrs = {'stroke': color or '#333', 'stroke_width': 2.5}
        if dash:
            line_attrs['stroke_dasharray'] = dash
        legend.add(dwg.line(start=(x, y), end=(x + 26, y), **line_attrs))
        label = SEMANTIC_TYPE_LABELS.get(st, st)
        legend.add(dwg.text(label, insert=(x + 32, y + 4),
                            font_size=f'{FONT_SIZE_ZONE}px', font_family='Arial, sans-serif',
                            fill='#3a362c'))
        x += 58 + len(label) * 6.8
    dwg.add(legend)


def resolve_connection_color(conn):
    """
    Color de una conexión según WISH-LAYOUT-007.

    Prioridad:
    1. `conn['color']` (hex o nombre CSS) — override directo.
    2. `conn['semantic_type']` mapeado por SEMANTIC_CONNECTION_COLORS.
    3. None (el caller usa el default, típicamente negro).
    """
    if conn.get('color'):
        return conn['color']
    st = conn.get('semantic_type')
    if st:
        return SEMANTIC_CONNECTION_COLORS.get(st)
    return None


def _create_arrow_marker(dwg, marker_id, color, direction='end'):
    """Crea un marker de flecha triangular."""
    if direction == 'end':
        marker = dwg.marker(id=marker_id, insert=(10, 5), size=(10, 10), orient='auto')
        marker.add(dwg.path(d='M 0 0 L 10 5 L 0 10 z', fill=color))
    else:
        marker = dwg.marker(id=marker_id, insert=(0, 5), size=(10, 10), orient='auto')
        marker.add(dwg.path(d='M 10 0 L 0 5 L 10 10 z', fill=color))
    dwg.defs.add(marker)
    return marker


# Radio del punto de origen (círculo). En userSpaceOnUse es px absolutos:
# diámetro 2.4px = 20% más ancho que la línea (stroke-width 2).
CIRCLE_MARKER_R = 1.2


def _create_circle_marker(dwg, marker_id, color):
    """Crea un marker de círculo para origen de conexiones unidireccionales.

    Tamaño absoluto (userSpaceOnUse) para que NO escale con el stroke-width:
    un punto discreto, apenas más ancho que la línea.
    """
    r = CIRCLE_MARKER_R
    marker = dwg.marker(id=marker_id, insert=(r, r), size=(2 * r, 2 * r), orient='auto')
    marker['markerUnits'] = 'userSpaceOnUse'
    marker.add(dwg.circle(center=(r, r), r=r, fill=color))
    dwg.defs.add(marker)
    return marker


def setup_arrow_markers(dwg, connections=None, color_connections=False):
    """Crea markers SVG para flechas y círculos direccionales."""
    arrow_end = _create_arrow_marker(dwg, 'arrow-end', 'black', 'end')
    arrow_start = _create_arrow_marker(dwg, 'arrow-start', 'black', 'start')
    circle_start = _create_circle_marker(dwg, 'circle-start', 'black')
    circle_end = _create_circle_marker(dwg, 'circle-end', 'black')

    default_markers = {
        'arrow_end': arrow_end.get_funciri(),
        'arrow_start': arrow_start.get_funciri(),
        'circle_start': circle_start.get_funciri(),
        'circle_end': circle_end.get_funciri(),
        'forward': arrow_end.get_funciri(),
        'backward': arrow_start.get_funciri(),
        'bidirectional': (arrow_start.get_funciri(), arrow_end.get_funciri()),
    }

    if not connections:
        return default_markers

    # Determinar el color de cada conexión:
    # - color_connections=True → paleta arcoíris (un color único por conexión).
    # - si no, WISH-LAYOUT-007 → color por semantic_type/color declarado.
    if color_connections:
        colors = _generate_color_palette(len(connections))
    else:
        colors = [resolve_connection_color(c) for c in connections]
        # Si ninguna conexión declara color semántico, comportamiento clásico.
        if not any(colors):
            return default_markers

    per_connection = []
    for i, conn in enumerate(connections):
        color = colors[i]
        if not color:
            # Conexión sin color semántico → markers/stroke negros por defecto.
            per_connection.append({'markers': default_markers, 'color': 'black'})
            continue
        suffix = f'-c{i}'
        ae = _create_arrow_marker(dwg, f'arrow-end{suffix}', color, 'end')
        ast = _create_arrow_marker(dwg, f'arrow-start{suffix}', color, 'start')
        cs = _create_circle_marker(dwg, f'circle-start{suffix}', color)
        ce = _create_circle_marker(dwg, f'circle-end{suffix}', color)

        per_connection.append({
            'markers': {
                'arrow_end': ae.get_funciri(),
                'arrow_start': ast.get_funciri(),
                'circle_start': cs.get_funciri(),
                'circle_end': ce.get_funciri(),
                'forward': ae.get_funciri(),
                'backward': ast.get_funciri(),
                'bidirectional': (ast.get_funciri(), ae.get_funciri()),
            },
            'color': color,
        })

    return default_markers, per_connection


def ndfn_wrap(target, elem_id, ndfn_labels):
    """Wrap drawing target en un <g> con <desc> si existe etiqueta NdFn.

    Returns (draw_target, group_or_None). Si envuelve, el caller debe agregar
    group_or_None al dwg después de dibujar.
    """
    ndfn = ndfn_labels.get(elem_id, '')
    if not ndfn:
        return target, None
    g = target.g(id=f'ndfn-{elem_id}')
    g.set_desc(desc=f'{ndfn} | {elem_id}')
    return DrawingGroupProxy(target, g), g


def draw_connections(dwg, connections, elements_by_id, markers, per_conn_styles, ndfn_labels):
    """Dibuja todas las líneas de conexión (sin etiquetas).

    Retorna dict conn_centers: {key: (mid_x, mid_y)} para posicionar etiquetas después.
    """
    conn_centers = {}
    for i, conn in enumerate(connections):
        if per_conn_styles and i < len(per_conn_styles):
            conn_markers = per_conn_styles[i]['markers']
            conn_color = per_conn_styles[i]['color']
        else:
            conn_markers = markers
            conn_color = 'black'

        conn_ndfn_group = None
        draw_target = dwg
        if ndfn_labels:
            from_ndfn = ndfn_labels.get(conn['from'], conn['from'])
            to_ndfn = ndfn_labels.get(conn['to'], conn['to'])
            from_aaa = from_ndfn.split('.')[1] if '.' in from_ndfn else conn['from']
            to_aaa = to_ndfn.split('.')[1] if '.' in to_ndfn else conn['to']
            conn_id = f"conn-{from_aaa}-to-{to_aaa}"
            conn_ndfn_group = dwg.g(id=conn_id)
            label = conn.get('label', '')
            desc_text = f"From {from_ndfn} to {to_ndfn}"
            if label:
                desc_text += f" | {label}"
            conn_ndfn_group.set_desc(desc=desc_text)
            draw_target = DrawingGroupProxy(dwg, conn_ndfn_group)

        center = draw_connection_line(draw_target, elements_by_id, conn, conn_markers, stroke_color=conn_color)
        if conn_ndfn_group is not None:
            dwg.add(conn_ndfn_group)

        key = f"{conn['from']}->{conn['to']}"
        conn_centers[key] = center

    return conn_centers


def draw_connection_labels(dwg, connections, conn_centers,
                           optimized_label_positions=None, stored_centers=None):
    """Dibuja etiquetas de conexiones.

    Fuentes en orden de precedencia:
    1. `_label_anchor` (§G23, hier): ancla pegada al puerto de salida.
    2. `stored_centers` (WISH-LAYOUT-008): `layout.connection_labels`, la
       verdad medida por la pasada global §P61 — camino del motor único.
    3. `optimized_label_positions`: posiciones del LabelPositionOptimizer
       (sólo lo usa la estrategia `legacy`, congelada).
    4. centro geométrico del path dibujado (`conn_centers`).
    """
    for conn in connections:
        if not conn.get('label'):
            continue
        key = f"{conn['from']}->{conn['to']}"
        anchor = conn.get('_label_anchor')
        if anchor:
            dwg.add(dwg.text(
                conn['label'],
                insert=(anchor[0], anchor[1]),
                text_anchor="middle",
                font_size=f"{FONT_SIZE_CONNECTION}px",
                font_family="Arial, sans-serif",
                fill="#14181d",
            ))
            continue
        stored = stored_centers.get(key) if stored_centers else None
        if stored:
            draw_connection_label(dwg, conn, stored)
            continue
        optimized_pos = (optimized_label_positions or {}).get(key)
        if optimized_pos:
            dwg.add(dwg.text(
                conn['label'],
                insert=(optimized_pos.x, optimized_pos.y),
                text_anchor=optimized_pos.anchor,
                font_size=f"{FONT_SIZE_CONNECTION}px",
                font_family="Arial, sans-serif",
                fill="#14181d",
            ))
        else:
            # Fallback: centro de la conexión (default text_anchor del helper).
            center = conn_centers.get(key)
            if center:
                draw_connection_label(dwg, conn, center)
