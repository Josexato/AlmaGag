"""
ContainerCalculator - Calcula dimensiones de contenedores

Este módulo calcula las dimensiones de los contenedores basándose en los
elementos que contienen. Los contenedores deben tener sus dimensiones
calculadas DESPUÉS de posicionar elementos, pero ANTES de la optimización
de colisiones, para que se consideren como obstáculos reales.

Autor: José + ALMA
Versión: v2.1
Fecha: 2026-01-08
"""

from typing import Dict, List, Tuple
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


class ContainerCalculator:
    """
    Calcula dimensiones de contenedores basándose en elementos contenidos.

    Los contenedores se tratan como elementos grandes cuyo tamaño depende
    de los elementos que contienen más un padding.
    """

    def __init__(self, sizing_calculator=None):
        """
        Inicializa el calculador de contenedores.

        Args:
            sizing_calculator: SizingCalculator para elementos con hp/wp
        """
        self.sizing = sizing_calculator

    def calculate_container_bounds(
        self,
        container: dict,
        elements_by_id: Dict[str, dict]
    ) -> Tuple[float, float, float, float]:
        """
        Calcula el bounding box de un contenedor basado en sus elementos.

        Args:
            container: Elemento contenedor con 'contains'
            elements_by_id: Mapa de id → elemento

        Returns:
            Tuple: (x, y, width, height) del contenedor
        """
        contains = container.get('contains', [])
        if not contains:
            # Sin elementos contenidos, usar tamaño por defecto
            x = container.get('x', 0)
            y = container.get('y', 0)
            return (x, y, 200, 150)

        # Padding (espacio interno)
        padding = container.get('padding', 40)

        # Encontrar bounds de todos los elementos contenidos
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for item in contains:
            # Soportar formato dict {"id": "...", "scope": "..."} o string directo
            elem_id = item['id'] if isinstance(item, dict) else item

            if elem_id not in elements_by_id:
                continue

            elem = elements_by_id[elem_id]

            # Validar que elemento tiene coordenadas
            if elem.get('x') is None or elem.get('y') is None:
                continue

            elem_x = elem['x']
            elem_y = elem['y']

            # Obtener tamaño del elemento (considerando hp/wp)
            if self.sizing:
                elem_w, elem_h = self.sizing.get_element_size(elem)
            else:
                elem_w, elem_h = ICON_WIDTH, ICON_HEIGHT

            min_x = min(min_x, elem_x)
            min_y = min(min_y, elem_y)
            max_x = max(max_x, elem_x + elem_w)
            max_y = max(max_y, elem_y + elem_h)

        # Si no se encontró ningún elemento válido, usar defaults
        if min_x == float('inf'):
            x = container.get('x', 0)
            y = container.get('y', 0)
            return (x, y, 200, 150)

        # Aplicar padding
        x = min_x - padding
        y = min_y - padding
        width = (max_x - min_x) + (2 * padding)
        height = (max_y - min_y) + (2 * padding)

        # Aplicar aspect_ratio si se especifica
        aspect_ratio = container.get('aspect_ratio')
        if aspect_ratio and height > 0:
            current_ratio = width / height
            if current_ratio < aspect_ratio:
                # Ensanchar
                new_width = height * aspect_ratio
                x -= (new_width - width) / 2
                width = new_width
            elif current_ratio > aspect_ratio:
                # Alargar
                new_height = width / aspect_ratio
                y -= (new_height - height) / 2
                height = new_height

        return (x, y, width, height)

    def update_container_dimensions(self, layout) -> None:
        """
        Actualiza las dimensiones de todos los contenedores en el layout.

        Modifica los contenedores in-place agregando/actualizando:
        - x, y: Posición superior izquierda
        - width, height: Dimensiones del contenedor

        Esto permite que los contenedores se traten como elementos grandes
        en la detección de colisiones y optimización.

        Args:
            layout: Layout con elements y elements_by_id
        """
        for elem in layout.elements:
            if 'contains' not in elem:
                continue

            # Calcular bounds del contenedor
            x, y, width, height = self.calculate_container_bounds(
                elem,
                layout.elements_by_id
            )

            # Actualizar dimensiones del contenedor
            elem['x'] = x
            elem['y'] = y
            elem['width'] = width
            elem['height'] = height

            # Marcar como contenedor calculado para que collision detector lo trate correctamente
            elem['_is_container_calculated'] = True
