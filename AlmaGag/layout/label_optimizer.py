"""
LabelPositionOptimizer - Optimización de posiciones de etiquetas (v3.0)

Este módulo maneja la detección y resolución de colisiones de etiquetas:
- Etiquetas de conexiones
- Etiquetas de contenedores
- Etiquetas de elementos

Algoritmo:
1. Generar posiciones candidatas para cada etiqueta
2. Evaluar cada posición (score basado en colisiones y legibilidad)
3. Asignar la mejor posición a cada etiqueta minimizando colisiones totales
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger('AlmaGag.LabelOptimizer')


@dataclass
class Label:
    """
    Representa una etiqueta en el diagrama.

    Attributes:
        id: Identificador único de la etiqueta
        text: Texto de la etiqueta
        anchor_x: Coordenada X del punto de anclaje
        anchor_y: Coordenada Y del punto de anclaje
        font_size: Tamaño de fuente
        priority: Prioridad (0=alta, 1=normal, 2=baja)
        category: Categoría ('connection', 'container', 'element')
        fixed: Si es True, no se reposiciona
    """
    id: str
    text: str
    anchor_x: float
    anchor_y: float
    font_size: int = 12
    priority: int = 1
    category: str = "connection"
    fixed: bool = False


@dataclass
class LabelPosition:
    """
    Representa una posición calculada para una etiqueta.

    Attributes:
        label_id: ID de la etiqueta
        x: Coordenada X de inserción del texto
        y: Coordenada Y de inserción del texto
        anchor: Alineación del texto ('start', 'middle', 'end')
        offset_name: Nombre descriptivo del offset ('top', 'bottom', etc.)
        score: Score de calidad de esta posición (menor = mejor)
    """
    label_id: str
    x: float
    y: float
    anchor: str
    offset_name: str
    score: float = 0.0


class LabelPositionOptimizer:
    """
    Optimizador de posiciones de etiquetas para minimizar colisiones.
    """

    def __init__(self, geometry_calculator, canvas_width: int, canvas_height: int, debug: bool = False):
        """
        Inicializa el optimizador.

        Args:
            geometry_calculator: Instancia de GeometryCalculator
            canvas_width: Ancho del canvas
            canvas_height: Alto del canvas
            debug: Si es True, activa logging detallado
        """
        self.geometry = geometry_calculator
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.debug = debug

        if debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("LabelPositionOptimizer inicializado en modo DEBUG")
        else:
            logger.setLevel(logging.WARNING)

    def generate_candidate_positions(
        self,
        label: Label,
        element_width: float = 80.0,
        element_height: float = 50.0
    ) -> List[LabelPosition]:
        """
        Genera posiciones candidatas para una etiqueta.

        Para etiquetas de conexiones, genera 8 posiciones:
        - Top, Bottom, Left, Right (cerca del anchor)
        - Top-Left, Top-Right, Bottom-Left, Bottom-Right (esquinas)

        Para etiquetas de contenedores, genera 3 posiciones:
        - Top (arriba centrado)
        - Top-Left (arriba izquierda)
        - Top-Right (arriba derecha)

        Args:
            label: Etiqueta a posicionar
            element_width: Ancho del elemento (para calcular FAR_OFFSET)
            element_height: Altura del elemento (para calcular NEAR_OFFSET)

        Returns:
            List[LabelPosition]: Lista de posiciones candidatas
        """
        candidates = []
        x, y = label.anchor_x, label.anchor_y

        # Offsets calculados dinámicamente según el tamaño del elemento
        # Fórmula: OFFSET = (dimension/2) + (1.5 * char_size)
        # Esto garantiza ~21px de separación desde el borde del elemento
        char_height = label.font_size
        char_width = label.font_size * 0.6  # Aproximación ancho de carácter

        NEAR_OFFSET = (element_height / 2) + (1.5 * char_height)
        FAR_OFFSET = (element_width / 2) + (1.5 * char_width)

        if label.category == "connection":
            # 8 posiciones para conexiones
            offsets = [
                ("top", x, y - NEAR_OFFSET, "middle"),
                ("bottom", x, y + NEAR_OFFSET, "middle"),
                ("left", x - FAR_OFFSET, y, "end"),
                ("right", x + FAR_OFFSET, y, "start"),
                ("top-left", x - FAR_OFFSET, y - NEAR_OFFSET, "end"),
                ("top-right", x + FAR_OFFSET, y - NEAR_OFFSET, "start"),
                ("bottom-left", x - FAR_OFFSET, y + NEAR_OFFSET, "end"),
                ("bottom-right", x + FAR_OFFSET, y + NEAR_OFFSET, "start"),
            ]
        elif label.category == "container":
            # 3 posiciones para contenedores (siempre arriba)
            offsets = [
                ("top", x, y - 10, "middle"),
                ("top-left", x - 20, y - 10, "end"),
                ("top-right", x + 20, y - 10, "start"),
            ]
        else:  # element
            # 4 posiciones para elementos (bottom primero - preferido)
            offsets = [
                ("bottom", x, y + NEAR_OFFSET, "middle"),  # Preferido
                ("top", x, y - NEAR_OFFSET, "middle"),
                ("right", x + FAR_OFFSET, y, "start"),
                ("left", x - FAR_OFFSET, y, "end"),
            ]

        for offset_name, pos_x, pos_y, anchor in offsets:
            candidates.append(LabelPosition(
                label_id=label.id,
                x=pos_x,
                y=pos_y,
                anchor=anchor,
                offset_name=offset_name
            ))

        return candidates

    def calculate_local_density(
        self,
        position_bbox: Tuple[float, float, float, float],
        placed_labels: List[Tuple[float, float, float, float]],
        radius: float = 100.0
    ) -> int:
        """
        Calcula la densidad local de etiquetas alrededor de una posición.

        Cuenta cuántas etiquetas ya colocadas están dentro de un radio
        desde el centro de la posición candidata.

        Args:
            position_bbox: Bounding box de la posición candidata (x1, y1, x2, y2)
            placed_labels: Lista de bboxes de etiquetas ya colocadas
            radius: Radio de búsqueda en píxeles (default: 100px)

        Returns:
            int: Número de etiquetas dentro del radio
        """
        # Centro de la posición candidata
        x1, y1, x2, y2 = position_bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        count = 0
        for label_bbox in placed_labels:
            # Centro de la etiqueta ya colocada
            lx1, ly1, lx2, ly2 = label_bbox
            label_center_x = (lx1 + lx2) / 2
            label_center_y = (ly1 + ly2) / 2

            # Distancia entre centros
            distance = ((center_x - label_center_x)**2 + (center_y - label_center_y)**2)**0.5

            if distance <= radius:
                count += 1

        return count

    def score_position(
        self,
        position: LabelPosition,
        label: Label,
        elements: List[dict],
        placed_labels: List[Tuple[float, float, float, float]],
        connections: List[dict] = None
    ) -> float:
        """
        Evalúa la calidad de una posición para una etiqueta.

        Score más bajo = mejor posición

        Factores considerados:
        - Colisiones con elementos: +100 por cada colisión
        - Colisiones con otras etiquetas: +50 por cada colisión
        - Colisiones con líneas de conexión: +75 por cada colisión (v3.2)
        - Fuera del canvas: +1000 (penalización severa)
        - Distancia al anchor: +1 por cada 10 píxeles
        - Preferencia por "top" para conexiones: -10
        - Densidad local: +60 por cada etiqueta en radio de 75px (v3.1)

        Args:
            position: Posición candidata
            label: Etiqueta a evaluar
            elements: Lista de elementos del diagrama
            placed_labels: Lista de bboxes de etiquetas ya colocadas
            connections: Lista de conexiones con endpoints (opcional, v3.2)

        Returns:
            float: Score de la posición (menor es mejor)
        """
        score = 0.0

        # Calcular bbox de la etiqueta en esta posición
        label_bbox = self.geometry.get_text_bbox(
            position.x,
            position.y,
            label.text,
            label.font_size,
            position.anchor
        )

        # Verificar si está fuera del canvas
        x1, y1, x2, y2 = label_bbox
        if x1 < 0 or y1 < 0 or x2 > self.canvas_width or y2 > self.canvas_height:
            score += 1000  # Penalización severa

        # Colisiones con elementos
        if self.geometry.label_intersects_elements(label_bbox, elements):
            score += 100

        # Colisiones con otras etiquetas
        if self.geometry.label_intersects_labels(label_bbox, placed_labels):
            score += 50

        # Colisiones con líneas de conexión (v3.2)
        if connections:
            # Crear lookup de elementos por ID
            elements_by_id = {elem.get('id'): elem for elem in elements if elem.get('id')}

            for conn in connections:
                # Obtener endpoints de la conexión
                from_elem = elements_by_id.get(conn.get('from'))
                to_elem = elements_by_id.get(conn.get('to'))

                if from_elem and to_elem:
                    # Calcular centro de cada elemento
                    from_x = from_elem.get('x', 0) + from_elem.get('width', 80) / 2
                    from_y = from_elem.get('y', 0) + from_elem.get('height', 50) / 2
                    to_x = to_elem.get('x', 0) + to_elem.get('width', 80) / 2
                    to_y = to_elem.get('y', 0) + to_elem.get('height', 50) / 2

                    line_endpoints = (from_x, from_y, to_x, to_y)

                    # Verificar si la línea cruza el bbox de la etiqueta
                    if self.geometry.line_intersects_rect(line_endpoints, label_bbox):
                        score += 75
                        if self.debug:
                            logger.debug(f"    Colisión con línea {conn.get('from')}->{conn.get('to')} (+75)")

        # Distancia al anchor (preferir cerca)
        distance = ((position.x - label.anchor_x)**2 + (position.y - label.anchor_y)**2)**0.5
        score += distance / 10

        # Penalización por densidad local (evitar clustering) - v3.1
        # Configuración optimizada: radius=75px, penalty=60
        # Balance entre detección efectiva y no sobre-penalizar
        density = self.calculate_local_density(label_bbox, placed_labels, radius=75.0)
        density_penalty = density * 60
        score += density_penalty
        if self.debug and density > 0:
            logger.debug(f"    Densidad local: {density} etiquetas cercanas (+{density_penalty})")

        # Preferencia por posición "top" para conexiones
        if label.category == "connection" and position.offset_name == "top":
            score -= 10

        # Preferencia por posición "top" centrada para contenedores
        if label.category == "container" and position.offset_name == "top":
            score -= 20

        # Preferencia suave por posición "bottom" para elementos (ícono)
        if label.category == "element" and position.offset_name == "bottom":
            score -= 15  # Preferencia suave (permite optimización dinámica)

        return score

    def optimize_labels(
        self,
        labels: List[Label],
        elements: List[dict],
        connections: List[dict] = None
    ) -> Dict[str, LabelPosition]:
        """
        Optimiza posiciones de todas las etiquetas minimizando colisiones.

        Algoritmo greedy:
        1. Ordenar etiquetas por prioridad (alta primero)
        2. Para cada etiqueta:
           - Generar posiciones candidatas
           - Evaluar cada posición considerando etiquetas ya colocadas
           - Asignar la mejor posición (score mínimo)

        Args:
            labels: Lista de etiquetas a posicionar
            elements: Lista de elementos del diagrama
            connections: Lista de conexiones para detectar colisiones (opcional, v3.2)

        Returns:
            Dict[str, LabelPosition]: Mapa de label_id → mejor posición
        """
        # Separar etiquetas fijas de optimizables
        fixed_labels = [lbl for lbl in labels if lbl.fixed]
        optimizable = [lbl for lbl in labels if not lbl.fixed]

        logger.debug(f"\nOptimizando {len(labels)} etiquetas:")
        logger.debug(f"  - Fijas: {len(fixed_labels)}")
        logger.debug(f"  - Optimizables: {len(optimizable)}")

        # Ordenar por prioridad (0 = alta prioridad primero)
        optimizable.sort(key=lambda lbl: lbl.priority)

        if self.debug:
            priority_counts = {}
            for lbl in optimizable:
                priority_counts[lbl.priority] = priority_counts.get(lbl.priority, 0) + 1
            logger.debug(f"  - Prioridades: {priority_counts}")

        # Resultado
        best_positions = {}

        # Etiquetas ya colocadas (bboxes)
        placed_bboxes = []

        # Procesar etiquetas fijas primero
        for label in fixed_labels:
            # Posición fija (usar anchor directo)
            fixed_pos = LabelPosition(
                label_id=label.id,
                x=label.anchor_x,
                y=label.anchor_y - 10,  # Offset default
                anchor="middle",
                offset_name="fixed"
            )
            best_positions[label.id] = fixed_pos

            # Agregar a placed_bboxes
            bbox = self.geometry.get_text_bbox(
                fixed_pos.x,
                fixed_pos.y,
                label.text,
                label.font_size,
                fixed_pos.anchor
            )
            placed_bboxes.append(bbox)

        # Optimizar etiquetas movibles
        for idx, label in enumerate(optimizable, 1):
            if self.debug:
                logger.debug(f"\n[{idx}/{len(optimizable)}] Procesando: {label.id[:30]}...")
                logger.debug(f"  Texto: '{label.text[:40]}...' " if len(label.text) > 40 else f"  Texto: '{label.text}'")
                logger.debug(f"  Categoria: {label.category}, Prioridad: {label.priority}")

            # Encontrar el elemento correspondiente para obtener su tamaño
            element_width, element_height = 80.0, 50.0  # Valores por defecto
            for elem in elements:
                if elem.get('id') == label.id:
                    element_width = elem.get('width', 80.0)
                    element_height = elem.get('height', 50.0)
                    break

            # Generar candidatos con el tamaño del elemento
            candidates = self.generate_candidate_positions(label, element_width, element_height)
            if self.debug:
                logger.debug(f"  Candidatos generados: {len(candidates)}")

            # Evaluar cada candidato
            best_score = float('inf')
            best_position = None

            for candidate in candidates:
                score = self.score_position(candidate, label, elements, placed_bboxes, connections)
                candidate.score = score

                if self.debug:
                    logger.debug(f"    {candidate.offset_name}: score={score:.2f}")

                if score < best_score:
                    best_score = score
                    best_position = candidate

            # Guardar mejor posición
            if best_position:
                if self.debug:
                    logger.debug(f"  Mejor posicion: {best_position.offset_name} (score: {best_score:.2f})")
                    if best_score > 50:
                        logger.warning(f"    ALTO SCORE detectado para '{label.id[:30]}' - posible colision")

                best_positions[label.id] = best_position

                # Agregar a placed_bboxes
                bbox = self.geometry.get_text_bbox(
                    best_position.x,
                    best_position.y,
                    label.text,
                    label.font_size,
                    best_position.anchor
                )
                placed_bboxes.append(bbox)

        if self.debug:
            high_scores = sum(1 for pos in best_positions.values() if pos.score > 50)
            logger.debug(f"\n[RESUMEN] Optimizacion completada:")
            logger.debug(f"  - Total posicionadas: {len(best_positions)}")
            logger.debug(f"  - Con score alto (>50): {high_scores}")
            if high_scores > 0:
                logger.warning(f"  {high_scores} etiqueta(s) tienen score alto - revisar colisiones")

        return best_positions
