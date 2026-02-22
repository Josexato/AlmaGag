"""
ContainerCalculator - Calcula dimensiones de contenedores

Este módulo calcula las dimensiones de los contenedores basándose en los
elementos que contienen. Los contenedores deben tener sus dimensiones
calculadas DESPUÉS de posicionar elementos, pero ANTES de la optimización
de colisiones, para que se consideren como obstáculos reales.

v2.2: Ahora considera TAMBIÉN las etiquetas de los elementos contenidos,
      no solo los íconos.

Autor: José + ALMA
Versión: v2.2
Fecha: 2026-01-09
"""

from typing import Dict, List, Tuple
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.utils import extract_item_id


class ContainerCalculator:
    """
    Calcula dimensiones de contenedores basándose en elementos contenidos.

    Los contenedores se tratan como elementos grandes cuyo tamaño depende
    de los elementos que contienen (íconos + etiquetas) más un padding.
    """

    def __init__(self, sizing_calculator=None, geometry_calculator=None):
        """
        Inicializa el calculador de contenedores.

        Args:
            sizing_calculator: SizingCalculator para elementos con hp/wp
            geometry_calculator: GeometryCalculator para bboxes de etiquetas
        """
        self.sizing = sizing_calculator
        self.geometry = geometry_calculator

    def calculate_container_bounds(
        self,
        container: dict,
        layout
    ) -> Tuple[float, float, float, float]:
        """
        Calcula el bounding box de un contenedor basado en sus elementos.

        v2.2: Ahora considera TANTO íconos como etiquetas de elementos contenidos.

        Args:
            container: Elemento contenedor con 'contains'
            layout: Layout con elements_by_id y label_positions

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
        padding = container.get('padding', 10)

        # Encontrar bounds de todos los elementos contenidos (íconos + etiquetas)
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for item in contains:
            # Soportar formato dict {"id": "...", "scope": "..."} o string directo
            elem_id = extract_item_id(item)

            if elem_id not in layout.elements_by_id:
                continue

            elem = layout.elements_by_id[elem_id]

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

            # Considerar bbox del ícono
            min_x = min(min_x, elem_x)
            min_y = min(min_y, elem_y)
            max_x = max(max_x, elem_x + elem_w)
            max_y = max(max_y, elem_y + elem_h)

            # NUEVO v2.2: Considerar TAMBIÉN bbox de la etiqueta del elemento
            if elem_id in layout.label_positions and self.geometry:
                pos_info = layout.label_positions[elem_id]
                position = pos_info[3]  # (x, y, anchor, position)
                label_bbox = self.geometry.get_label_bbox(elem, position)

                if label_bbox:
                    lx1, ly1, lx2, ly2 = label_bbox
                    min_x = min(min_x, lx1)
                    min_y = min(min_y, ly1)
                    max_x = max(max_x, lx2)
                    max_y = max(max_y, ly2)

        # Si no se encontró ningún elemento válido, usar defaults
        if min_x == float('inf'):
            x = container.get('x', 0)
            y = container.get('y', 0)
            return (x, y, 200, 150)

        # Calcular dimensiones del contenido (elementos contenidos)
        content_width = max_x - min_x
        content_height = max_y - min_y

        # Aplicar padding horizontal
        x = min_x - padding
        width = content_width + (2 * padding)

        # Calcular espacio del header del contenedor (icono + etiqueta)
        header_height = 0
        if container.get('label'):
            label_text = container['label']
            lines = label_text.split('\n')
            num_lines = len(lines)
            max_line_len = max(len(line) for line in lines) if lines else 0
            label_width = max_line_len * 8  # 8px por carácter
            label_height = num_lines * 18  # 18px por línea

            # El icono del contenedor tiene 50px de altura
            icon_height = 50

            # El header ocupa el máximo entre icono y etiqueta
            header_height = max(icon_height, label_height)

            # Calcular ancho necesario considerando que la etiqueta está a la derecha del ícono
            # Etiqueta comienza en: 10 (margen) + 80 (ícono) + 10 (margen) = 100
            label_x_position = 10 + ICON_WIDTH + 10
            label_required_width = label_x_position + label_width + 10  # posición + ancho + margen derecho

            # Expandir horizontalmente si es necesario
            if label_required_width > width:
                width = label_required_width

        # Altura total = header + padding_mid + content + padding_bottom
        # = (2 * padding) + header_height + content_height
        height = (2 * padding) + header_height + content_height

        # Posición Y del contenedor (arriba de los elementos)
        # El contenedor empieza en: min_y - (header + padding_mid)
        y = min_y - padding - header_height

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

    def update_container_dimensions(self, layout, debug=False) -> None:
        """
        Actualiza las dimensiones de todos los contenedores en el layout.

        Modifica los contenedores in-place agregando/actualizando:
        - x, y: Posición superior izquierda
        - width, height: Dimensiones del contenedor

        v2.2: Ahora considera tanto íconos como etiquetas de elementos contenidos.

        Esto permite que los contenedores se traten como elementos grandes
        en la detección de colisiones y optimización.

        Args:
            layout: Layout con elements, elements_by_id y label_positions
            debug: Si es True, imprime información de debugging
        """
        import logging
        logger = logging.getLogger('AlmaGag.ContainerCalculator')

        for elem in layout.elements:
            if 'contains' not in elem:
                continue

            # Calcular bounds del contenedor (considerando íconos + etiquetas)
            x, y, width, height = self.calculate_container_bounds(
                elem,
                layout
            )

            if debug:
                logger.debug(f"\n[CONTAINER] {elem['id']}")
                logger.debug(f"  contains: {len(elem.get('contains', []))} elementos")
                logger.debug(f"  dimensiones: ({x:.1f}, {y:.1f}) {width:.1f}x{height:.1f}")

            # Actualizar dimensiones del contenedor
            elem['x'] = x
            elem['y'] = y
            elem['width'] = width
            elem['height'] = height

            # Marcar como contenedor calculado para que collision detector lo trate correctamente
            elem['_is_container_calculated'] = True
