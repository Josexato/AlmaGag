"""
SVGRenderer — encapsula la creación de elementos SVG para diagramas AlmaGag.

Extraído de generator.py para separar orquestación de renderizado.
"""
import colorsys
import logging

logger = logging.getLogger('AlmaGag')


class DrawingGroupProxy:
    """Proxy that redirects add() to a Group while delegating factory methods to Drawing.

    Used to wrap SVG elements in <g> groups with <desc> metadata for NdFn labels.
    Factory methods (rect, text, linearGradient, defs, etc.) go to the real Drawing,
    while add() puts elements into the group.
    """

    def __init__(self, dwg, group):
        self._dwg = dwg
        self._group = group

    def add(self, element):
        return self._group.add(element)

    def __getattr__(self, name):
        return getattr(self._dwg, name)


def _generate_color_palette(n):
    """Genera N colores distinguibles usando HSL con hue distribuido uniformemente."""
    colors = []
    for i in range(n):
        hue = i / max(n, 1)
        r, g, b = colorsys.hls_to_rgb(hue, 0.45, 0.70)
        colors.append(f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}')
    return colors


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


def _create_circle_marker(dwg, marker_id, color):
    """Crea un marker de círculo para el origen de conexiones unidireccionales."""
    marker = dwg.marker(id=marker_id, insert=(5, 5), size=(10, 10), orient='auto')
    marker.add(dwg.circle(center=(5, 5), r=4, fill=color))
    dwg.defs.add(marker)
    return marker


def setup_arrow_markers(dwg, connections=None, color_connections=False):
    """
    Crea los markers SVG para flechas y círculos direccionales.

    - Conexiones unidireccionales: círculo en origen, flecha en destino.
    - Conexiones bidireccionales: flechas en ambos extremos.
    - Si color_connections=True, cada conexión recibe un color distinto.

    Retorna:
        Si color_connections=False: dict global con markers negros.
        Si color_connections=True: (dict_global_fallback, list_per_connection)
           donde list_per_connection[i] = {'markers': {...}, 'color': hex_color}
    """
    # Markers negros por defecto (siempre se crean)
    arrow_end = _create_arrow_marker(dwg, 'arrow-end', 'black', 'end')
    arrow_start = _create_arrow_marker(dwg, 'arrow-start', 'black', 'start')
    circle_start = _create_circle_marker(dwg, 'circle-start', 'black')
    circle_end = _create_circle_marker(dwg, 'circle-end', 'black')

    default_markers = {
        'arrow_end': arrow_end.get_funciri(),
        'arrow_start': arrow_start.get_funciri(),
        'circle_start': circle_start.get_funciri(),
        'circle_end': circle_end.get_funciri(),
        # Compat keys legacy
        'forward': arrow_end.get_funciri(),
        'backward': arrow_start.get_funciri(),
        'bidirectional': (arrow_start.get_funciri(), arrow_end.get_funciri()),
    }

    if not color_connections or not connections:
        return default_markers

    # Generar markers coloreados por conexión
    n = len(connections)
    palette = _generate_color_palette(n)
    per_connection = []

    for i, conn in enumerate(connections):
        color = palette[i]
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
                # Compat keys legacy
                'forward': ae.get_funciri(),
                'backward': ast.get_funciri(),
                'bidirectional': (ast.get_funciri(), ae.get_funciri()),
            },
            'color': color,
        })

    return default_markers, per_connection
