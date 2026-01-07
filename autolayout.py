"""
AlmaGag.autolayout

Clase AutoLayout v2.0 para detección y resolución de colisiones.
Maneja el posicionamiento inteligente de etiquetas considerando
íconos, conexiones, estructura del grafo y prioridades.

Uso:
    layout = AutoLayout(elements, connections, canvas)
    if layout.has_collisions():
        layout.optimize(max_iterations=5)
    elements, label_positions, conn_labels = layout.get_result()
    recommended_canvas = layout.recommended_canvas

Autor: Jose + ALMA
Fecha: 2025-07-06
Version: 2.0
"""

from copy import deepcopy
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


class AutoLayout:
    """
    Clase v2.0 para optimizar el layout de diagramas evitando colisiones.

    Detecta colisiones entre:
    - Etiquetas de íconos vs otros íconos
    - Etiquetas de íconos vs etiquetas de conexiones
    - Etiquetas de íconos vs líneas de conexión
    - Etiquetas de conexiones vs íconos

    Estrategia de resolución v2.0:
    1. Analiza estructura del grafo (niveles, grupos, prioridades)
    2. Posiciona etiquetas respetando prioridades
    3. Intenta mover etiquetas a posiciones alternativas
    4. Desplaza niveles completos si es necesario
    5. Expande el canvas como último recurso
    """

    # Posiciones a probar en orden de preferencia
    POSITIONS = ['bottom', 'right', 'top', 'left']

    # Sistema de prioridades
    PRIORITY_ORDER = {'high': 0, 'normal': 1, 'low': 2}

    def __init__(self, elements, connections, canvas=None):
        """
        Inicializa el AutoLayout v2.0.

        Args:
            elements: Lista de elementos del diagrama
            connections: Lista de conexiones
            canvas: Dict con 'width' y 'height' (opcional)
        """
        self.original_elements = elements
        self.connections = connections
        self.elements = deepcopy(elements)
        self.elements_by_id = {e['id']: e for e in self.elements}

        # Canvas original y recomendado
        self.original_canvas = canvas or {'width': 1400, 'height': 900}
        self.recommended_canvas = dict(self.original_canvas)

        # Posiciones calculadas para etiquetas
        self.label_positions = {}      # {element_id: (x, y, anchor, position)}
        self.connection_labels = {}    # {conn_key: (x, y)}

        # v2.0: Análisis de estructura del grafo
        self.graph = {}                # {element_id: [connected_ids]}
        self.levels = {}               # {element_id: level_number}
        self.groups = []               # [[elem_ids grupo 1], ...]

        # Construir estructura del grafo
        self._build_graph()
        self._calculate_levels()
        self._identify_groups()

        # Calcular posiciones iniciales
        self._calculate_initial_positions()

    # =========================================================================
    # v2.0: ANÁLISIS DE ESTRUCTURA DEL GRAFO
    # =========================================================================

    def _build_graph(self):
        """
        Construye grafo de adyacencia desde connections.

        Returns:
            dict: {element_id: [connected_ids]}
        """
        self.graph = {e['id']: [] for e in self.elements}
        for conn in self.connections:
            from_id = conn['from']
            to_id = conn['to']
            if from_id in self.graph:
                self.graph[from_id].append(to_id)
            if to_id in self.graph:
                self.graph[to_id].append(from_id)

    def _calculate_levels(self):
        """
        Asigna nivel (fila lógica) a cada elemento basado en su posición Y.
        Elementos con Y similar (±80px) están en el mismo nivel.

        Returns:
            dict: {element_id: level_number}
        """
        sorted_by_y = sorted(self.elements, key=lambda e: e['y'])
        self.levels = {}
        current_level = 0
        last_y = -100

        for elem in sorted_by_y:
            if elem['y'] - last_y > 80:  # Nueva fila
                current_level += 1
            self.levels[elem['id']] = current_level
            last_y = elem['y']

    def _identify_groups(self):
        """
        Identifica subgrafos conectados usando DFS.

        Returns:
            list: [[elem_ids del grupo 1], [elem_ids del grupo 2], ...]
        """
        visited = set()
        self.groups = []

        def dfs(node, group):
            if node in visited:
                return
            visited.add(node)
            group.append(node)
            for neighbor in self.graph.get(node, []):
                dfs(neighbor, group)

        for elem in self.elements:
            if elem['id'] not in visited:
                group = []
                dfs(elem['id'], group)
                self.groups.append(group)

    def _calculate_auto_priority(self, element_id):
        """
        Calcula prioridad automática basada en número de conexiones.
        Elementos con más conexiones son más importantes.

        Args:
            element_id: ID del elemento

        Returns:
            str: 'high', 'normal', o 'low'
        """
        connections = len(self.graph.get(element_id, []))
        if connections >= 4:
            return 'high'
        elif connections >= 2:
            return 'normal'
        return 'low'

    def _get_element_priority(self, element):
        """
        Obtiene prioridad de un elemento (manual o automática).

        Args:
            element: Dict del elemento

        Returns:
            int: Valor de prioridad (0=high, 1=normal, 2=low)
        """
        # Prioridad manual tiene precedencia
        manual_priority = element.get('label_priority')
        if manual_priority in self.PRIORITY_ORDER:
            return self.PRIORITY_ORDER[manual_priority]

        # Calcular automáticamente
        auto_priority = self._calculate_auto_priority(element['id'])
        return self.PRIORITY_ORDER[auto_priority]

    # =========================================================================
    # v2.0: DESPLAZAMIENTO DE NIVELES Y EXPANSIÓN DE CANVAS
    # =========================================================================

    def _shift_level_down(self, from_level, delta_y=60):
        """
        Desplaza todos los elementos desde un nivel hacia abajo.

        Args:
            from_level: Nivel desde el cual desplazar
            delta_y: Cantidad de píxeles a desplazar
        """
        for elem in self.elements:
            if self.levels.get(elem['id'], 0) >= from_level:
                elem['y'] += delta_y

        # Actualizar elements_by_id
        self.elements_by_id = {e['id']: e for e in self.elements}

        # Recalcular niveles
        self._calculate_levels()

    def _find_most_problematic_level(self):
        """
        Identifica el nivel con más colisiones.

        Returns:
            int: Número de nivel problemático, o None
        """
        level_collisions = {}

        for elem in self.elements:
            elem_id = elem['id']
            collisions = self._count_element_collisions(elem_id)
            level = self.levels.get(elem_id, 0)
            level_collisions[level] = level_collisions.get(level, 0) + collisions

        if not level_collisions:
            return None

        max_level = max(level_collisions, key=level_collisions.get)
        if level_collisions[max_level] > 0:
            return max_level
        return None

    def _expand_canvas_if_needed(self):
        """
        Expande el canvas si los elementos + etiquetas exceden el tamaño actual.
        """
        # Calcular espacio necesario
        max_x = max(e['x'] + ICON_WIDTH for e in self.elements)
        max_y = max(e['y'] + ICON_HEIGHT for e in self.elements)

        # Agregar espacio para etiquetas (estimado)
        needed_width = max_x + 200   # Margen para etiquetas a la derecha
        needed_height = max_y + 120  # Margen para etiquetas abajo

        # Actualizar canvas recomendado
        self.recommended_canvas = {
            'width': max(needed_width, self.original_canvas.get('width', 1400)),
            'height': max(needed_height, self.original_canvas.get('height', 900))
        }

    def _try_relocate_labels(self):
        """
        Intenta reubicar etiquetas con colisiones a otras posiciones.

        Returns:
            bool: True si se mejoró alguna posición
        """
        improved = False

        for elem in self.elements:
            if not elem.get('label'):
                continue

            elem_id = elem['id']
            current_collisions = self._count_element_collisions(elem_id)

            if current_collisions == 0:
                continue

            # Probar otras posiciones
            current_pos = self.label_positions.get(elem_id)
            if not current_pos:
                continue

            current_position_name = current_pos[3]
            best_collisions = current_collisions
            best_pos = current_pos

            for pos_name in self.POSITIONS:
                if pos_name == current_position_name:
                    continue

                # Temporalmente cambiar posición
                test_pos = self._get_text_coords(elem, pos_name, len(elem.get('label', '').split('\n')))
                self.label_positions[elem_id] = test_pos

                new_collisions = self._count_element_collisions(elem_id)
                if new_collisions < best_collisions:
                    best_collisions = new_collisions
                    best_pos = test_pos

            # Restaurar mejor posición
            self.label_positions[elem_id] = best_pos
            if best_collisions < current_collisions:
                improved = True

        return improved

    def _calculate_initial_positions(self):
        """
        Calcula posiciones iniciales de todas las etiquetas.
        v2.0: Ordena por prioridad para que elementos importantes
        obtengan sus posiciones preferidas primero.
        """
        # Calcular posiciones de etiquetas de conexiones primero
        for conn in self.connections:
            if conn.get('label'):
                key = f"{conn['from']}->{conn['to']}"
                self.connection_labels[key] = self._get_connection_center(conn)

        # v2.0: Ordenar elementos por prioridad (high primero)
        sorted_elements = sorted(
            self.elements,
            key=lambda e: self._get_element_priority(e)
        )

        # Calcular posiciones de etiquetas de íconos en orden de prioridad
        for elem in sorted_elements:
            if elem.get('label'):
                preferred = elem.get('label_position', 'bottom')
                pos = self._find_best_label_position(elem, preferred)
                self.label_positions[elem['id']] = pos

    def _get_icon_bbox(self, element):
        """
        Retorna bounding box del ícono.

        Returns:
            tuple: (x1, y1, x2, y2)
        """
        x, y = element['x'], element['y']
        return (x, y, x + ICON_WIDTH, y + ICON_HEIGHT)

    def _get_text_coords(self, element, position, num_lines=1):
        """
        Calcula coordenadas del texto según posición.

        Returns:
            tuple: (x, y, anchor, position_name)
        """
        x, y = element['x'], element['y']
        center_x = x + ICON_WIDTH // 2
        center_y = y + ICON_HEIGHT // 2

        if position == 'bottom':
            return (center_x, y + ICON_HEIGHT + 20, 'middle', 'bottom')
        elif position == 'top':
            text_y = y - 10 - ((num_lines - 1) * 18)
            return (center_x, text_y, 'middle', 'top')
        elif position == 'right':
            return (x + ICON_WIDTH + 15, center_y, 'start', 'right')
        elif position == 'left':
            return (x - 15, center_y, 'end', 'left')
        else:
            return (center_x, y + ICON_HEIGHT + 20, 'middle', 'bottom')

    def _get_label_bbox(self, element, position):
        """
        Calcula bounding box de una etiqueta de ícono.

        Returns:
            tuple: (x1, y1, x2, y2) o None si no hay etiqueta
        """
        label = element.get('label', '')
        if not label:
            return None

        lines = label.split('\n')
        num_lines = len(lines)
        max_line_len = max(len(line) for line in lines)

        text_x, text_y, anchor, _ = self._get_text_coords(element, position, num_lines)

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

    def _get_connection_endpoints(self, connection):
        """
        Calcula los puntos de inicio y fin de una conexión.

        Returns:
            tuple: (x1, y1, x2, y2) o None si no se puede calcular
        """
        from_elem = self.elements_by_id.get(connection['from'])
        to_elem = self.elements_by_id.get(connection['to'])

        if not from_elem or not to_elem:
            return None

        x1 = from_elem['x'] + ICON_WIDTH // 2
        y1 = from_elem['y'] + ICON_HEIGHT // 2
        x2 = to_elem['x'] + ICON_WIDTH // 2
        y2 = to_elem['y'] + ICON_HEIGHT // 2

        return (x1, y1, x2, y2)

    def _get_connection_center(self, connection):
        """
        Calcula el centro de una conexión.

        Returns:
            tuple: (x, y)
        """
        endpoints = self._get_connection_endpoints(connection)
        if not endpoints:
            return (0, 0)

        x1, y1, x2, y2 = endpoints
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def _get_connection_line_bbox(self, connection, padding=8):
        """
        Calcula bounding box de la línea de conexión.

        Para líneas verticales u horizontales, crea un rectángulo delgado.
        Para líneas diagonales, crea un rectángulo que envuelve la línea.

        Args:
            connection: Diccionario de conexión
            padding: Padding alrededor de la línea (default: 8px)

        Returns:
            tuple: (x1, y1, x2, y2) o None
        """
        endpoints = self._get_connection_endpoints(connection)
        if not endpoints:
            return None

        x1, y1, x2, y2 = endpoints

        # Crear bbox con padding
        min_x = min(x1, x2) - padding
        max_x = max(x1, x2) + padding
        min_y = min(y1, y2) - padding
        max_y = max(y1, y2) + padding

        return (min_x, min_y, max_x, max_y)

    def _line_intersects_rect(self, line_endpoints, rect):
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
        if not self._rectangles_intersect(line_bbox, rect):
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

    def _get_connection_label_bbox(self, connection):
        """
        Calcula bounding box de una etiqueta de conexión.

        Returns:
            tuple: (x1, y1, x2, y2) o None si no hay etiqueta
        """
        label = connection.get('label', '')
        if not label:
            return None

        key = f"{connection['from']}->{connection['to']}"
        center = self.connection_labels.get(key, self._get_connection_center(connection))
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

    def _rectangles_intersect(self, rect1, rect2):
        """
        Verifica si dos rectángulos se intersectan.

        Args:
            rect1, rect2: tuplas (x1, y1, x2, y2)

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

    def _collect_all_bboxes(self):
        """
        Recolecta todos los bounding boxes del diagrama.

        Returns:
            list: Lista de tuplas (bbox, type, id)
        """
        bboxes = []

        # Bboxes de íconos
        for elem in self.elements:
            bbox = self._get_icon_bbox(elem)
            bboxes.append((bbox, 'icon', elem['id']))

        # Bboxes de etiquetas de íconos
        for elem in self.elements:
            if elem['id'] in self.label_positions:
                pos_info = self.label_positions[elem['id']]
                position = pos_info[3]  # (x, y, anchor, position)
                bbox = self._get_label_bbox(elem, position)
                if bbox:
                    bboxes.append((bbox, 'icon_label', elem['id']))

        # Bboxes de etiquetas de conexiones
        for conn in self.connections:
            bbox = self._get_connection_label_bbox(conn)
            if bbox:
                key = f"{conn['from']}->{conn['to']}"
                bboxes.append((bbox, 'conn_label', key))

        return bboxes

    def _collect_all_lines(self):
        """
        Recolecta todas las líneas de conexión.

        Returns:
            list: Lista de tuplas (endpoints, conn_key)
                  donde endpoints es (x1, y1, x2, y2)
        """
        lines = []
        for conn in self.connections:
            endpoints = self._get_connection_endpoints(conn)
            if endpoints:
                key = f"{conn['from']}->{conn['to']}"
                lines.append((endpoints, key))
        return lines

    def count_collisions(self):
        """
        Cuenta el número total de colisiones.

        Incluye:
        - Colisiones entre bboxes (íconos, etiquetas)
        - Colisiones entre líneas y etiquetas de íconos

        Returns:
            int: Número de colisiones detectadas
        """
        bboxes = self._collect_all_bboxes()
        lines = self._collect_all_lines()
        collision_count = 0

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

                # Verificar intersección
                if self._rectangles_intersect(bbox1, bbox2):
                    collision_count += 1

        # Colisiones entre líneas y etiquetas de íconos
        for bbox, bbox_type, bbox_id in bboxes:
            if bbox_type != 'icon_label':
                continue

            for endpoints, conn_key in lines:
                # No contar colisión si la línea conecta este elemento
                from_id, to_id = conn_key.split('->')
                if bbox_id in (from_id, to_id):
                    continue

                if self._line_intersects_rect(endpoints, bbox):
                    collision_count += 1

        return collision_count

    def has_collisions(self):
        """
        Verifica si hay alguna colisión.

        Returns:
            bool: True si hay al menos una colisión
        """
        return self.count_collisions() > 0

    def _find_best_label_position(self, element, preferred='bottom'):
        """
        Encuentra la mejor posición para una etiqueta.

        Considera colisiones con:
        - Otros íconos
        - Etiquetas de conexiones
        - Etiquetas de otros íconos
        - Líneas de conexión (NUEVO)

        Args:
            element: Elemento del diagrama
            preferred: Posición preferida

        Returns:
            tuple: (x, y, anchor, position)
        """
        label = element.get('label', '')
        if not label:
            return None

        num_lines = len(label.split('\n'))

        # Ordenar posiciones con preferida primero
        positions = list(self.POSITIONS)
        if preferred in positions:
            positions.remove(preferred)
            positions.insert(0, preferred)

        # Recolectar bboxes de otros elementos (íconos y etiquetas existentes)
        occupied_bboxes = []
        for elem in self.elements:
            if elem['id'] != element['id']:
                occupied_bboxes.append(self._get_icon_bbox(elem))

        # Añadir etiquetas de conexiones
        for conn in self.connections:
            bbox = self._get_connection_label_bbox(conn)
            if bbox:
                occupied_bboxes.append(bbox)

        # Añadir etiquetas de otros íconos ya calculadas
        for elem_id, pos_info in self.label_positions.items():
            if elem_id != element['id']:
                other_elem = self.elements_by_id.get(elem_id)
                if other_elem:
                    bbox = self._get_label_bbox(other_elem, pos_info[3])
                    if bbox:
                        occupied_bboxes.append(bbox)

        # Recolectar líneas de conexión (excluyendo las que conectan este elemento)
        connection_lines = []
        element_id = element.get('id', '')
        for conn in self.connections:
            # Incluir todas las líneas, incluso las conectadas a este elemento
            endpoints = self._get_connection_endpoints(conn)
            if endpoints:
                connection_lines.append(endpoints)

        # Probar cada posición
        for pos in positions:
            text_bbox = self._get_label_bbox(element, pos)
            if text_bbox is None:
                continue

            has_collision = False

            # Verificar colisión con bboxes
            for occ_bbox in occupied_bboxes:
                if self._rectangles_intersect(text_bbox, occ_bbox):
                    has_collision = True
                    break

            # Verificar colisión con líneas de conexión
            if not has_collision:
                for line in connection_lines:
                    if self._line_intersects_rect(line, text_bbox):
                        has_collision = True
                        break

            if not has_collision:
                return self._get_text_coords(element, pos, num_lines)

        # Si todas colisionan, usar preferida
        return self._get_text_coords(element, preferred, num_lines)

    def _count_element_collisions(self, element_id):
        """
        Cuenta colisiones de un elemento específico.

        Incluye colisiones con:
        - Etiquetas de otros íconos
        - Otros íconos
        - Líneas de conexión

        Returns:
            int: Número de colisiones del elemento
        """
        elem = self.elements_by_id.get(element_id)
        if not elem:
            return 0

        count = 0
        icon_bbox = self._get_icon_bbox(elem)

        # Colisiones del ícono con etiquetas de otros
        for other_id, pos_info in self.label_positions.items():
            if other_id == element_id:
                continue
            other_elem = self.elements_by_id.get(other_id)
            if other_elem:
                label_bbox = self._get_label_bbox(other_elem, pos_info[3])
                if self._rectangles_intersect(icon_bbox, label_bbox):
                    count += 1

        # Colisiones de mi etiqueta con otros íconos y líneas
        if element_id in self.label_positions:
            my_label_bbox = self._get_label_bbox(elem, self.label_positions[element_id][3])

            # Con otros íconos
            for other_elem in self.elements:
                if other_elem['id'] == element_id:
                    continue
                other_icon_bbox = self._get_icon_bbox(other_elem)
                if self._rectangles_intersect(my_label_bbox, other_icon_bbox):
                    count += 1

            # Con líneas de conexión (que no conectan este elemento)
            for conn in self.connections:
                from_id = conn['from']
                to_id = conn['to']
                if element_id in (from_id, to_id):
                    continue
                endpoints = self._get_connection_endpoints(conn)
                if self._line_intersects_rect(endpoints, my_label_bbox):
                    count += 1

        return count

    def _find_most_problematic_element(self):
        """
        Identifica el elemento con más colisiones.

        Returns:
            str: ID del elemento más problemático, o None
        """
        max_collisions = 0
        problematic_id = None

        for elem in self.elements:
            collisions = self._count_element_collisions(elem['id'])
            if collisions > max_collisions:
                max_collisions = collisions
                problematic_id = elem['id']

        return problematic_id

    def _shift_element(self, element_id, dx=0, dy=60):
        """
        Desplaza un elemento y recalcula posiciones.

        Args:
            element_id: ID del elemento a desplazar
            dx: Desplazamiento horizontal
            dy: Desplazamiento vertical
        """
        elem = self.elements_by_id.get(element_id)
        if elem:
            elem['x'] += dx
            elem['y'] += dy

    def optimize(self, max_iterations=5):
        """
        Ejecuta el algoritmo de optimización v2.0.

        Estrategia de resolución:
        1. Intentar reubicar etiquetas a posiciones alternativas
        2. Desplazar niveles completos si hay colisiones persistentes
        3. Expandir el canvas como último recurso

        Args:
            max_iterations: Máximo número de iteraciones

        Returns:
            int: Número de colisiones restantes
        """
        best_config = None
        min_collisions = float('inf')

        for iteration in range(max_iterations):
            collision_count = self.count_collisions()

            # Guardar mejor configuración
            if collision_count < min_collisions:
                min_collisions = collision_count
                best_config = (
                    deepcopy(self.elements),
                    dict(self.label_positions),
                    dict(self.connection_labels),
                    dict(self.recommended_canvas)
                )

            if collision_count == 0:
                break

            # Estrategia A: Intentar reubicar etiquetas
            improved = self._try_relocate_labels()
            if improved:
                continue

            # Estrategia B: Desplazar nivel problemático
            problem_level = self._find_most_problematic_level()
            if problem_level is not None:
                self._shift_level_down(problem_level + 1, delta_y=60)
                # Recalcular posiciones después del desplazamiento
                self.label_positions = {}
                self.connection_labels = {}
                self._calculate_initial_positions()
                continue

            # Estrategia C: Expandir canvas (último recurso)
            self._expand_canvas_if_needed()
            break

        # Restaurar mejor configuración encontrada
        if best_config and min_collisions < self.count_collisions():
            self.elements = best_config[0]
            self.label_positions = best_config[1]
            self.connection_labels = best_config[2]
            self.recommended_canvas = best_config[3]
            self.elements_by_id = {e['id']: e for e in self.elements}

        return min_collisions

    def get_result(self):
        """
        Retorna el resultado de la optimización.

        Returns:
            tuple: (elements, label_positions, connection_labels)
                - elements: Lista de elementos (posiblemente modificados)
                - label_positions: Dict {id: (x, y, anchor, position)}
                - connection_labels: Dict {conn_key: (x, y)}
        """
        return (self.elements, self.label_positions, self.connection_labels)
