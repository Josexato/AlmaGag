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

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def by_rule(self, rule: str) -> List[Violation]:
        return [v for v in self.violations if v.rule == rule]


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


def _collect_icon_bboxes(root):
    """
    Recolecta bboxes de iconos. Un "icono" se identifica por <rect> con
    fill gradient (o por <polygon>/<circle> dentro de un <g id="..._icon"></g>).

    Para mantenerlo simple, usamos los <rect> con fill="url(#gradient-...)".
    Excluimos containers (los que tienen "gradient-X_container" o cuando el
    rect es muy grande relativo al canvas, asumimos container).
    """
    bboxes = []
    for rect in root.iter(f'{{{SVG_NS}}}rect'):
        fill = rect.get('fill', '')
        if 'url' not in fill or 'gradient' not in fill:
            continue
        # Saltar containers: gradient ID contiene "_container" o el rect es muy ancho/alto
        if '_container' in fill or '_box' in fill:
            continue
        try:
            x = float(rect.get('x', 0))
            y = float(rect.get('y', 0))
            w = float(rect.get('width', 0))
            h = float(rect.get('height', 0))
        except (TypeError, ValueError):
            continue
        # Containers suelen ser grandes: heurística — si w > 300 o h > 200 lo saltamos
        if w > 300 or h > 200:
            continue
        bboxes.append((x, y, x + w, y + h))
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
    Conexiones reales usan stroke 'black', 'gray' (líneas grises de
    waypoints) o colores explícitos asignados por --color-connections.
    Las líneas decorativas dentro de iconos tienen colores HEX específicos
    cortos (#566c73, etc).
    """
    if not stroke or stroke == 'none':
        return False
    s = stroke.lower().strip()
    return s in ('black', '#000', '#000000', 'gray', '#808080')


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


def check_connections_attached(endpoints, icon_bboxes, tolerance=20):
    """
    R3: cada extremo de conector debe estar cerca de un icono
    (dentro de `tolerance` px del borde del icono).
    """
    violations = []
    for ep in endpoints:
        x1, y1, x2, y2 = ep
        for p_name, (px, py) in (('start', (x1, y1)), ('end', (x2, y2))):
            attached = False
            for ibb in icon_bboxes:
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
                 icon_bboxes=None,
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
        report.violations.extend(check_connections_attached(endpoints, icon_bboxes))

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
    from AlmaGag.generator import generate_diagram
    from AlmaGag.layout import Layout
    from AlmaGag.layout.auto.optimizer import AutoLayoutOptimizer
    from AlmaGag.layout.laf.optimizer import LAFOptimizer

    with open(gag_path) as f:
        data = json.load(f)

    # Aplicar template si está declarado (igual que generator)
    template_name = data.get('layout_template')
    if template_name:
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
    Optim = AutoLayoutOptimizer if layout_algorithm == 'auto' else LAFOptimizer
    eng = Optim(verbose=False)
    result = eng.optimize(layout)

    # Bboxes reales de iconos (no-containers)
    icon_bboxes = []
    for e in result.elements:
        if 'contains' in e:
            continue
        if 'x' not in e or 'y' not in e:
            continue
        w = e.get('width', 80)
        h = e.get('height', 50)
        icon_bboxes.append((e['x'], e['y'], e['x'] + w, e['y'] + h))

    # Renderizar a SVG temporal y validar
    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
        tmp_svg = f.name
    generate_diagram(gag_path, output_file=tmp_svg, layout_algorithm=layout_algorithm)
    report = validate_svg(tmp_svg, icon_bboxes=icon_bboxes)
    os.unlink(tmp_svg)
    return report
