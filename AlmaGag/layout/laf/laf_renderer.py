"""
LAFSVGRenderer — renderer del algoritmo LAF.

Encapsula toda la lógica de cómo LAF transforma un Layout optimizado en un
archivo SVG. Cada algoritmo de layout tiene su propio renderer; este NO sabe
nada sobre AUTO ni sus convenciones.

Características específicas de LAF:
- Los iconos de containers se dibujan como **elementos separados** (no inline
  en el rect del container), porque LAF los trata como nodos individuales del
  grafo con sus propias coordenadas.
- Soporta el sistema NdFn de etiquetas de debug para inspeccionar el pipeline.
"""

import importlib
import logging

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT, CONTAINER_PADDING, TEXT_LINE_HEIGHT
from AlmaGag.draw.primitives.container import draw_container as _draw_container, calculate_container_bounds
from AlmaGag.draw.icons import draw_icon_shape as _draw_icon_shape, draw_icon_label as _draw_icon_label
from AlmaGag.draw.primitives.svg import (
    create_canvas,
    setup_arrow_markers,
    ndfn_wrap,
    draw_connections,
    draw_connection_labels,
)
from AlmaGag.layout.label_optimizer import LabelPositionOptimizer, Label
from AlmaGag.utils import extract_item_id
from AlmaGag.debug import add_debug_badge, draw_grid, draw_guide_lines, draw_debug_free_ranges, convert_svg_to_png

logger = logging.getLogger('AlmaGag')


