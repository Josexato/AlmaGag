"""WISH-LAYOUT-018 (W84 residual) — la franja de un journey es zona a
evitar para labels AJENOS al recorrido.

Los ICONOS ya cumplían el canal (gap mo↔dproc 144px ≥ 48, medido); el
residuo real eran LABELS que caían bajo la banda de color de otra
cadena (constr bajo la banda f2 del presupuesto del repo; est3 bajo la
banda scada de la arquitectura). P61 ahora puntúa la franja ajena
(+1) y recoloca; lo que queda sin lado limpio se NOMBRA en el log.
"""

import json
import math

from AlmaGag.draw.primitives.journeys import build_journey_lanes
from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.considerations import extract_considerations
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.geometry import GeometryCalculator

BAND_W = 28.0


def _foreign_label_band_overlaps(path):
    d = json.load(open(path))
    canvas = dict(d.get('canvas') or {})
    canvas.setdefault('width', 1400)
    canvas.setdefault('height', 900)
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=canvas)
    L._strategy = select_strategy(d, None)
    L._considerations = extract_considerations(d)
    L._journeys = d.get('journeys')
    out = LayoutEngine(verbose=False, strategy=None).optimize(L)
    geo = GeometryCalculator()
    hits = []
    for j, pts in build_journey_lanes(d['journeys'], out.elements_by_id,
                                      out.connections):
        if pts is None:
            continue
        members = set(j['path'])
        for eid, pi in out.label_positions.items():
            if eid in members:
                continue
            e = out.elements_by_id.get(eid)
            if not e:
                continue
            bb = geo.get_label_bbox_stored(e, pi)
            if not bb:
                continue
            for a, b in zip(pts, pts[1:]):
                n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 10))
                if any(bb[0] - BAND_W / 2 <= a[0] + (b[0] - a[0]) * i / n
                       <= bb[2] + BAND_W / 2
                       and bb[1] - BAND_W / 2 <= a[1] + (b[1] - a[1]) * i / n
                       <= bb[3] + BAND_W / 2 for i in range(n + 1)):
                    hits.append((j['id'], eid))
                    break
            else:
                continue
            break
    return hits


def test_presupuesto_labels_clear_foreign_bands():
    """El label de constr ya no queda bajo la banda f2 (antes: 1)."""
    hits = _foreign_label_band_overlaps(
        'docs/diagrams/gags/mina-presupuesto.sdjf')
    assert not hits, f'labels ajenos bajo bandas: {hits}'


def test_arquitectura_labels_clear_foreign_bands():
    """El label de est3 ya no queda bajo la banda scada (antes: 1)."""
    hits = _foreign_label_band_overlaps(
        'docs/diagrams/gags/mina-arquitectura-fisica.sdjf')
    assert not hits, f'labels ajenos bajo bandas: {hits}'
