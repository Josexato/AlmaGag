"""
AutoSVGRenderer — renderer del algoritmo AUTO.

Encapsula toda la lógica de cómo AUTO transforma un Layout optimizado en un
archivo SVG. Cada algoritmo de layout tiene su propio renderer; este NO sabe
nada sobre LAF ni sus convenciones.

Características específicas de AUTO:
- Containers se dibujan con el icono **inline**, en la esquina superior izquierda
  del rect del container (en oposición a LAF que lo trata como elemento separado).
- No usa `render_container_icons` (eso es exclusivo de LAF).
"""

import logging

from AlmaGag.config import (ICON_WIDTH, ICON_HEIGHT, TEXT_LINE_HEIGHT,
                            FONT_SIZE_NODE)
from AlmaGag.draw.primitives.container import draw_container as _draw_container
from AlmaGag.draw.icons import draw_icon_shape as _draw_icon_shape, draw_icon_label as _draw_icon_label
from AlmaGag.draw.primitives.svg import (
    create_canvas,
    setup_arrow_markers,
    ndfn_wrap,
    draw_connections,
    draw_connection_labels,
)
from AlmaGag.draw.primitives.phase_areas import (
    draw_area_boxes, draw_role_markers, draw_role_legend, draw_area_node_labels,
    draw_lane_strips, draw_matrix_grid)
from AlmaGag.utils import extract_item_id
from AlmaGag.debug import add_debug_badge, draw_grid, draw_guide_lines, draw_debug_free_ranges, convert_svg_to_png

logger = logging.getLogger('AlmaGag')


