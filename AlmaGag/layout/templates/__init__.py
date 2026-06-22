"""
Layout templates — patrones pre-definidos con auto-detección
(WISH-LAYOUT-004 Fase 2).

Pipeline cuando se procesa un SDJF:

1. Si el SDJF declara `"layout_template": "<name>"` → override manual:
   se busca el template con ese nombre y se aplica directamente.

2. Si no hay override:
   - Se extraen GraphFeatures del SDJF.
   - Cada template calcula su `detect_score(features) → [0, 1]`.
   - Si el mejor score supera DEFAULT_THRESHOLD y el segundo está por
     debajo (ventaja >= DEFAULT_MIN_LEAD), se aplica.
   - Si no, se devuelve None y el caller usa fallback agnóstico
     (algoritmo AUTO o LAF normal).

Templates registrados:
- ArchitectureTemplate ('architecture')
- FlowTemplate ('flow')
- HubAndSpokeTemplate ('hub_and_spoke')
"""

from AlmaGag.layout.templates.base import BaseTemplate, TemplateClassifier
from AlmaGag.layout.templates.features import GraphFeatures
from AlmaGag.layout.templates.architecture import (
    ArchitectureTemplate,
    apply_architecture_template,
)
from AlmaGag.layout.templates.flow import FlowTemplate, apply_flow_template
from AlmaGag.layout.templates.hub_and_spoke import (
    HubAndSpokeTemplate,
    apply_hub_and_spoke_template,
)
from AlmaGag.layout.templates.dashboard import (
    DashboardTemplate,
    apply_dashboard_template,
)
from AlmaGag.layout.templates.er import ERTemplate, apply_er_template
from AlmaGag.layout.templates.sequence import (
    SequenceTemplate,
    apply_sequence_template,
)
from AlmaGag.layout.templates.state import StateTemplate, apply_state_template
from AlmaGag.layout.templates.nested import (
    apply_nested_templates,
    offset_nested_children,
)


def get_default_classifier() -> TemplateClassifier:
    """Construye el clasificador con todos los templates registrados."""
    return TemplateClassifier([
        ArchitectureTemplate(),
        FlowTemplate(),
        HubAndSpokeTemplate(),
        DashboardTemplate(),
        ERTemplate(),
        SequenceTemplate(),
        StateTemplate(),
    ])


def apply_sub_templates(data) -> list:
    """
    Aplica sub-templates declarados en containers (Fase 4 nested).
    SIEMPRE se llama, independiente de si hay template padre.

    Returns lista de (container_id, template_name) aplicados.
    """
    classifier = get_default_classifier()
    return apply_nested_templates(data, classifier.by_name)


def apply_template(template_name, data) -> bool:
    """
    Aplica el template indicado por nombre (override manual).
    Antes de aplicar el padre, ejecuta los sub-templates anidados.

    Returns True si se aplicó alguno.
    """
    if not template_name:
        return False
    classifier = get_default_classifier()
    tpl = classifier.by_name(template_name)
    if tpl is None:
        return False
    apply_sub_templates(data)
    tpl.apply(data)
    offset_nested_children(data)
    return True


def auto_apply_template(data, debug=False) -> tuple:
    """
    Detecta automáticamente el template y lo aplica si pasa el threshold.
    Aplica SIEMPRE los sub-templates anidados, aunque el padre no aplique.

    Returns (applied_template_name, all_scores).
    """
    classifier = get_default_classifier()
    tpl, all_scores = classifier.classify(data)
    apply_sub_templates(data)  # SIEMPRE, antes del padre
    if tpl is not None:
        tpl.apply(data)
        offset_nested_children(data)
        return tpl.name, all_scores
    offset_nested_children(data)
    return None, all_scores


__all__ = [
    'BaseTemplate',
    'TemplateClassifier',
    'GraphFeatures',
    'ArchitectureTemplate',
    'FlowTemplate',
    'HubAndSpokeTemplate',
    'DashboardTemplate',
    'ERTemplate',
    'SequenceTemplate',
    'StateTemplate',
    'apply_template',
    'auto_apply_template',
    'get_default_classifier',
    'apply_architecture_template',
    'apply_flow_template',
    'apply_hub_and_spoke_template',
    'apply_dashboard_template',
    'apply_er_template',
    'apply_sequence_template',
    'apply_state_template',
]
