"""
CollisionDetector - Detección de colisiones entre elementos del diagrama

Este módulo detecta colisiones entre:
- Etiquetas de íconos vs otros íconos
- Etiquetas de íconos vs etiquetas de conexiones
- Etiquetas de íconos vs líneas de conexión
- Etiquetas de íconos vs etiquetas de otros íconos
"""

from typing import List, Tuple
from AlmaGag.layout.geometry import GeometryCalculator


class CollisionDetector:
    """
    Detector de colisiones para elementos de diagramas.

    Utiliza GeometryCalculator para cálculos geométricos.
    """

    def __init__(self, geometry: GeometryCalculator):
        """
        Inicializa el detector de colisiones.

        Args:
            geometry: Instancia de GeometryCalculator para cálculos geométricos
        """
        self.geometry = geometry

    def _is_parent_child_relation(
        self,
        id1: str,
        id2: str,
        layout
    ) -> bool:
        """
        Verifica si id1 contiene a id2 o viceversa.

        Args:
            id1: ID del primer elemento
            id2: ID del segundo elemento
            layout: Layout con elements_by_id

        Returns:
            True si hay relación padre-hijo directa
        """
        elem1 = layout.elements_by_id.get(id1)
        elem2 = layout.elements_by_id.get(id2)

        # Verificar si elem1 contiene a elem2
        if elem1 and 'contains' in elem1:
            contains = [
                item['id'] if isinstance(item, dict) else item
                for item in elem1['contains']
            ]
            if id2 in contains:
                return True

        # Verificar si elem2 contiene a elem1
        if elem2 and 'contains' in elem2:
            contains = [
                item['id'] if isinstance(item, dict) else item
                for item in elem2['contains']
            ]
            if id1 in contains:
                return True

        return False

    def detect_all_collisions(
        self,
        layout
    ) -> Tuple[int, List[Tuple]]:
        """
        Detecta todas las colisiones en el layout.

        Detecta colisiones entre:
        - Bboxes (íconos, etiquetas de íconos, etiquetas de conexiones)
        - Líneas de conexión vs etiquetas de íconos

        Args:
            layout: Layout a evaluar

        Returns:
            Tuple[int, List[Tuple]]: (collision_count, collision_pairs)
                collision_pairs: [(id1, id2, collision_type), ...]
        """
        bboxes = self._collect_all_bboxes(layout)
        lines = self._collect_all_lines(layout)
        collision_count = 0
        collision_pairs = []

        # Colisiones entre bboxes
        for i, (bbox1, type1, id1) in enumerate(bboxes):
            for j, (bbox2, type2, id2) in enumerate(bboxes):
                if i >= j:
                    continue

                # No contar colisión de un ícono con su propia etiqueta
                if type1 == 'icon' and type2 == 'icon_label' and id1 == id2:
                    continue
                if type1 == 'icon_label' and type2 == 'icon' and id1 == id2:
                    continue

                # No contar colisión contenedor-hijo (FALSO POSITIVO)
                if self._is_parent_child_relation(id1, id2, layout):
                    continue

                # Verificar intersección
                if self.geometry.rectangles_intersect(bbox1, bbox2):
                    collision_count += 1
                    collision_pairs.append((id1, id2, f'{type1}_vs_{type2}'))

        # Colisiones entre líneas y etiquetas de íconos
        for bbox, bbox_type, bbox_id in bboxes:
            if bbox_type != 'icon_label':
                continue

            for endpoints, conn_key in lines:
                # No contar colisión si la línea conecta este elemento
                from_id, to_id = conn_key.split('->')
                if bbox_id in (from_id, to_id):
                    continue

                if self.geometry.line_intersects_rect(endpoints, bbox):
                    collision_count += 1
                    collision_pairs.append((bbox_id, conn_key, 'label_vs_line'))

        return collision_count, collision_pairs

    def count_element_collisions(
        self,
        layout,
        element_id: str
    ) -> int:
        """
        Cuenta colisiones de un elemento específico.

        Incluye colisiones con:
        - Etiquetas de otros íconos
        - Otros íconos
        - Líneas de conexión

        Args:
            layout: Layout a evaluar
            element_id: ID del elemento a evaluar

        Returns:
            int: Número de colisiones del elemento
        """
        elem = layout.elements_by_id.get(element_id)
        if not elem:
            return 0

        # Ignorar contenedores SIN dimensiones calculadas
        # (Contenedores con dimensiones calculadas se tratan como elementos normales)
        if 'contains' in elem and not elem.get('_is_container_calculated', False):
            return 0

        count = 0
        icon_bbox = self.geometry.get_icon_bbox(elem)

        # Colisiones del ícono con etiquetas de otros
        for other_id, pos_info in layout.label_positions.items():
            if other_id == element_id:
                continue
            other_elem = layout.elements_by_id.get(other_id)
            if other_elem:
                label_bbox = self.geometry.get_label_bbox(other_elem, pos_info[3])
                if self.geometry.rectangles_intersect(icon_bbox, label_bbox):
                    count += 1

        # Colisiones de mi etiqueta con otros íconos y líneas
        if element_id in layout.label_positions:
            my_label_bbox = self.geometry.get_label_bbox(
                elem,
                layout.label_positions[element_id][3]
            )

            # Con otros íconos
            for other_elem in layout.elements:
                if other_elem['id'] == element_id:
                    continue
                other_icon_bbox = self.geometry.get_icon_bbox(other_elem)
                if other_icon_bbox and self.geometry.rectangles_intersect(my_label_bbox, other_icon_bbox):
                    count += 1

            # Con líneas de conexión (que no conectan este elemento)
            for conn in layout.connections:
                from_id = conn['from']
                to_id = conn['to']
                if element_id in (from_id, to_id):
                    continue
                endpoints = self.geometry.get_connection_endpoints(layout, conn)
                if self.geometry.line_intersects_rect(endpoints, my_label_bbox):
                    count += 1

        return count

    def _collect_all_bboxes(self, layout) -> List[Tuple]:
        """
        Recolecta todos los bounding boxes del diagrama.

        Args:
            layout: Layout con elementos y posiciones

        Returns:
            List[Tuple]: Lista de tuplas (bbox, type, id)
                bbox: (x1, y1, x2, y2)
                type: 'icon', 'icon_label', 'conn_label'
                id: ID del elemento o clave de conexión
        """
        bboxes = []

        # Filtrar contenedores SIN dimensiones calculadas
        # (Contenedores con dimensiones calculadas se tratan como elementos normales)
        normal_elements = [e for e in layout.elements
                          if 'contains' not in e or e.get('_is_container_calculated', False)]

        # Bboxes de íconos
        for elem in normal_elements:
            bbox = self.geometry.get_icon_bbox(elem)
            bboxes.append((bbox, 'icon', elem['id']))

        # Bboxes de etiquetas de íconos
        for elem in normal_elements:
            if elem['id'] in layout.label_positions:
                pos_info = layout.label_positions[elem['id']]
                position = pos_info[3]  # (x, y, anchor, position)
                bbox = self.geometry.get_label_bbox(elem, position)
                if bbox:
                    bboxes.append((bbox, 'icon_label', elem['id']))

        # Bboxes de etiquetas de conexiones
        for conn in layout.connections:
            bbox = self.geometry.get_connection_label_bbox(layout, conn)
            if bbox:
                key = f"{conn['from']}->{conn['to']}"
                bboxes.append((bbox, 'conn_label', key))

        return bboxes

    def _collect_all_lines(self, layout) -> List[Tuple]:
        """
        Recolecta todas las líneas de conexión.

        Args:
            layout: Layout con conexiones

        Returns:
            List[Tuple]: Lista de tuplas (endpoints, conn_key)
                endpoints: (x1, y1, x2, y2)
                conn_key: "from_id->to_id"
        """
        lines = []
        for conn in layout.connections:
            endpoints = self.geometry.get_connection_endpoints(layout, conn)
            if endpoints:
                key = f"{conn['from']}->{conn['to']}"
                lines.append((endpoints, key))
        return lines