class AutoSVGRenderer:
    """Renderer SVG específico del algoritmo AUTO."""

    def __init__(self, geometry_calculator):
        """
        Args:
            geometry_calculator: GeometryCalculator (fallback canónico de
                etiquetas). Generalmente el mismo que usa el optimizer.
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
        """Orquesta el rendering completo del layout AUTO al archivo SVG."""
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
        # WISH-LAYOUT-007: per_conn_styles puede venir por color_connections
        # (arcoíris) o por semantic_type/color declarado en el SDJF.
        if isinstance(marker_result, tuple):
            markers, per_conn_styles = marker_result
        else:
            markers = marker_result
            per_conn_styles = None

        # ndfn_labels: AUTO no produce structure_info, así que viene vacío excepto
        # en --visualdebug si el optimizer las populó. Mantenemos dict vacío para
        # compatibilidad con primitivas (que aceptan dict vacío).
        ndfn_labels = self._build_ndfn_labels(layout, elements_by_id) if visualdebug else {}

        # §I27/§I28: cajas de fase (áreas) o franjas de carril (lanes) al fondo,
        # sólo en los modos agrupados de hier.
        areas = getattr(layout, 'areas', None)
        lanes = getattr(layout, 'lanes', None)
        matrix = getattr(layout, 'matrix', None)
        roles = getattr(layout, 'roles', None)
        grouped = bool(areas or lanes or matrix)
        if areas:
            draw_area_boxes(dwg, areas)
        if lanes:
            draw_lane_strips(dwg, lanes)
        if matrix:
            draw_matrix_grid(dwg, matrix)

        # §N46: cajas de zona `near` (fondo, detrás de todo lo demás).
        from AlmaGag.draw.primitives.phase_areas import draw_near_zones
        draw_near_zones(dwg, normal_elements)

        # === Orden de dibujo ===
        # 1. Containers (rect de fondo, icono va inline)
        self._render_containers(dwg, containers, elements_by_id, ndfn_labels)

        # WISH-DRAW-002: flujos resaltados — capa de anotación sobre los
        # fondos y BAJO iconos/líneas/textos (el trazo sigue los
        # computed_path ya calculados; no toca layout ni métricas).
        from AlmaGag.draw.primitives.journeys import draw_journeys
        _journeys = getattr(layout, '_journeys', None)
        draw_journeys(dwg, _journeys, elements_by_id, connections)

        # 2. Iconos de elementos normales
        self._render_icons(dwg, normal_elements, ndfn_labels, embedded_icons=embedded_icons)

        # §I30: franja de color por rol sobre cada icono.
        if areas:
            draw_role_markers(dwg, normal_elements, roles)

        # 3. Conexiones
        conn_centers = draw_connections(dwg, connections, elements_by_id, markers, per_conn_styles, ndfn_labels)

        # 4. Dibujar etiquetas — WISH-LAYOUT-008: el renderer dibuja LA VERDAD
        # del layout (label_positions / connection_labels, ya optimizadas por
        # la única pasada global §P61 en la etapa de layout). Aquí no se
        # re-optimiza nada: lo dibujado ES lo medido.
        # §I27/§I28: en modos agrupados las etiquetas de nodo van centradas
        # bajo el icono (placement propio de la vista).
        if grouped:
            draw_area_node_labels(dwg, normal_elements)
        else:
            self._render_element_labels(dwg, elements, layout.label_positions, canvas_width, canvas_height)
        draw_connection_labels(dwg, connections, conn_centers,
                               stored_centers=layout.connection_labels)
        self._render_container_labels(dwg, containers, elements_by_id)

        # §I30: leyenda de responsables (sólo roles usados).
        role_legend_drawn = False
        if areas and roles:
            used = {e.get('role') for e in normal_elements if e.get('role')}
            draw_role_legend(dwg, roles, used, canvas_width, canvas_height)
            role_legend_drawn = True

        # §N48: leyenda de tipos de conexión (≥3 semantic_type distintos). Si la
        # leyenda de roles ya ocupa la franja inferior, ésta sube una línea.
        from AlmaGag.draw.primitives.svg import draw_connection_type_legend
        draw_connection_type_legend(dwg, connections, canvas_width, canvas_height,
                                    y_offset=24 if role_legend_drawn else 0)

        # WISH-DRAW-002: leyenda «Recorridos:» apilada sobre las otras franjas
        _n_legends = (1 if role_legend_drawn else 0) + \
            (1 if len({c.get('semantic_type') for c in connections
                       if c.get('semantic_type')}) >= 3 else 0)
        if _journeys:
            from AlmaGag.draw.primitives.journeys import draw_journey_legend
            if draw_journey_legend(dwg, _journeys, canvas_width, canvas_height,
                                y_offset=24 * _n_legends):
                _n_legends += 1

        # WISH-DRAW-004 (V82): leyenda LIBRE del autor (canvas.legend[]),
        # apilada sobre las demás franjas.
        _canvas_legend = (getattr(layout, 'canvas', None) or {}).get('legend')
        if _canvas_legend:
            from AlmaGag.draw.primitives.svg import draw_canvas_legend
            draw_canvas_legend(dwg, _canvas_legend, canvas_width,
                               canvas_height, y_offset=24 * _n_legends)

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
        """Construye etiquetas NdFn para visualdebug. AUTO no las usa típicamente."""
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
        """Dibuja los contenedores (rect de fondo). El icono se dibuja inline por draw_container."""
        for container in containers:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[RECT] {container['id']}: "
                    f"({container.get('x', 0):.1f}, {container.get('y', 0):.1f}) "
                    f"{container.get('width', 0):.1f}x{container.get('height', 0):.1f}"
                )
            draw_target, ndfn_group = ndfn_wrap(dwg, container['id'], ndfn_labels)
            # AUTO: icon inline en la esquina del container (el label va a su
            # derecha, ya con espacio reservado). Las bands lo ubican tras el
            # título rotado.
            _draw_container(
                draw_target, container, elements_by_id,
                draw_label=False, layout_algorithm='auto', draw_icon=True,
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

    def _render_element_labels(self, dwg, elements, label_positions, canvas_width=0, canvas_height=0):
        """Dibuja etiquetas de elementos no-container desde `label_positions`
        TAL CUAL (WISH-LAYOUT-008: la verdad vive en el layout; la única
        optimización es la pasada global §P61, que ya corrió).

        Fallback canónico sólo para fotos intermedias (Epifanía) donde la
        siembra aún no ocurrió. Si el label excede umbrales (WISH-LAYOUT-003),
        se renderiza como callout box separado con leader line; el icono queda
        con su label canónico (primera línea).
        """
        from AlmaGag.draw.primitives.callout import should_use_callout, get_canonical_label, draw_callout

        for elem in elements:
            if 'contains' not in elem and elem.get('label'):
                full_label = elem['label']
                use_callout = should_use_callout(elem, full_label)
                visible_label = get_canonical_label(full_label) if use_callout else full_label

                position_info = label_positions.get(elem['id'])
                if position_info is None and 'x' in elem and 'y' in elem:
                    num_lines = len(visible_label.split('\n'))
                    position_info = self.geometry.get_text_coords(
                        elem, elem.get('label_position', 'bottom'), num_lines)
                if use_callout:
                    elem_short = dict(elem)
                    elem_short['label'] = visible_label
                    _draw_icon_label(dwg, elem_short, position_info)
                    draw_callout(dwg, elem, full_label, canvas_width, canvas_height)
                else:
                    _draw_icon_label(dwg, elem, position_info)

    def _render_container_labels(self, dwg, containers, elements_by_id):
        """Dibuja etiquetas de contenedores en posición fija (no optimizadas)."""
        for container in containers:
            if not container.get('label'):
                continue
            if 'x' not in container or 'y' not in container:
                continue
            container_x = container['x']
            container_y = container['y']
            lines = container['label'].split('\n')

            # WISH-LAYOUT-005: band → título lateral rotado, centrado vertical.
            if container.get('shape') == 'band':
                cx = container_x + 18
                cy = container_y + container['height'] / 2
                for i, line in enumerate(lines):
                    line_x = cx + (i * 18)
                    dwg.add(dwg.text(
                        line,
                        insert=(line_x, cy),
                        text_anchor="middle", font_size=f"{FONT_SIZE_NODE}px",
                        font_family="Arial, sans-serif", font_weight="bold",
                        fill="black", filter='url(#text-glow)',
                        transform=f"rotate(-90 {line_x} {cy})",
                    ))
                continue

            # T73: un área no lleva icono — su rótulo arranca en el padding,
            # sin reservar el hueco del icono inexistente.
            if container.get('type') == 'area':
                label_local_x = 10
            else:
                label_local_x = 10 + ICON_WIDTH + 10
            label_local_y = 16
            label_x = container_x + label_local_x
            label_y = container_y + label_local_y
            for i, line in enumerate(lines):
                dwg.add(dwg.text(
                    line,
                    insert=(label_x, label_y + (i * 18)),
                    text_anchor="start", font_size=f"{FONT_SIZE_NODE}px",
                    font_family="Arial, sans-serif", font_weight="bold",
                    fill="black", filter='url(#text-glow)',
                ))

    def _render_debug_levels(self, dwg, elements, containers, levels):
        """Dibuja niveles topológicos de elementos primarios (visualdebug).

        Los textos van ARRIBA del elemento (fuera del bbox) para no solapar
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
