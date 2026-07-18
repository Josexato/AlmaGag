"""
Epifanía agnóstica del motor — grabador de fases (WISH-ARCH-002, paso 2).

Epifanía es el *concepto*: ver cómo NACE la abstracción del layout, fase por
fase. La estrategia `legacy` tiene su propia Epifanía "de lujo"
(`strategies/legacy/epifania/`), que dibuja los internos VC/SCC/centralidad que
sólo ese motor histórico conoce. Este módulo es la Epifanía **agnóstica del
motor**: un grabador que NO sabe nada de ninguna estrategia — sólo hace una foto
(`deepcopy`) del layout en cada fase del pipeline y luego re-renderiza cada foto
con el *renderer real* de la estrategia. Así funciona igual para AUTO, hier o
cualquier motor futuro: la salida es un "flipbook" del layout real naciendo
etapa a etapa (la última foto es byte-idéntica al SVG final).

Uso (desde `LayoutEngine`):

    rec = PhaseRecorder(diagram_name, strategy_label='auto', enabled=True)
    strategy.recorder = rec               # las estrategias emiten rec.capture(...)
    result = strategy.optimize(layout)
    rec.render_all(strategy.renderer)      # una SVG por fase + index.html

Las estrategias emiten fases con `self._capture(label, layout, note)` (helper de
`LayoutOptimizer`), que es un no-op cero-costo si no hay grabador conectado.
"""

import os
import re
import logging
from copy import deepcopy

from AlmaGag.layout.metrics import count_crossings, quality_counters

logger = logging.getLogger('AlmaGag')


def _collision_points(snap):
    """§H9: puntos (x,y) donde el detector marca colisiones en esta fase, para
    dibujarlos como círculos rojos sobre el thumbnail (chip ✕N verificable de un
    vistazo). Tolerante a fallos: devuelve [] si algo no está disponible."""
    try:
        from AlmaGag.layout.collision import CollisionDetector
        from AlmaGag.layout.geometry import GeometryCalculator
        sizing = getattr(snap, 'sizing', None)
        geo = GeometryCalculator(sizing) if sizing else GeometryCalculator()
        _, pairs = CollisionDetector(geo).detect_all_collisions(snap)
    except Exception:
        return []

    by_id = getattr(snap, 'elements_by_id', {}) or {}
    labels = getattr(snap, 'label_positions', {}) or {}

    def _pt(token):
        # token puede ser id de elemento, "a->b" (conexión) o id con label
        if isinstance(token, str) and '->' in token:
            a, b = token.split('->', 1)
            pa, pb = _pt(a), _pt(b)
            if pa and pb:
                return ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            return pa or pb
        e = by_id.get(token)
        if e and 'x' in e and 'y' in e:
            w = e.get('width', 80)
            h = e.get('height', 50)
            return (e['x'] + w / 2, e['y'] + h / 2)
        if token in labels:
            p = labels[token]
            return (p[0], p[1])
        return None

    points = []
    for pair in pairs:
        if len(pair) < 2:
            continue
        p = _pt(pair[0]) or _pt(pair[1])
        if p:
            points.append(p)
    return points


def _overlay_collision_markers(svg_path, points):
    """Inyecta círculos rojos semitransparentes en los puntos de colisión antes
    de </svg>. No-op si no hay puntos o el archivo no se puede leer."""
    if not points:
        return
    try:
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg = f.read()
        marks = ''.join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="#e5484d" '
            f'fill-opacity="0.35" stroke="#c00" stroke-width="1.5"/>'
            for (x, y) in points
        )
        svg = svg.replace('</svg>', f'<g class="epifania-colisiones">{marks}</g></svg>', 1)
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg)
    except OSError:
        return


def _slug(text: str) -> str:
    """Nombre de archivo seguro a partir de una etiqueta de fase."""
    s = re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')
    return s or 'fase'


