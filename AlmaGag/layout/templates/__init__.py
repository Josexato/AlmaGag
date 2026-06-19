"""
Layout templates — patrones pre-definidos para diagramas comunes
(WISH-LAYOUT-004 Fase 1).

Los templates calculan coordenadas (x, y) para los elementos del SDJF
basándose en la estructura del grafo y heurísticas semánticas. Se invocan
ANTES del optimizer cuando el SDJF declara `"layout_template": "<nombre>"`
en su raíz.

Templates disponibles:
- 'architecture' — layout en T para diagramas arquitectónicos jerárquicos.
"""

from AlmaGag.layout.templates.architecture import apply_architecture_template

TEMPLATES = {
    'architecture': apply_architecture_template,
}


def apply_template(template_name, data):
    """
    Aplica el template indicado sobre `data` (SDJF parseado) in-place.

    Args:
        template_name: nombre del template (clave de TEMPLATES).
        data: dict con 'elements', 'connections', 'canvas' (opcional).

    Returns:
        bool: True si se aplicó algún template, False si el nombre es
        desconocido o no había template definido.
    """
    if not template_name:
        return False
    fn = TEMPLATES.get(template_name)
    if fn is None:
        return False
    fn(data)
    return True
