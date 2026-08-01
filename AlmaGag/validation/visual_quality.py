"""
SVGQualityValidator — chequea reglas de calidad visual sobre SVGs renderizados.

Reglas implementadas (definidas con el usuario, 2026-06-19):

R1. Las etiquetas NO deben caer encima de iconos.
R2. Las etiquetas NO deben solaparse entre sí.
R3. Los conectores NO deben terminar en el aire (sin endpoint cercano a icono).

Se usa para:
- Auditar canonical SVGs (un report rápido de cuáles violan reglas).
- Tests de regresión visual.
- Validar nuevos diagramas generados por templates.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

SVG_NS = "http://www.w3.org/2000/svg"


@dataclass
class Violation:
    rule: str
    description: str
    location: Optional[Tuple[float, float]] = None
    extra: dict = field(default_factory=dict)


@dataclass
class QualityReport:
    file: str
    canvas_width: float
    canvas_height: float
    n_icons: int
    n_labels: int
    n_connections: int
    violations: List[Violation] = field(default_factory=list)
    # §H8: avisos no bloqueantes (p.ej. contraste bajo). No cuentan como
    # violaciones ni afectan `passed` — son recomendaciones.
    warnings: List[Violation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def by_rule(self, rule: str) -> List[Violation]:
        return [v for v in self.violations if v.rule == rule]


def _relative_luminance(hex_color: str) -> float:
    """Luminancia relativa WCAG de un color #rrggbb."""
    h = hex_color.lstrip('#')
    if len(h) != 6:
        return 1.0
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 1.0
    def _lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    R, G, B = _lin(r), _lin(g), _lin(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B


def contrast_vs_white(hex_color: str) -> float:
    """Razón de contraste WCAG del color contra fondo blanco."""
    return (1.0 + 0.05) / (_relative_luminance(hex_color) + 0.05)


def check_color_contrast(data, min_ratio: float = 3.0) -> List[Violation]:
    """§H8: avisa de colores de conexión con contraste < min_ratio sobre blanco
    (líneas casi invisibles en proyector, p.ej. respaldos rosados)."""
    warnings = []
    for conn in data.get('connections', []):
        color = conn.get('color')
        if not color or not str(color).startswith('#'):
            continue
        ratio = contrast_vs_white(color)
        if ratio < min_ratio:
            warnings.append(Violation(
                rule='contrast_low',
                description=(f"conexión {conn.get('from')}→{conn.get('to')}: "
                             f"color {color} contraste {ratio:.1f}:1 (<{min_ratio}:1)"),
                extra={'color': color, 'ratio': round(ratio, 2)},
            ))
    return warnings


def _bbox_intersects(a, b, tol=0):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 + tol <= bx1 or bx2 + tol <= ax1
                or ay2 + tol <= by1 or by2 + tol <= ay1)