class LAFSVGRenderer:
    """Renderer SVG específico del algoritmo LAF."""

    def __init__(self, geometry_calculator):
        """
        Args:
            geometry_calculator: GeometryCalculator usado por LabelPositionOptimizer.
                Generalmente el mismo que usa el optimizer (reutilización).
        """
        self.geometry = geometry_calculator

    # -------- Entry point --------

    def render(
        self,
        layout,
        output_svg,
        *,
        visualdebug=False,
        guide_lines=None,
        debug=False,
        color_connections=False,
        embedded_icons=None,
        exportpng=False,
    ):
        """Orquesta el rendering completo del layout LAF al archivo SVG."""
        canvas_width = layout.canvas['width']
        canvas_height = layout.canvas['height']

        dwg = create_canvas(output_svg, canvas_width, canvas_height)

        if visualdebug:
            add_debug_badge(dwg, canvas_width, canvas_height)
            draw_grid(dwg, canvas_width, canvas_height, grid_size=20)

        if guide_lines:
            draw_guide_lines(dwg, canvas_width, guide_lines)

        if visualdebug and getattr(layout, 'debug_free_ranges', None):
            draw_debug_free_ranges(dwg, layout.debug_free_ranges, canvas_width)

        elements = layout.elements
        connections = layout.connections
        elements_by_id = {e['id']: e for e in elements}
        containers = [e for e in elements if 'contains' in e]
        normal_elements = [e for e in elements if 'contains' not in e]

        marker_result = setup_arrow_markers(dwg, connections, color_connections)
        if color_connections and isinstance(marker_result, tuple):
            markers, per_conn_styles = marker_result
        else:
            markers = marker_result
            per_conn_styles = None

        # LAF construye etiquetas NdFn desde structure_info cuando visualdebug está activo
        ndfn_labels = self._build_ndfn_labels(layout, elements_by_id) if visualdebug else {}

        # === Orden de dibujo (LAF) ===
        # 1. Container backgrounds (rect, sin icono inline — LAF lo dibuja aparte)
        self._render_containers(dwg, containers, elements_by_id, ndfn_labels)

        # 2. Iconos de elementos no-container
        self._render_icons(dwg, normal_elements, ndfn_labels, embedded_icons=embedded_icons)

        # 2.5. LAF-ONLY: iconos de containers como elementos separados
        self._render_container_icons(dwg, containers, elements_by_id, ndfn_labels, embedded_icons=embedded_icons)

        # 3. Conexiones
        conn_centers = draw_connections(dwg, connections, elements_by_id, markers, per_conn_styles, ndfn_labels)

        # 4. Optimizar y dibujar etiquetas
        label_optimizer = LabelPositionOptimizer(self.geometry, canvas_width, canvas_height, debug=debug)
        labels_to_optimize = self._collect_labels(elements, connections, containers, conn_centers, layout.label_positions)
        optimized_label_positions = label_optimizer.optimize_labels(labels_to_optimize, elements, connections)
        self._render_element_labels(dwg, elements, optimized_label_positions, layout.label_positions, canvas_width, canvas_height)
        draw_connection_labels(dwg, connections, conn_centers, optimized_label_positions)
        self._render_container_labels(dwg, containers, elements_by_id)

        # 5. Debug visual
        if visualdebug:
            self._render_debug_levels(dwg, elements, containers, layout.levels)
        if ndfn_labels:
            self._render_debug_ndfn(dwg, elements, ndfn_labels)

        dwg.save()
        logger.info(f"Diagrama generado exitosamente: {output_svg}")

        if exportpng:
            convert_svg_to_png(output_svg)

    # -------- Métodos privados de orquestación --------

    def _build_ndfn_labels(self, layout, elements_by_id):
        """Construye etiquetas NdFn desde structure_info (LAF las populá en optimize())."""
        ndfn_labels = {}
        si = getattr(layout, 'structure_info', None)
        if si is None:
            return ndfn_labels
        ndpr_map = {eid: nid for eid, nid in si.all_node_ids.items()}
        container_children = {}
        for eid, elem in elements_by_id.items():
            if 'contains' in elem and elem['contains']:
                container_children[eid] = [extract_item_id(item) for item in elem['contains']]
        aaa = 1
        for eid in si.primary_elements:
            nddp = ndpr_map.get(eid, 'NdDp00-000')
            node_type = si.primary_node_types.get(eid, 'Simple')
            is_container = eid in container_children
            is_virtual = node_type == 'Contenedor Virtual'
            ndfn_labels[eid] = f"NdFn.{aaa:03d}.{nddp}.0"
            aaa += 1
            if is_container:
                if not is_virtual:
                    ndfn_labels[f"{eid}__icon"] = f"NdFn.{aaa:03d}.{nddp}.1"
                    aaa += 1
                sub_idx = 2
                for child_id in container_children[eid]:
                    child_nddp = ndpr_map.get(child_id, 'NdDp00-000')
                    ndfn_labels[child_id] = f"NdFn.{aaa:03d}.{child_nddp}.{sub_idx}"
                    aaa += 1
                    sub_idx += 1
        return ndfn_labels

    def _render_containers(self, dwg, containers, elements_by_id, ndfn_labels):
        """Dibuja containers (solo rect, sin icono — LAF dibuja el icono aparte)."""
        for container in containers:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[RECT] {container['id']}: "
                    f"({container.get('x', 0):.1f}, {container.get('y', 0):.1f}) "
                    f"{container.get('width', 0):.1f}x{container.get('height', 0):.1f}"
                )
            draw_target, ndfn_group = ndfn_wrap(dwg, container['id'], ndfn_labels)
            # LAF: explícitamente NO dibujar icono inline (se dibuja después como elemento separado).
            _draw_container(
                draw_target, container, elements_by_id,
                draw_label=False, layout_algorithm='laf', draw_icon=False,
            )
            if ndfn_group is not None:
                dwg.add(ndfn_group)

    def _render_icons(self, dwg, normal_elements, ndfn_labels, embedded_icons=None):
        """Dibuja iconos de todos los elementos no-container."""
        for elem in normal_elements:
            draw_target, ndfn_group = ndfn_wrap(dwg, elem['id'], ndfn_labels)
            _draw_icon_shape(draw_target, elem, embedded_icons=embedded_icons)
            if ndfn_group is not None:
                dwg.add(ndfn_group)

    def _render_container_icons(self, dwg, containers, elements_by_id, ndfn_labels, embedded_icons=None):
        """LAF-only: dibuja iconos de containers como elementos separados."""
        for container in containers:
            container_id = container['id']

            if '_is_container_calculated' in container and all(k in container for k in ['x', 'y']):
                container_x = container['x']
                container_y = container['y']
            else:
                bounds = calculate_container_bounds(container, elements_by_id)
                container_x = bounds['x']
                container_y = bounds['y']

            icon_x = container_x + CONTAINER_PADDING
            icon_y = container_y + CONTAINER_PADDING
            icon_type = container.get('type', 'building')
            color = container.get('color', 'lightgray')

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[ICON] {container_id}: container=({container_x:.1f}, {container_y:.1f}), "
                    f"icon=({icon_x:.1f}, {icon_y:.1f})"
                )

            icon_ndfn_key = f"{container_id}__icon"
            draw_target, ndfn_group = ndfn_wrap(dwg, icon_ndfn_key, ndfn_labels)
            icon_elem_id = f"{container_id}_icon"

            if embedded_icons and icon_type in embedded_icons:
                from AlmaGag.draw.icons import draw_embedded_icon
                draw_embedded_icon(draw_target, icon_x, icon_y, color, icon_elem_id, embedded_icons[icon_type])
            else:
                try:
                    icon_module = importlib.import_module(f'AlmaGag.draw.icons.{icon_type}')
                    draw_func = getattr(icon_module, f'draw_{icon_type}')
                    draw_func(draw_target, icon_x, icon_y, color, icon_elem_id)
                except (ImportError, AttributeError):
                    from AlmaGag.draw.icons import create_gradient
                    gradient_id = create_gradient(draw_target, container_id, color)
                    icon_size = min(ICON_WIDTH, ICON_HEIGHT) * 0.6
                    draw_target.add(draw_target.rect(
                        insert=(icon_x, icon_y),
                        size=(icon_size, icon_size),
                        fill=gradient_id, stroke='black', opacity=1.0,
                    ))

            if ndfn_group is not None:
                dwg.add(ndfn_group)

    def _collect_labels(self, elements, connections, containers, conn_centers, label_positions):
        """Recolecta todas las etiquetas a optimizar."""
        labels_to_optimize = []
        for conn in connections:
            if conn.get('label'):
                key = f"{conn['from']}->{conn['to']}"
                center = conn_centers.get(key)
                if center:
                    labels_to_optimize.append(Label(
                        id=key, text=conn['label'],
                        anchor_x=center[0], anchor_y=center[1],
                        font_size=12, priority=1, category="connection",
                    ))

        contained_element_ids = set()
        for container in containers:
            for item in container.get('contains', []):
                contained_element_ids.add(extract_item_id(item))

        for elem in elements:
            if ('contains' not in elem and elem['id'] not in contained_element_ids
                    and elem.get('label') and 'x' in elem and 'y' in elem):
                elem_id = elem['id']
                elem_width = elem.get('width', ICON_WIDTH)
                elem_height = elem.get('height', ICON_HEIGHT)
                elem_cx = elem['x'] + elem_width / 2
                elem_cy = elem['y'] + elem_height / 2
                if elem_id in label_positions:
                    label_x, label_y, _anchor, _baseline = label_positions[elem_id]
                else:
                    label_x = elem_cx
                    label_y = elem_cy
                labels_to_optimize.append(Label(
                    id=elem_id, text=elem['label'],
                    anchor_x=label_x, anchor_y=label_y,
                    font_size=14, priority=2, category="element",
                    fixed=False, element_center_x=elem_cx, element_center_y=elem_cy,
                ))
        return labels_to_optimize

    def _render_element_labels(self, dwg, elements, optimized_label_positions, label_positions, canvas_width=0, canvas_height=0):
        """Dibuja etiquetas de elementos no-container.

        Si el label excede umbrales (WISH-LAYOUT-003), se renderiza como
        callout box separado con leader line; el icono queda con su label
        canónico (primera línea).
        """
        from AlmaGag.draw.primitives.callout import should_use_callout, get_canonical_label, draw_callout

        for elem in elements:
            if 'contains' not in elem and elem.get('label'):
                full_label = elem['label']
                use_callout = should_use_callout(elem, full_label)
                visible_label = get_canonical_label(full_label) if use_callout else full_label

                optimized_pos = optimized_label_positions.get(elem['id'])
                if optimized_pos:
                    lines = visible_label.split('\n')
                    for i, line in enumerate(lines):
                        dwg.add(dwg.text(
                            line,
                            insert=(optimized_pos.x, optimized_pos.y + (i * 18)),
                            text_anchor=optimized_pos.anchor,
                            font_size="14px", font_family="Arial, sans-serif",
                            fill="black", filter='url(#text-glow)',
                        ))
                else:
                    position_info = label_positions.get(elem['id'])
                    if use_callout:
                        elem_short = dict(elem)
                        elem_short['label'] = visible_label
                        _draw_icon_label(dwg, elem_short, position_info)
                    else:
                        _draw_icon_label(dwg, elem, position_info)

                if use_callout:
                    draw_callout(dwg, elem, full_label, canvas_width, canvas_height)

    def _render_container_labels(self, dwg, containers, elements_by_id):
        """Dibuja etiquetas de contenedores en posición fija."""
        for container in containers:
            if not container.get('label'):
                continue
            if 'x' not in container or 'y' not in container:
                continue
            container_x = container['x']
            container_y = container['y']

            label_local_x = 10 + ICON_WIDTH + 10
            label_local_y = 16
            lines = container['label'].split('\n')

            label_x = container_x + label_local_x
            label_y = container_y + label_local_y
            for i, line in enumerate(lines):
                dwg.add(dwg.text(
                    line,
                    insert=(label_x, label_y + (i * 18)),
                    text_anchor="start", font_size="16px",
                    font_family="Arial, sans-serif", font_weight="bold",
                    fill="black", filter='url(#text-glow)',
                ))

    def _render_debug_levels(self, dwg, elements, containers, levels):
        """Dibuja niveles topológicos para debug visual.

        Textos van ARRIBA del elemento (fuera del bbox) para no solapar
        con íconos/etiquetas/conexiones (fix BUGS-LAYOUT-001).
        """
        contained_ids = set()
        for container in containers:
            for item in container.get('contains', []):
                contained_ids.add(extract_item_id(item))

        primary_elements = []
        for elem in elements:
            if elem['id'] not in contained_ids and 'x' in elem and 'y' in elem:
                primary_elements.append(elem)
        for container in containers:
            if container['id'] not in contained_ids and 'x' in container and 'y' in container:
                primary_elements.append(container)

        for elem in primary_elements:
            elem_id = elem['id']
            elem_x = elem['x']
            elem_y = elem['y']
            elem_width = elem.get('width', ICON_WIDTH)
            elem_height = elem.get('height', ICON_HEIGHT)
            level = levels.get(elem_id, 0)
            box_height = elem_height
            if elem.get('label'):
                lines = elem['label'].split('\n')
                box_height = elem_height + 15 + len(lines) * 18

            dwg.add(dwg.rect(
                insert=(elem_x - 5, elem_y - 5),
                size=(elem_width + 10, box_height + 10),
                fill='none', stroke='red', stroke_width=2,
                stroke_dasharray='5,5', opacity=0.7,
            ))
            dwg.add(dwg.text(
                str(level), insert=(elem_x, elem_y - 8),
                text_anchor="start", font_size="14px",
                font_family="Arial, sans-serif", font_weight="bold", fill="red",
                filter='url(#text-glow)',
            ))

    def _render_debug_ndfn(self, dwg, elements, ndfn_labels):
        """Dibuja anotaciones NdFn arriba de elementos (visualdebug).

        Posicionado por encima del nivel topológico (fix BUGS-LAYOUT-001).
        Stack vertical desde el elemento hacia arriba:
          elem_y - 8  : nivel topológico (14px)
          elem_y - 24 : NdFn (7px)
          elem_y - 33 : NdFn icon (7px)
        """
        for elem in elements:
            eid = elem.get('id', '')
            if 'x' not in elem or 'y' not in elem:
                continue
            x = elem['x']
            y = elem['y']
            ndfn = ndfn_labels.get(eid, '')
            if ndfn:
                dwg.add(dwg.text(
                    ndfn, insert=(x + 2, y - 24),
                    font_size='7px', fill='red',
                    font_family='monospace', font_weight='bold', opacity=0.9,
                    filter='url(#text-glow)',
                ))
            ndfn_icon = ndfn_labels.get(f"{eid}__icon", '')
            if ndfn_icon:
                dwg.add(dwg.text(
                    ndfn_icon, insert=(x + 2, y - 33),
                    font_size='7px', fill='#e85d04',
                    font_family='monospace', font_weight='bold', opacity=0.9,
                    filter='url(#text-glow)',
                ))
