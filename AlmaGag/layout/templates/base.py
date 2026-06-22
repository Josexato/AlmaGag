"""
BaseTemplate + TemplateClassifier (WISH-LAYOUT-004 Fase 2).

Cada template implementa:
- `name` (str): clave para override manual via SDJF `layout_template`.
- `detect_score(features) -> float` en [0, 1]: qué tan probable es que el
  grafo coincida con este patrón.
- `apply(data)`: asigna coordenadas in-place.

El TemplateClassifier elige el template con mayor score si supera un
threshold; si no, devuelve None (caller usa fallback agnóstico).
"""

from typing import Optional, List

from AlmaGag.layout.templates.features import GraphFeatures


class BaseTemplate:
    """Interfaz que cumplen todos los templates registrados."""

    name: str = ''

    def detect_score(self, features: GraphFeatures) -> float:
        raise NotImplementedError

    def apply(self, data: dict) -> None:
        raise NotImplementedError


class TemplateClassifier:
    """
    Elige el template más apropiado para un grafo dado.

    `threshold` es el mínimo score que un template debe superar para ser
    considerado el ganador. Por debajo del threshold, no se aplica template
    y el caller decide qué hacer (típicamente: fallback a algoritmo AUTO/LAF
    agnóstico).

    `min_lead` es la ventaja mínima del primer template sobre el segundo
    para considerar la elección "confiada". Si dos templates están empate
    cerrado, devolvemos None (es señal de patrón mixto/ambiguo).
    """

    DEFAULT_THRESHOLD = 0.6
    DEFAULT_MIN_LEAD = 0.05

    def __init__(self, templates: List[BaseTemplate],
                 threshold: float = DEFAULT_THRESHOLD,
                 min_lead: float = DEFAULT_MIN_LEAD):
        self.templates = templates
        self.threshold = threshold
        self.min_lead = min_lead

    def by_name(self, name: str) -> Optional[BaseTemplate]:
        for t in self.templates:
            if t.name == name:
                return t
        return None

    def classify(self, data: dict) -> tuple:
        """
        Returns (template_or_none, all_scores_sorted)
        where all_scores_sorted is List[(template_name, score)] descending.
        """
        features = GraphFeatures.extract(data.get('elements', []), data.get('connections', []))
        scored = [(t, t.detect_score(features)) for t in self.templates]
        scored.sort(key=lambda x: -x[1])

        scores_named = [(t.name, s) for t, s in scored]

        if not scored:
            return None, scores_named

        best_template, best_score = scored[0]
        if best_score < self.threshold:
            return None, scores_named

        # Confianza: ventaja sobre el segundo
        if len(scored) >= 2:
            _, second_score = scored[1]
            if best_score - second_score < self.min_lead:
                # Ambiguo — devolver None para que el caller decida
                return None, scores_named

        return best_template, scores_named