def _bbox_area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def _bbox_overlap_area(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ox = max(0, min(ax2, bx2) - max(ax1, bx1))
    oy = max(0, min(ay2, by2) - max(ay1, by1))
    return ox * oy


def _estimate_text_bbox(elem):
    """
    Estima el bbox de un <text>. Como SVG no incluye dimensiones del texto
    renderizado, aproximamos: ancho ≈ len(text) * font_size * 0.55,
    alto ≈ font_size * 1.2 (con baseline en y).

    Devuelve (x1, y1, x2, y2) o None si falta info.
    """
    try:
        x = float(elem.get('x', 0))
        y = float(elem.get('y', 0))
    except (TypeError, ValueError):
        return None
    text = (elem.text or '').strip()
    if not text:
        return None
    size_str = elem.get('font-size', '14')
    try:
        font_size = float(size_str.replace('px', ''))
    except ValueError:
        font_size = 14.0
    # Bold suele usar más ancho
    weight = elem.get('font-weight', '')
    char_w_factor = 0.62 if 'bold' in str(weight).lower() else 0.55
    width = len(text) * font_size * char_w_factor
    height = font_size * 1.2

    anchor = elem.get('text-anchor', 'start')
    if anchor == 'middle':
        x1 = x - width / 2
    elif anchor == 'end':
        x1 = x - width
    else:
        x1 = x
    x2 = x1 + width
    # y es baseline → text vive arriba de y
    y1 = y - font_size
    y2 = y + 0.2 * font_size  # descenders
    return (x1, y1, x2, y2)


import re as _re

# Dimensiones nominales de un icono (deben coincidir con AlmaGag.config).
_ICON_W = 80
_ICON_H = 50

_TRANSLATE_RE = _re.compile(r'translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)')
_SCALE_RE = _re.compile(r'scale\(\s*([-\d.]+)')


def _group_transform_bbox(g):
    """
    Bbox de un icono custom renderizado como <g transform="translate(x,y) scale(s)">
    (factory, gear, contract, iconos SVG embebidos). Devuelve (x1,y1,x2,y2) o None.
    """
    tr = g.get('transform', '')
    m = _TRANSLATE_RE.search(tr)
    if not m:
        return None
    tx, ty = float(m.group(1)), float(m.group(2))
    sm = _SCALE_RE.search(tr)
    s = float(sm.group(1)) if sm else 1.0
    return (tx, ty, tx + _ICON_W * s, ty + _ICON_H * s)


def _group_children_bbox(g):
    """
    Bbox a partir de las formas hijas de un <g> sin transform: <rect>,
    <polygon>, <circle>, <ellipse> (cubre diamond y built-ins con coords
    absolutas). Devuelve (x1,y1,x2,y2) o None.
    """
    xs, ys = [], []
    for rect in g.iter(f'{{{SVG_NS}}}rect'):
        try:
            x, y = float(rect.get('x', 0)), float(rect.get('y', 0))
            w, h = float(rect.get('width', 0)), float(rect.get('height', 0))
            xs += [x, x + w]; ys += [y, y + h]
        except (TypeError, ValueError):
            pass
    for poly in g.iter(f'{{{SVG_NS}}}polygon'):
        nums = []
        for part in poly.get('points', '').replace(',', ' ').split():
            try:
                nums.append(float(part))
            except ValueError:
                pass
        xs += nums[0::2]; ys += nums[1::2]
    for circ in g.iter(f'{{{SVG_NS}}}circle'):
        try:
            cx, cy, r = float(circ.get('cx', 0)), float(circ.get('cy', 0)), float(circ.get('r', 0))
            xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
        except (TypeError, ValueError):
            pass
    for el in g.iter(f'{{{SVG_NS}}}ellipse'):
        try:
            cx, cy = float(el.get('cx', 0)), float(el.get('cy', 0))
            rx, ry = float(el.get('rx', 0)), float(el.get('ry', 0))
            xs += [cx - rx, cx + rx]; ys += [cy - ry, cy + ry]
        except (TypeError, ValueError):
            pass
    if not xs or not ys:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _is_icon_group_id(gid):
    """¿El id de un <g> corresponde a un elemento-icono (no metadata)?"""
    if not gid:
        return False
    if gid.startswith('ndfn-') or gid.startswith('conn-'):
        return False
    if gid.endswith('_icon'):  # icono de container, lo tratamos aparte
        return False
    return True


def _collect_icon_bboxes(root):
    """
    Recolecta bboxes de iconos del SVG.

    BUGS-VAL-001: además de los <rect> con gradiente (iconos built-in como
    server/database), reconoce iconos CUSTOM:
    - <g transform="translate(x,y) scale(s)"> (factory, gear, contract,
      iconos SVG embebidos).
    - <g id="..."> con polygon/circle (diamond y similares en coords abs).

    Sin esto, los conectores hacia iconos custom se reportaban como
    "dangling" (R3 falso positivo) porque el icono no se detectaba.

    Excluye containers (gradient "_container"/"_box" o rect muy grande).
    """
    bboxes = []
    seen_groups = set()

    # 1. Iconos custom: cada <g> de elemento → bbox por transform o por hijos.
    for g in root.iter(f'{{{SVG_NS}}}g'):
        gid = g.get('id', '')
        if not _is_icon_group_id(gid):
            continue
        bb = _group_transform_bbox(g)
        if bb is None:
            bb = _group_children_bbox(g)
        if bb is None:
            continue
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        # Saltar containers grandes
        if w > 300 or h > 200:
            continue
        bboxes.append(bb)
        seen_groups.add(gid)

    # 2. Built-in por gradient rect SUELTO (no dentro de un <g> ya contado).
    for rect in root.iter(f'{{{SVG_NS}}}rect'):
        fill = rect.get('fill', '')
        if 'url' not in fill or 'gradient' not in fill:
            continue
        if '_container' in fill or '_box' in fill:
            continue
        try:
            x = float(rect.get('x', 0))
            y = float(rect.get('y', 0))
            w = float(rect.get('width', 0))
            h = float(rect.get('height', 0))
        except (TypeError, ValueError):
            continue
        if w > 300 or h > 200:
            continue
        bb = (x, y, x + w, y + h)
        # Evitar duplicar un rect que ya está cubierto por un grupo contado.
        if any(_bbox_intersects(bb, e) and _bbox_overlap_area(bb, e) > 0.5 * w * h
               for e in bboxes):
            continue
        bboxes.append(bb)

    return bboxes


def _collect_text_bboxes(root, only_visible_labels=True):
    """
    Recolecta bboxes de etiquetas (textos visibles, no <desc> ni
    metadatos NdFn de debug).
    """
    bboxes = []
    for txt in root.iter(f'{{{SVG_NS}}}text'):
        if (txt.text or '').strip() == '':
            continue
        # §O50: los gemelos de halo (copia con trazo blanco bajo cada label)
        # no son etiquetas — contarlos duplicaría cada solape.
        if txt.get('class') == 'ag-text-halo':
            continue
        # Excluir labels minúsculos de debug (NdFn etc) que viven en gris muy chico
        size = txt.get('font-size', '14')
        try:
            font_size = float(str(size).replace('px', ''))
        except ValueError:
            font_size = 14
        if font_size < 9:
            continue
        bb = _estimate_text_bbox(txt)
        if bb:
            bboxes.append((bb, txt.text.strip()))
    return bboxes


def _is_connection_stroke(stroke: str) -> bool:
    """
    Conexiones reales usan stroke 'black', 'gray' (waypoints) o un color
    semántico declarado (WISH-LAYOUT-007). Las líneas decorativas dentro de
    iconos tienen otros colores HEX y, sobre todo, no llevan marker — el
    chequeo de marker/longitud en _collect_connection_endpoints las filtra.
    """
    if not stroke or stroke == 'none':
        return False
    s = stroke.lower().strip()
    if s in ('black', '#000', '#000000', 'gray', '#808080'):
        return True
    # Colores de la paleta semántica (WISH-LAYOUT-007).
    try:
        from AlmaGag.draw.primitives.svg import SEMANTIC_CONNECTION_COLORS
        if s in {c.lower() for c in SEMANTIC_CONNECTION_COLORS.values()}:
            return True
    except Exception:
        pass
    return False


def _has_marker(elem) -> bool:
    """¿El elemento tiene marker (flecha) en algún extremo?"""
    return bool(
        elem.get('marker-end') or elem.get('marker-start')
        or elem.get('marker-mid')
    )


def _collect_connection_endpoints(root):
    """
    Devuelve lista de (x_start, y_start, x_end, y_end) de conexiones REALES.

    Heurísticas combinadas para distinguir conexión vs decoración interna
    de icono:
    1. Stroke debe ser color de conexión (black/gray, no colores HEX
       decorativos como #566c73).
    2. Debe tener marker O ser polyline/path (las decoraciones suelen
       ser <line> sin marker).
    3. Largo mínimo: 50px (las decoraciones de icono son cortas).
    """
    MIN_CONN_LENGTH = 50

    endpoints = []
    for ln in root.iter(f'{{{SVG_NS}}}line'):
        if not _is_connection_stroke(ln.get('stroke', '')):
            continue
        try:
            x1 = float(ln.get('x1', 0))
            y1 = float(ln.get('y1', 0))
            x2 = float(ln.get('x2', 0))
            y2 = float(ln.get('y2', 0))
        except (TypeError, ValueError):
            continue
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        # Filtros: si NO tiene marker Y es corta, es decoración
        if not _has_marker(ln) and length < MIN_CONN_LENGTH:
            continue
        endpoints.append((x1, y1, x2, y2))

    for pl in root.iter(f'{{{SVG_NS}}}polyline'):
        if not _is_connection_stroke(pl.get('stroke', '')):
            continue
        pts_str = pl.get('points', '').strip()
        if not pts_str:
            continue
        pts = []
        for part in pts_str.replace(',', ' ').split():
            try:
                pts.append(float(part))
            except ValueError:
                pass
        if len(pts) >= 4:
            endpoints.append((pts[0], pts[1], pts[-2], pts[-1]))

    import re
    for path in root.iter(f'{{{SVG_NS}}}path'):
        if not _is_connection_stroke(path.get('stroke', '')):
            continue
        d = path.get('d', '')
        nums = [float(n) for n in re.findall(r'-?\d+\.?\d*', d)]
        if len(nums) >= 4:
            endpoints.append((nums[0], nums[1], nums[-2], nums[-1]))

    return endpoints


# ============================================================================
# Reglas
# ============================================================================

def check_labels_over_icons(text_bboxes, icon_bboxes, min_overlap_area=80):
    """R1: cada label NO debe caer dentro de un icono."""
    violations = []
    for tbb, txt in text_bboxes:
        for ibb in icon_bboxes:
            overlap = _bbox_overlap_area(tbb, ibb)
            if overlap >= min_overlap_area:
                cx = (tbb[0] + tbb[2]) / 2
                cy = (tbb[1] + tbb[3]) / 2
                violations.append(Violation(
                    rule='R1_label_over_icon',
                    description=f'Label {txt!r} solapa icono ({overlap:.0f} px²)',
                    location=(cx, cy),
                    extra={'text': txt, 'overlap_area': overlap},
                ))
                break  # Una violación por label es suficiente
    return violations


def check_labels_overlap(text_bboxes, min_overlap_area=50):
    """R2: dos labels NO deben solaparse."""
    violations = []
    n = len(text_bboxes)
    for i in range(n):
        for j in range(i + 1, n):
            ai, ti = text_bboxes[i]
            aj, tj = text_bboxes[j]
            ov = _bbox_overlap_area(ai, aj)
            if ov >= min_overlap_area:
                violations.append(Violation(
                    rule='R2_labels_overlap',
                    description=f'Labels {ti!r} y {tj!r} solapan ({ov:.0f} px²)',
                    location=((ai[0] + ai[2]) / 2, (ai[1] + ai[3]) / 2),
                    extra={'text_a': ti, 'text_b': tj, 'overlap_area': ov},
                ))
    return violations


def check_connections_attached(endpoints, icon_bboxes, container_bboxes=None, tolerance=30):
    """
    R3: cada extremo de conector debe estar cerca de un icono O de un
    contenedor (dentro de `tolerance` px del borde).

    BUGS-VAL-001: tolerancia 20 → 30. port_assignment coloca los puntos de
    conexión en los bordes del icono distribuidos en sectores angulares, con
    offsets de hasta ~25px del centro del lado; 20px generaba falsos
    positivos en conexiones legítimamente atadas.

    BUGS-VAL-002: las conexiones entre CONTENEDORES terminan en el borde de la
    caja (un endpoint válido), lejos de cualquier icono contenido → se contaban
    como colgantes falsamente. Ahora un endpoint sobre/dentro de un contenedor
    también cuenta como atado.
    """
    targets = list(icon_bboxes) + list(container_bboxes or [])
    violations = []
    for ep in endpoints:
        x1, y1, x2, y2 = ep
        for p_name, (px, py) in (('start', (x1, y1)), ('end', (x2, y2))):
            attached = False
            for ibb in targets:
                bx1, by1, bx2, by2 = ibb
                if (bx1 - tolerance <= px <= bx2 + tolerance
                        and by1 - tolerance <= py <= by2 + tolerance):
                    attached = True
                    break
            if not attached:
                violations.append(Violation(
                    rule='R3_dangling_connection',
                    description=f'Conector con punto {p_name} ({px:.0f},{py:.0f}) sin icono cercano',
                    location=(px, py),
                    extra={'endpoint': p_name},
                ))
    return violations


# ============================================================================
# API principal
# ============================================================================

def validate_svg(svg_path: str,
                 icon_bboxes=None, container_bboxes=None,
                 check_r1=True, check_r2=True, check_r3=True) -> QualityReport:
    """
    Valida un SVG contra las 3 reglas.

    Args:
        svg_path: ruta al SVG renderizado.
        icon_bboxes: lista opcional de (x1, y1, x2, y2) de iconos REALES,
                     típicamente obtenida del optimizer. Si None, se infiere
                     del SVG (heurística menos confiable, falla con iconos
                     custom embebidos).
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    cw = float(root.get('width', 0))
    ch = float(root.get('height', 0))

    if icon_bboxes is None:
        icon_bboxes = _collect_icon_bboxes(root)
    texts = _collect_text_bboxes(root)
    endpoints = _collect_connection_endpoints(root)

    report = QualityReport(
        file=svg_path,
        canvas_width=cw, canvas_height=ch,
        n_icons=len(icon_bboxes), n_labels=len(texts), n_connections=len(endpoints),
    )

    if check_r1:
        report.violations.extend(check_labels_over_icons(texts, icon_bboxes))
    if check_r2:
        report.violations.extend(check_labels_overlap(texts))
    if check_r3:
        report.violations.extend(check_connections_attached(endpoints, icon_bboxes, container_bboxes))

    return report


def validate_gag(gag_path: str, layout_algorithm='auto') -> QualityReport:
    """
    Valida un .gag/.sdjf: lo renderiza, extrae posiciones reales de iconos
    del optimizer (incluso para iconos custom embebidos), y aplica las 3
    reglas sobre el SVG resultante.
    """
    import json
    import tempfile
    import os
    from AlmaGag.generator import generate_diagram, select_strategy
    from AlmaGag.layout import Layout
    from AlmaGag.layout.engine import LayoutEngine

    with open(gag_path) as f:
        data = json.load(f)

    # §H7: expandir uniones igual que el generator (para que las bboxes y el
    # render coincidan). No-op si no hay `unions`.
    from AlmaGag.layout.unions import expand_unions
    expand_unions(data)

    # Decidir la estrategia sobre el JSON CRUDO, igual que el generator: si el
    # motor resuelto es `hier`, hace su propio placement y el template (coords
    # pensadas para AUTO) sólo estorbaría — se saltea. Extraer las bboxes con
    # otro motor que el del render produce falsos R3 (endpoints "colgantes"
    # porque los iconos están donde el motor equivocado los puso, no donde el
    # SVG los dibujó). Por eso aquí se usa el MISMO LayoutEngine que el render.
    resolved_strategy = (
        select_strategy(data, 'auto') if layout_algorithm == 'select'
        else layout_algorithm
    )

    template_name = data.get('layout_template')
    if resolved_strategy != 'hier' and template_name:
        from AlmaGag.layout.templates import (
            apply_template, auto_apply_template
        )
        if template_name == 'auto':
            auto_apply_template(data)
        else:
            apply_template(template_name, data)

    layout = Layout(
        elements=data.get('elements', []),
        connections=data.get('connections', []),
        canvas=data.get('canvas', {}),
    )
    # Metadata semántica que el motor hier consume (retrocompatible: si falta,
    # camino normal). Debe viajar en el layout igual que en el generator.
    layout._areas = data.get('areas')
    layout._roles = data.get('roles')
    layout._lanes = data.get('lanes')
    from AlmaGag.layout.considerations import extract_considerations
    layout._considerations = extract_considerations(data)
    if layout_algorithm == 'select':
        layout._strategy = resolved_strategy
        forced = None
    else:
        forced = layout_algorithm
    eng = LayoutEngine(verbose=False, strategy=forced)
    result = eng.optimize(layout)

    # Bboxes reales de iconos (no-containers) y de contenedores por separado:
    # R1 (label sobre icono) sólo mira iconos; R3 (colgantes) acepta también
    # bordes de contenedor como endpoint válido (conexiones entre contenedores).
    icon_bboxes = []
    container_bboxes = []
    for e in result.elements:
        if 'x' not in e or 'y' not in e:
            continue
        w = e.get('width', 80)
        h = e.get('height', 50)
        bbox = (e['x'], e['y'], e['x'] + w, e['y'] + h)
        if 'contains' in e:
            container_bboxes.append(bbox)
        else:
            icon_bboxes.append(bbox)

    # Renderizar a SVG temporal y validar
    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
        tmp_svg = f.name
    generate_diagram(gag_path, output_file=tmp_svg, layout_algorithm=layout_algorithm)
    report = validate_svg(tmp_svg, icon_bboxes=icon_bboxes, container_bboxes=container_bboxes)
    os.unlink(tmp_svg)
    # §H8: avisos de contraste bajo (no bloqueantes) sobre los colores del origen.
    report.warnings.extend(check_color_contrast(data))
    return report
