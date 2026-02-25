"""
GeometryCalculator - Cálculos geométricos para bounding boxes y coordenadas

Este módulo es stateless y proporciona métodos puros para cálculos geométricos:
- Bounding boxes de íconos y etiquetas
- Coordenadas de texto según posición
- Endpoints y centros de conexiones
- Detección de intersecciones entre rectángulos y líneas
- Detección de colisiones de etiquetas (v3.0)
"""

from typing import Tuple, Optional, List
from AlmaGag.config import (
    ICON_WIDTH, ICON_HEIGHT,
    LABEL_OFFSET_BOTTOM, LABEL_OFFSET_TOP, LABEL_OFFSET_SIDE,
    TEXT_LINE_HEIGHT, TEXT_CHAR_WIDTH, TEXT_CHAR_WIDTH_NARROW,
    CONNECTION_BBOX_PADDING
)


class GeometryCalculator:
    """
    Calculadora de geometría para elementos de diagramas.

    Esta clase es stateless - todos los métodos son funciones puras que
    toman los datos necesarios como argumentos y retornan resultados sin
    efectos secundarios.
    """

    def __init__(self, sizing=None):
        """
        Inicializa el calculador geométrico.

        Args:
            sizing: Instancia de SizingCalculator para cálculos de tamaño.
                    Si es None, usa dimensiones por defecto (ICON_WIDTH/HEIGHT)
        """
        self.sizing = sizing

    def get_icon_bbox(self, element: dict) -> Optional[Tuple[float, float, float, float]]:
        """
        Calcula bounding box de un ícono o contenedor.

        Args:
            element: Elemento con 'x' e 'y', opcionalmente 'hp'/'wp' para sizing
                     o 'width'/'height' para contenedores

        Returns:
            Optional[Tuple[float, float, float, float]]: (x1, y1, x2, y2) o None si falta coordenada
        """
        # Validar que elemento tiene coordenadas
        x = element.get('x')
        y = element.get('y')
        if x is None or y is None:
            return None

        # Si es contenedor con dimensiones calculadas, usar esas dimensiones
        if 'contains' in element and 'width' in element and 'height' in element:
            width = element['width']
            height = element['height']
        # Usar SizingCalculator si está disponible
        elif self.sizing:
            width, height = self.sizing.get_element_size(element)
        else:
            width, height = ICON_WIDTH, ICON_HEIGHT

        return (x, y, x + width, y + height)

    def get_text_coords(
        self,
        element: dict,
        position: str,
        num_lines: int = 1
    ) -> Tuple[float, float, str, str]:
        """
        Calcula coordenadas del texto según posición.

        Args:
            element: Elemento con 'x' e 'y', opcionalmente 'hp'/'wp' para sizing
            position: 'bottom', 'top', 'left', 'right'
            num_lines: Número de líneas de texto

        Returns:
            Tuple: (x, y, anchor, position_name)
                anchor: 'middle', 'start', 'end'
        """
        x, y = element['x'], element['y']

        # Usar SizingCalculator si está disponible
        if self.sizing:
            width, height = self.sizing.get_element_size(element)
        else:
            width, height = ICON_WIDTH, ICON_HEIGHT

        center_x = x + width // 2
        center_y = y + height // 2

        if position == 'bottom':
            return (center_x, y + height + 20, 'middle', 'bottom')
        elif position == 'top':
            text_y = y - 10 - ((num_lines - 1) * 18)
            return (center_x, text_y, 'middle', 'top')
        elif position == 'right':
            return (x + width + 15, center_y, 'start', 'right')
        elif position == 'left':
            return (x - 15, center_y, 'end', 'left')
        else:
            return (center_x, y + height + 20, 'middle', 'bottom')

    def get_label_bbox(
        self,
        element: dict,
        position: str
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Calcula bounding box de una etiqueta de ícono.

        Args:
            element: Elemento con 'label'
            position: 'bottom', 'top', 'left', 'right'

        Returns:
            Optional[Tuple]: (x1, y1, x2, y2) o None si no hay etiqueta
        """
        label = element.get('label', '')
        if not label:
            return None

        lines = label.split('\n')
        num_lines = len(lines)
        max_line_len = max(len(line) for line in lines)

        text_x, text_y, anchor, _ = self.get_text_coords(element, position, num_lines)

        # Estimación del tamaño del texto (~8px por caracter en Arial 14px)
        text_width = max_line_len * 8
        text_height = num_lines * 18

        # Calcular bbox según anchor
        if anchor == 'middle':
            x1 = text_x - text_width // 2
            x2 = text_x + text_width // 2
        elif anchor == 'start':
            x1 = text_x
            x2 = text_x + text_width
        else:  # 'end'
            x1 = text_x - text_width
            x2 = text_x

        # Ajuste de Y según posición
        if position == 'top':
            y1 = text_y - 14
            y2 = text_y + text_height - 14
        elif position in ('left', 'right'):
            y1 = text_y - (text_height // 2)
            y2 = text_y + (text_height // 2)
        else:  # bottom
            y1 = text_y - 14
            y2 = text_y + text_height - 14

        return (x1, y1, x2, y2)

    def get_connection_endpoints(
        self,
        layout,
        connection: dict
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Calcula los puntos de inicio y fin de una conexión.

        Args:
            layout: Layout con elements_by_id
            connection: Conexión con 'from' y 'to'

        Returns:
            Optional[Tuple]: (x1, y1, x2, y2) o None si no se puede calcular
        """
        from_elem = layout.elements_by_id.get(connection['from'])
        to_elem = layout.elements_by_id.get(connection['to'])

        if not from_elem or not to_elem:
            return None

        # Skip if elements don't have positions yet (e.g. contained elements)
        if 'x' not in from_elem or 'x' not in to_elem:
            return None

        # Calcular centro del elemento 'from' usando sizing si está disponible
        if self.sizing:
            from_width, from_height = self.sizing.get_element_size(from_elem)
            to_width, to_height = self.sizing.get_element_size(to_elem)
        else:
            from_width, from_height = ICON_WIDTH, ICON_HEIGHT
            to_width, to_height = ICON_WIDTH, ICON_HEIGHT

        x1 = from_elem['x'] + from_width // 2
        y1 = from_elem['y'] + from_height // 2
        x2 = to_elem['x'] + to_width // 2
        y2 = to_elem['y'] + to_height // 2

        return (x1, y1, x2, y2)

    def get_connection_center(
        self,
        layout,
        connection: dict
    ) -> Tuple[float, float]:
        """
        Calcula el centro de una conexión.

        Args:
            layout: Layout con elements_by_id
            connection: Conexión con 'from' y 'to'

        Returns:
            Tuple[float, float]: (x, y) - retorna (0, 0) si no se puede calcular
        """
        endpoints = self.get_connection_endpoints(layout, connection)
        if not endpoints:
            return (0, 0)

        x1, y1, x2, y2 = endpoints
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def get_connection_line_bbox(
        self,
        layout,
        connection: dict,
        padding: int = 8
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Calcula bounding box de la línea de conexión.

        Para líneas verticales u horizontales, crea un rectángulo delgado.
        Para líneas diagonales, crea un rectángulo que envuelve la línea.

        Args:
            layout: Layout con elements_by_id
            connection: Diccionario de conexión
            padding: Padding alrededor de la línea (default: 8px)

        Returns:
            Optional[Tuple]: (x1, y1, x2, y2) o None
        """
        endpoints = self.get_connection_endpoints(layout, connection)
        if not endpoints:
            return None

        x1, y1, x2, y2 = endpoints

        # Crear bbox con padding
        min_x = min(x1, x2) - padding
        max_x = max(x1, x2) + padding
        min_y = min(y1, y2) - padding
        max_y = max(y1, y2) + padding

        return (min_x, min_y, max_x, max_y)

    def get_connection_label_bbox(
        self,
        layout,
        connection: dict
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Calcula bounding box de una etiqueta de conexión.

        Args:
            layout: Layout con connection_labels
            connection: Conexión con 'label'

        Returns:
            Optional[Tuple]: (x1, y1, x2, y2) o None si no hay etiqueta
        """
        label = connection.get('label', '')
        if not label:
            return None

        key = f"{connection['from']}->{connection['to']}"
        center = layout.connection_labels.get(
            key,
            self.get_connection_center(layout, connection)
        )
        mid_x, mid_y = center

        # Estimación: 7px por caracter, 12px altura
        text_width = len(label) * 7
        text_height = 16

        return (
            mid_x - text_width // 2,
            mid_y - 10 - text_height,
            mid_x + text_width // 2,
            mid_y - 10
        )

    def rectangles_intersect(
        self,
        rect1: Tuple[float, float, float, float],
        rect2: Tuple[float, float, float, float]
    ) -> bool:
        """
        Verifica si dos rectángulos se intersectan.

        Args:
            rect1: (x1, y1, x2, y2)
            rect2: (x1, y1, x2, y2)

        Returns:
            bool: True si se intersectan
        """
        if rect1 is None or rect2 is None:
            return False

        x1_1, y1_1, x2_1, y2_1 = rect1
        x1_2, y1_2, x2_2, y2_2 = rect2

        if x2_1 < x1_2 or x2_2 < x1_1:
            return False
        if y2_1 < y1_2 or y2_2 < y1_1:
            return False

        return True

    def line_intersects_rect(
        self,
        line_endpoints: Tuple[float, float, float, float],
        rect: Tuple[float, float, float, float]
    ) -> bool:
        """
        Verifica si una línea intersecta con un rectángulo.

        Más preciso que comparar bboxes para líneas diagonales.

        Args:
            line_endpoints: (x1, y1, x2, y2)
            rect: (rx1, ry1, rx2, ry2)

        Returns:
            bool: True si la línea cruza el rectángulo
        """
        if line_endpoints is None or rect is None:
            return False

        x1, y1, x2, y2 = line_endpoints
        rx1, ry1, rx2, ry2 = rect

        # Primero verificar si el bbox de la línea intersecta el rectángulo
        line_bbox = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        if not self.rectangles_intersect(line_bbox, rect):
            return False

        # Para líneas verticales
        if abs(x2 - x1) < 1:
            return rx1 <= x1 <= rx2 and not (max(y1, y2) < ry1 or min(y1, y2) > ry2)

        # Para líneas horizontales
        if abs(y2 - y1) < 1:
            return ry1 <= y1 <= ry2 and not (max(x1, x2) < rx1 or min(x1, x2) > rx2)

        # Para líneas diagonales, verificar si algún punto del rectángulo
        # está en lados opuestos de la línea
        def side(px, py):
            return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)

        corners = [(rx1, ry1), (rx2, ry1), (rx2, ry2), (rx1, ry2)]
        sides = [side(px, py) for px, py in corners]

        # Si todas las esquinas están del mismo lado, no hay intersección
        if all(s > 0 for s in sides) or all(s < 0 for s in sides):
            return False

        return True

    def get_text_bbox(
        self,
        x: float,
        y: float,
        text: str,
        font_size: int = 12,
        anchor: str = "middle"
    ) -> Tuple[float, float, float, float]:
        """
        Calcula bounding box aproximado de un texto (v3.0 - Label Optimizer).

        Args:
            x: Coordenada X del punto de inserción
            y: Coordenada Y del punto de inserción
            text: Texto de la etiqueta
            font_size: Tamaño de fuente en píxeles
            anchor: Alineación del texto ('start', 'middle', 'end')

        Returns:
            Tuple[float, float, float, float]: (x1, y1, x2, y2) del bbox
        """
        # Estimar ancho del texto (6px promedio por carácter para Arial)
        char_width = font_size * 0.6
        lines = text.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else 0
        text_width = max_line_length * char_width

        # Alto del texto
        line_height = font_size * 1.2
        text_height = len(lines) * line_height

        # Ajustar según anchor
        if anchor == "middle":
            x1 = x - text_width / 2
            x2 = x + text_width / 2
        elif anchor == "end":
            x1 = x - text_width
            x2 = x
        else:  # start
            x1 = x
            x2 = x + text_width

        y1 = y - font_size  # Texto va arriba de la coordenada Y
        y2 = y + text_height - font_size

        return (x1, y1, x2, y2)

    def label_intersects_elements(
        self,
        label_bbox: Tuple[float, float, float, float],
        elements: List[dict]
    ) -> bool:
        """
        Verifica si una etiqueta colisiona con algún elemento.

        Args:
            label_bbox: Bounding box de la etiqueta (x1, y1, x2, y2)
            elements: Lista de elementos con coordenadas

        Returns:
            bool: True si hay colisión, False si no
        """
        for elem in elements:
            elem_bbox = self.get_icon_bbox(elem)
            if elem_bbox and self.rectangles_intersect(label_bbox, elem_bbox):
                return True
        return False

    def label_intersects_labels(
        self,
        label_bbox: Tuple[float, float, float, float],
        other_labels: List[Tuple[float, float, float, float]]
    ) -> bool:
        """
        Verifica si una etiqueta colisiona con otras etiquetas.

        Args:
            label_bbox: Bounding box de la etiqueta a verificar
            other_labels: Lista de bboxes de otras etiquetas

        Returns:
            bool: True si hay colisión, False si no
        """
        for other_bbox in other_labels:
            if self.rectangles_intersect(label_bbox, other_bbox):
                return True
        return False