class PhaseRecorder:
    """Graba fases del pipeline y las re-renderiza con el renderer de la estrategia.

    Es un observador pasivo: la estrategia decide *qué* fases marcar (llamando a
    `capture`); el grabador sólo guarda una foto profunda de cada una y, al
    final, las dibuja en orden. No conoce ni depende de ninguna estrategia.
    """

    def __init__(self, diagram_name: str, strategy_label: str = '',
                 output_dir: str = 'debug/epifania', enabled: bool = False):
        self.diagram_name = diagram_name or 'diagram'
        self.strategy_label = strategy_label
        self.output_dir = output_dir
        self.enabled = enabled
        self._snaps = []   # lista de (label, note, layout_snapshot)

    def capture(self, label: str, layout, note: str = '') -> None:
        """Guarda una foto (deepcopy) del layout en esta fase. No-op si off."""
        if not self.enabled:
            return
        try:
            snap = deepcopy(layout)
        except Exception as e:   # una fase no-copiable no debe romper el layout
            logger.warning(f"[EPIFANIA] no se pudo capturar la fase '{label}': {e}")
            return
        self._snaps.append((label, note, snap))

    def render_all(self, renderer) -> str:
        """Renderiza cada fase capturada a un SVG + un index.html de contacto.

        Cada foto se dibuja con el `renderer` real de la estrategia, así que la
        última fase coincide con el SVG final. Un render que falle (fase
        intermedia sin computed_path, p.ej.) se saltea con un warning; no aborta
        el resto. Devuelve el directorio de salida (o None si no hubo fases)."""
        if not self.enabled or not self._snaps:
            return None
        out_dir = os.path.join(self.output_dir, self.diagram_name)
        os.makedirs(out_dir, exist_ok=True)

        pages = []
        for i, (label, note, snap) in enumerate(self._snaps, 1):
            fname = f"{i:02d}_{_slug(label)}.svg"
            path = os.path.join(out_dir, fname)
            try:
                renderer.render(snap, path)
            except Exception as e:
                logger.warning(f"[EPIFANIA] fase {i} '{label}' no renderizó: {e}")
                continue
            # Métricas de calidad por fase: los 3 contadores §H6 (se ven bajar a
            # lo largo del flipbook) + marcado de colisiones sobre el thumbnail
            # (§H9: el chip deja de ser un número a ciegas — se ve DÓNDE están).
            try:
                q = quality_counters(snap)
            except Exception:
                q = None
            try:
                _overlay_collision_markers(path, _collision_points(snap))
            except Exception:
                pass
            crossings = q['edge_x_edge'] if q else None
            pages.append((i, label, note, fname, crossings, q))

        self._write_index(out_dir, pages)
        logger.info(f"[EPIFANIA] {len(pages)} fase(s) de '{self.strategy_label}' "
                    f"en {out_dir}/ (abrir index.html)")
        return out_dir

    def _write_index(self, out_dir: str, pages) -> None:
        """Hoja de contacto: una página que muestra el flipbook en orden."""
        title = f"Epifanía · {self.diagram_name} · motor «{self.strategy_label}»"
        cards = []
        prev_cross = None
        for i, label, note, fname, crossings, q in pages:
            note_html = f'<p class="note">{_esc(note)}</p>' if note else ''
            counters_html = _counters_badge(q)
            cards.append(
                f'<figure><figcaption><span class="n">{i:02d}</span> '
                f'{_esc(label)}{_cross_badge(crossings, prev_cross)}</figcaption>'
                f'<a href="{fname}" target="_blank"><img src="{fname}" '
                f'alt="{_esc(label)}"></a>{counters_html}{note_html}</figure>'
            )
            if crossings is not None:
                prev_cross = crossings
        html = _INDEX_TMPL.format(
            title=_esc(title),
            subtitle=f"{len(pages)} fases — así nace el layout, paso a paso "
                     f"(el chip muestra cruces entre conexiones por fase)",
            cards='\n'.join(cards),
        )
        with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)


def _counters_badge(q) -> str:
    """§H6/§H9: fila con los tres contadores separados bajo el thumbnail."""
    if not q:
        return ''
    return (f'<p class="counters">'
            f'<span title="cruces arista×arista">✕ {q["edge_x_edge"]}</span>'
            f'<span title="aristas sobre nodo/contenedor ajeno">▦ {q["edge_x_node"]}</span>'
            f'<span title="solapes de etiqueta">🅰 {q["label_overlap"]}</span></p>')


def _cross_badge(crossings, prev) -> str:
    """Chip HTML con los cruces de la fase y el delta contra la fase anterior."""
    if crossings is None:
        return ''
    delta = ''
    if prev is not None and crossings != prev:
        d = crossings - prev
        cls = 'up' if d > 0 else 'down'
        delta = f' <span class="d {cls}">{d:+d}</span>'
    return f' <span class="x" title="cruces entre conexiones">✕ {crossings}{delta}</span>'


def _esc(text: str) -> str:
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


_INDEX_TMPL = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, sans-serif; margin: 2rem; background: Canvas; color: CanvasText; }}
  h1 {{ font-size: 1.15rem; margin: 0 0 .2rem; }}
  .sub {{ color: GrayText; margin: 0 0 1.5rem; font-size: .9rem; }}
  .grid {{ display: grid; gap: 1.2rem; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
  figure {{ margin: 0; border: 1px solid GrayText; border-radius: 8px; overflow: hidden; background: Canvas; }}
  figcaption {{ padding: .5rem .7rem; font-size: .85rem; font-weight: 600; border-bottom: 1px solid GrayText; }}
  figcaption .n {{ display: inline-block; min-width: 1.6em; color: GrayText; font-variant-numeric: tabular-nums; }}
  figcaption .x {{ float: right; font-weight: 500; font-size: .8rem; color: GrayText; font-variant-numeric: tabular-nums; }}
  figcaption .x .d {{ font-size: .75rem; }}
  figcaption .x .d.down {{ color: #1a7f37; }}
  figcaption .x .d.up {{ color: #cf222e; }}
  img {{ display: block; width: 100%; height: auto; background: #fff; }}
  .note {{ margin: 0; padding: .4rem .7rem; font-size: .78rem; color: GrayText; }}
  .counters {{ margin: 0; padding: .35rem .7rem; font-size: .78rem; display: flex; gap: .9rem; border-top: 1px solid GrayText; font-variant-numeric: tabular-nums; }}
  .counters span {{ color: GrayText; }}
</style></head>
<body>
  <h1>{title}</h1>
  <p class="sub">{subtitle}</p>
  <div class="grid">
{cards}
  </div>
</body></html>
"""
