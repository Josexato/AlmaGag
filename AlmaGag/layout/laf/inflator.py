"""
ElementInflator - Conversión de posiciones abstractas a reales

Infla elementos desde grid abstracto (1px) a dimensiones reales con spacing
proporcional basado en ICON_WIDTH.

Author: José + ALMA
Version: v1.0
Date: 2026-01-17
"""

from typing import Dict, Tuple
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT, TOP_MARGIN_DEBUG, TOP_MARGIN_NORMAL
from AlmaGag.layout.laf.structure_analyzer import StructureInfo


class ElementInflator:
    """
    Convierte posiciones abstractas a coordenadas reales con spacing proporcional.
    """

    def __init__(self, label_optimizer=None, debug: bool = False, visualdebug: bool = False):
        """
        Inicializa el inflador.

        Args:
            label_optimizer: LabelOptimizer para calcular posiciones de etiquetas
            debug: Si True, imprime logs de debug
            visualdebug: Si True, usa TOP_MARGIN grande para área de debug badge
        """
        self.label_optimizer = label_optimizer
        self.debug = debug
        self.visualdebug = visualdebug

    def inflate_elements(
        self,
        abstract_positions: Dict[str, Tuple[int, int]],
        structure_info: StructureInfo,
        layout
    ) -> float:
        """
        Asigna posiciones reales (x, y) a elementos.

        Algoritmo:
        1. Calcular spacing base proporcional
        2. Convertir coordenadas abstractas → reales
        3. Asignar dimensiones reales a elementos
        4. Calcular posiciones de etiquetas

        Args:
            abstract_positions: {element_id: (abstract_x, abstract_y)}
            structure_info: Información estructural
            layout: Layout a modificar in-place

        Returns:
            float: Spacing calculado (para debug/logging)
        """
        # Fase 3.1: Calcular spacing proporcional
        spacing = self.calculate_spacing(structure_info)

        if self.debug:
            print(f"[INFLATOR] Spacing calculado: {spacing:.1f}px")
            print(f"           Formula: MAX(20*{ICON_WIDTH}, 3*max_contained*{ICON_WIDTH})")

        # Fase 3.2: Asignar posiciones reales
        self._assign_real_positions(
            abstract_positions,
            spacing,
            layout
        )

        if self.debug:
            print(f"[INFLATOR] Posiciones reales asignadas: {len(abstract_positions)} elementos")

        # Fase 3.3: Calcular posiciones de etiquetas
        if self.label_optimizer:
            self._calculate_label_positions(layout)

            if self.debug:
                print(f"[INFLATOR] Etiquetas calculadas: {len(layout.label_positions)} elementos")

        return spacing

    def calculate_spacing(self, structure_info: StructureInfo) -> float:
        """
        Calcula spacing entre elementos primarios.

        Formula (ajustada para evitar diagramas excesivamente grandes):
            max_contained = max(total_icons for container in containers)
            spacing = MAX(
                3 * ICON_WIDTH,                 # Base: 3 unidades (reducido de 20)
                1.5 * max_contained * ICON_WIDTH  # Scaled: 1.5x contenido máximo (reducido de 3x)
            )

        Args:
            structure_info: Información estructural con container_metrics

        Returns:
            float: Spacing en píxeles
        """
        # Base: 3 unidades de ICON_WIDTH (240px con ICON_WIDTH=80)
        base_spacing = 3 * ICON_WIDTH

        # Scaled: 1.5 veces el contenedor más grande
        if structure_info.container_metrics:
            max_contained = max(
                metrics['total_icons']
                for metrics in structure_info.container_metrics.values()
            )
            scaled_spacing = 1.5 * max_contained * ICON_WIDTH
        else:
            scaled_spacing = 0

        return max(base_spacing, scaled_spacing)

    def _assign_real_positions(
        self,
        abstract_positions: Dict[str, Tuple[int, int]],
        spacing: float,
        layout
    ) -> None:
        """
        Convierte coordenadas abstractas a reales y las asigna al layout.

        Formula:
            real_x = abstract_x * spacing
            real_y = TOP_MARGIN + (abstract_y * spacing * vertical_factor)

        Args:
            abstract_positions: {element_id: (abstract_x, abstract_y)}
            spacing: Spacing calculado
            layout: Layout a modificar in-place
        """
        # Factor vertical (reducido para evitar diagramas excesivamente altos)
        # Original: 1.5, ajustado a 0.5 para diagramas más compactos
        vertical_factor = 0.5

        # TOP_MARGIN - área de debug badge si visualdebug activo
        TOP_MARGIN = TOP_MARGIN_DEBUG if self.visualdebug else TOP_MARGIN_NORMAL

        if self.debug:
            margin_type = "DEBUG (80px)" if self.visualdebug else "NORMAL (20px)"
            print(f"[INFLATOR] TOP_MARGIN: {TOP_MARGIN:.0f}px ({margin_type})")

        for elem_id, (abstract_x, abstract_y) in abstract_positions.items():
            # Convertir a coordenadas reales
            real_x = abstract_x * spacing
            real_y = TOP_MARGIN + (abstract_y * spacing * vertical_factor)

            # Asignar al elemento en layout
            elem = layout.elements_by_id.get(elem_id)
            if elem:
                elem['x'] = real_x
                elem['y'] = real_y

                # Asignar dimensiones reales si aún no las tiene
                if 'width' not in elem or 'height' not in elem:
                    # Elementos normales: ICON_WIDTH x ICON_HEIGHT
                    # Contenedores: Mantener 1x1 hasta Fase 4
                    if 'contains' not in elem:
                        elem['width'] = ICON_WIDTH
                        elem['height'] = ICON_HEIGHT
                    # else: Contenedores se expanden en Fase 4

    def _calculate_label_positions(self, layout) -> None:
        """
        Calcula posiciones iniciales de etiquetas para contenedores.

        IMPORTANTE: NO calcular para elementos primarios, ya que sus posiciones
        se ajustarán durante el centrado horizontal en Fase 4.5 y el
        LabelPositionOptimizer las calculará correctamente después.

        Args:
            layout: Layout con elementos ya posicionados
        """
        if not self.label_optimizer:
            return

        # Solo calcular posiciones para CONTENEDORES
        # Los elementos primarios serán calculados por LabelPositionOptimizer
        # después del centrado horizontal (Fase 4.5)
        for elem in layout.elements:
            if not elem.get('label'):
                continue

            elem_id = elem['id']

            # Solo procesar contenedores con dimensiones ya calculadas
            if 'contains' in elem and 'width' in elem:
                x = elem.get('x', 0)
                y = elem.get('y', 0)
                width = elem.get('width', ICON_WIDTH)

                # Centrada arriba del contenedor
                label_x = x + width / 2
                label_y = y - 5  # 5px arriba del elemento

                layout.label_positions[elem_id] = (
                    label_x,
                    label_y,
                    'middle',
                    'bottom'
                )
