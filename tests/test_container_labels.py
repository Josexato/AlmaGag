"""
K35 — etiquetas dentro de contenedores no se pisan, y el audit R3 no marca
conexiones a bordes de contenedor como colgantes.
"""

from AlmaGag.validation.visual_quality import validate_gag, check_connections_attached


def test_r3_accepts_container_border_endpoint():
    """Un endpoint sobre el borde de un CONTENEDOR (conexión inter-contenedor)
    no es colgante — el audit debe aceptarlo (BUGS-VAL-002)."""
    # endpoint en (150, 300): lejos de cualquier icono, pero sobre el borde
    # inferior de un contenedor (100,100)-(200,300).
    endpoints = [(150, 300, 150, 300)]
    icons = [(500, 500, 580, 550)]              # icono lejano
    containers = [(100, 100, 200, 300)]         # el endpoint cae en su borde
    # Sin contenedores → colgante (2 extremos)
    assert len(check_connections_attached(endpoints, icons)) == 2
    # Con el contenedor como target válido → 0
    assert len(check_connections_attached(endpoints, icons, containers)) == 0


def test_arquitectura_no_container_label_pileup():
    """05-arquitectura: antes 11 violaciones (labels apilados dentro de «Shared»);
    tras K35, 0 labels sobre iconos (R1) y a lo sumo 1 solape residual."""
    rep = validate_gag('docs/diagrams/gags/05-arquitectura-gag.gag', layout_algorithm='auto')
    r1 = sum(1 for v in rep.violations if v.rule == 'R1_label_over_icon')
    r2 = sum(1 for v in rep.violations if v.rule == 'R2_labels_overlap')
    assert r1 == 0, f"labels sobre iconos: {r1}"
    assert r2 <= 1, f"solapes de labels: {r2}"
    assert len(rep.violations) <= 1


def test_architecture_template_clean():
    """15-architecture-template: 0 violaciones tras K35 (era 4)."""
    rep = validate_gag('docs/diagrams/gags/15-architecture-template.gag', layout_algorithm='auto')
    assert len(rep.violations) == 0
