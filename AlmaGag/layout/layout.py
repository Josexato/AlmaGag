"""
Layout - Contenedor inmutable del estado del diagrama

El Layout almacena el estado completo de un diagrama en un momento dado:
- Elementos y conexiones (datos core)
- Posiciones de etiquetas
- Análisis de grafo (niveles, grupos, prioridades)
- Métricas de colisiones (calculadas bajo demanda)

Filosofía:
- El Layout ES un snapshot del diagrama
- Los optimizadores CREAN nuevos layouts, no modifican existentes
- Los análisis ESCRIBEN características en el layout durante evaluación
"""

from copy import deepcopy
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Layout:
    """
    Contenedor del estado del diagrama.

    Attributes:
        elements (List[dict]): Lista de elementos del diagrama con x, y, type, label, etc.
        connections (List[dict]): Lista de conexiones entre elementos
        canvas (Dict[str, int]): Dimensiones del canvas {'width': int, 'height': int}

        label_positions (Dict): Posiciones calculadas de etiquetas de elementos
        connection_labels (Dict): Posiciones calculadas de etiquetas de conexiones

        graph (Dict): Grafo de adyacencia {element_id: [connected_ids]}
        levels (Dict): Niveles verticales {element_id: level_number}
        groups (List): Subgrafos conectados [[elem_ids_grupo_1], ...]
        priorities (Dict): Prioridades de elementos {element_id: priority_value}

        _collision_count (Optional[int]): Número de colisiones detectadas
        _collision_pairs (Optional[List]): Lista de pares en colisión
    """

    # Core data (inmutable conceptualmente)
    elements: List[dict]
    connections: List[dict]
    canvas: Dict[str, int]

    # Atributos de posicionamiento (mutables - calculados por optimizador)
    label_positions: Dict[str, Tuple[float, float, str, str]] = field(default_factory=dict)
    connection_labels: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # Atributos de análisis (escritos por optimizador durante evaluación)
    graph: Dict[str, List[str]] = field(default_factory=dict)
    levels: Dict[str, int] = field(default_factory=dict)
    groups: List[List[str]] = field(default_factory=list)
    priorities: Dict[str, int] = field(default_factory=dict)

    # Lookup rápido
    elements_by_id: Dict[str, dict] = field(default_factory=dict)

    # Métricas de colisiones (lazy evaluation)
    _collision_count: Optional[int] = field(default=None, repr=False)
    _collision_pairs: Optional[List[Tuple]] = field(default=None, repr=False)

    def __post_init__(self):
        """Construye índices después de inicialización."""
        if not self.elements_by_id:
            self.elements_by_id = {e['id']: e for e in self.elements}

    def copy(self) -> 'Layout':
        """
        Crea una copia profunda del layout.

        Usado por optimizadores para crear candidatos en cada iteración.
        Los atributos de análisis (graph, levels, groups, priorities) se copian
        también para permitir que cada candidato tenga su propio estado de análisis.

        Returns:
            Layout: Nueva instancia con datos copiados

        Example:
            >>> original = Layout(elements=[...], connections=[...], canvas={...})
            >>> candidate = original.copy()
            >>> candidate.elements[0]['x'] += 10  # No afecta a original
        """
        return Layout(
            elements=deepcopy(self.elements),
            connections=self.connections.copy(),  # Shallow copy - no se modifican
            canvas=self.canvas.copy(),
            label_positions=self.label_positions.copy(),
            connection_labels=self.connection_labels.copy(),
            graph={k: v.copy() for k, v in self.graph.items()},
            levels=self.levels.copy(),
            groups=[g.copy() for g in self.groups],
            priorities=self.priorities.copy()
        )

    def invalidate_collision_cache(self):
        """
        Invalida el caché de colisiones después de modificar el layout.

        Debe llamarse después de cualquier operación que modifique:
        - Posiciones de elementos
        - Posiciones de etiquetas
        - Conexiones
        """
        self._collision_count = None
        self._collision_pairs = None

    @property
    def collision_count(self) -> int:
        """
        Propiedad lazy para obtener el número de colisiones.

        Returns:
            int: Número de colisiones detectadas

        Raises:
            ValueError: Si el layout no ha sido evaluado todavía
        """
        if self._collision_count is None:
            raise ValueError(
                "Collision count not evaluated. "
                "Call optimizer.evaluate(layout) first."
            )
        return self._collision_count

    @property
    def collision_pairs(self) -> List[Tuple]:
        """
        Propiedad lazy para obtener los pares en colisión.

        Returns:
            List[Tuple]: Lista de tuplas (id1, id2, collision_type)

        Raises:
            ValueError: Si el layout no ha sido evaluado todavía
        """
        if self._collision_pairs is None:
            raise ValueError(
                "Collision pairs not evaluated. "
                "Call optimizer.evaluate(layout) first."
            )
        return self._collision_pairs

    def has_analysis(self) -> bool:
        """
        Verifica si el layout ha sido analizado.

        Returns:
            bool: True si se ha realizado análisis de grafo
        """
        return bool(self.graph or self.levels or self.groups)

    def has_positions(self) -> bool:
        """
        Verifica si las posiciones de etiquetas han sido calculadas.

        Returns:
            bool: True si se han calculado posiciones
        """
        return bool(self.label_positions)

    def has_collision_data(self) -> bool:
        """
        Verifica si se han calculado las colisiones.

        Returns:
            bool: True si el layout ha sido evaluado
        """
        return self._collision_count is not None

    def get_recommended_canvas(self) -> Dict[str, int]:
        """
        Calcula el canvas recomendado basado en elementos actuales.

        Calcula el área mínima necesaria para contener todos los elementos
        con márgenes adecuados.

        Returns:
            Dict[str, int]: {'width': int, 'height': int}
        """
        from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

        if not self.elements:
            return self.canvas.copy()

        # Filtrar elementos con coordenadas válidas
        positioned_elements = [e for e in self.elements if 'x' in e and 'y' in e]

        if not positioned_elements:
            return self.canvas.copy()

        max_x = max(e['x'] + ICON_WIDTH for e in positioned_elements)
        max_y = max(e['y'] + ICON_HEIGHT for e in positioned_elements)

        return {
            'width': max(max_x + 200, self.canvas['width']),
            'height': max(max_y + 120, self.canvas['height'])
        }

    def __repr__(self) -> str:
        """Representación string del layout."""
        collision_status = (
            f"{self._collision_count} colisiones"
            if self._collision_count is not None
            else "no evaluado"
        )
        analysis_status = "analizado" if self.has_analysis() else "sin analizar"
        positions_status = "calculadas" if self.has_positions() else "sin calcular"

        return (
            f"Layout("
            f"elementos={len(self.elements)}, "
            f"conexiones={len(self.connections)}, "
            f"canvas={self.canvas['width']}x{self.canvas['height']}, "
            f"colisiones={collision_status}, "
            f"análisis={analysis_status}, "
            f"posiciones={positions_status}"
            f")"
        )
