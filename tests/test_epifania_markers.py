"""H9 — la epifanía marca colisiones sobre el thumbnail y reporta 3 contadores."""
import json
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.generator import select_strategy
from AlmaGag.layout.epifania import _collision_points, _counters_badge
from AlmaGag.layout.metrics import quality_counters


def _render(path):
    d = json.load(open(path))
    tn = d.get('layout_template')
    if tn:
        from AlmaGag.layout.templates import auto_apply_template, apply_template
        (auto_apply_template if tn == 'auto' else lambda x: apply_template(tn, x))(d)
    L = Layout(elements=d['elements'], connections=d['connections'], canvas=d.get('canvas', {}))
    L._strategy = select_strategy(d, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_collision_points_are_coordinates():
    res = _render('docs/diagrams/gags/05-arquitectura-gag.gag')
    pts = _collision_points(res)
    # hay colisiones residuales → hay puntos, y son (x,y) numéricos
    assert isinstance(pts, list)
    for p in pts:
        assert len(p) == 2 and all(isinstance(v, (int, float)) for v in p)


def test_counters_badge_shows_three():
    res = _render('docs/diagrams/gags/05-arquitectura-gag.gag')
    html = _counters_badge(quality_counters(res))
    assert html.count('<span') == 3
    assert '✕' in html
