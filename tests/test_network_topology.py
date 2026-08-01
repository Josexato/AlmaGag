"""§N45/§N47 — detección de topología de red y layout hub-and-spoke."""
import json
import glob

from AlmaGag.layout.strategies.auto.network import (
    detect_network_topology, find_hubs, build_sites)
from AlmaGag.layout.considerations import extract_considerations


def _load(f):
    return json.load(open(f))


def test_detection_exact_set():
    """Sólo las fixtures de red disparan; los flujos con nube+ciclo NO
    (eran falsos positivos: 06-flujo, svg-to-bwt, system-architecture)."""
    trig = []
    for f in sorted(glob.glob('docs/diagrams/gags/*')):
        try:
            d = _load(f)
        except Exception:
            continue
        if detect_network_topology(d.get('elements', []), d.get('connections', [])):
            trig.append(f.rsplit('/', 1)[1])
    # red-dual-homing-areas ES una red (detección correcta), pero declara
    # `areas` → select_strategy la manda a hier y N45 (que vive en AUTO)
    # nunca la toca. Los flujos con nube+ciclo NO disparan.
    assert trig == ['red-dual-homing-areas.sdjf',
                    'red-minera-antes.gag', 'red-minera-despues.gag']


def test_hubs_are_the_wan_clouds():
    d = _load('docs/diagrams/gags/red-minera-antes.gag')
    assert set(find_hubs(d['elements'], d['connections'])) == {'internet', 'rpv_mpls'}


def test_sites_expand_partial_seeds():
    """Los near parciales del .gag se completan por conectividad: rtr_rpv se
    une a la oficina aunque ningún near lo mencione (§N45 con .gag imperfecto)."""
    d = _load('docs/diagrams/gags/red-minera-antes.gag')
    cons = extract_considerations(d)
    sites = build_sites(d['elements'], d['connections'], cons)
    oficina = next(s for s in sites if 'usuarios' in s)
    assert 'rtr_rpv' in oficina          # expandido, no estaba en el near
    assert 'rtr_inet' in oficina


def test_deterministic_between_files():
    """§N47: los sitios compartidos entre antes/después salen en el mismo
    orden determinista (misma plantilla de zonas)."""
    def _site_of(f, member):
        d = _load(f)
        cons = extract_considerations(d)
        sites = build_sites(d['elements'], d['connections'], cons)
        ordered = sorted(sites, key=lambda s: (-len(s), s[0]))
        for k, s in enumerate(ordered):
            if member in s:
                return k
        return None
    # el cluster de mina existe en ambos archivos con los mismos ids
    ka = _site_of('docs/diagrams/gags/red-minera-antes.gag', 'camp_fg')
    kd = _site_of('docs/diagrams/gags/red-minera-despues.gag', 'camp_fg')
    assert ka is not None and ka == kd


def test_n47_interzone_edges_orthogonal():
    """§N47: los enlaces entre zonas distintas llevan routing ortogonal."""
    import json
    d = _load('docs/diagrams/gags/red-minera-antes.gag')
    from AlmaGag.layout import Layout
    from AlmaGag.layout.strategies.auto.network import apply_network_layout
    cons = extract_considerations(d)
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {}))
    assert apply_network_layout(L, cons) > 0
    ortho = [c for c in L.connections
             if (c.get('routing') or {}).get('type') == 'orthogonal']
    assert len(ortho) >= 4
