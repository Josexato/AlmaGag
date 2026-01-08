"""
SizingCalculator - Cálculo de dimensiones con hp/wp

Este módulo calcula dimensiones de elementos considerando proporciones
de altura y anchura (hp/wp), proporcionando soporte para sizing flexible.
"""

from typing import Tuple
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


class SizingCalculator:
    """
    Calcula dimensiones de elementos considerando hp/wp.

    Prioridad de resolución:
    1. width/height explícitos (contenedores)
    2. hp/wp multipliers
    3. ICON_WIDTH/ICON_HEIGHT (defaults)
    """

    def get_element_size(self, element: dict) -> Tuple[float, float]:
        """
        Retorna (width, height) final del elemento.

        Args:
            element: Diccionario con 'hp', 'wp', 'width', 'height' opcionales

        Returns:
            (width, height): Dimensiones finales

        Examples:
            {'hp': 2.0} → (80, 100)  # ICON_WIDTH=80, ICON_HEIGHT=50*2.0
            {'wp': 1.5, 'hp': 1.5} → (120, 75)
            {'width': 200} → (200, 50)  # Explícito tiene precedencia
        """
        # Contenedores: usar width/height explícitos
        if 'width' in element and 'height' in element:
            return (element['width'], element['height'])

        # Sizing proporcional
        hp = element.get('hp', 1.0)
        wp = element.get('wp', 1.0)

        width = element.get('width', ICON_WIDTH * wp)
        height = element.get('height', ICON_HEIGHT * hp)

        return (width, height)

    def get_element_weight(self, element: dict) -> float:
        """
        Calcula peso para optimización de colisiones.

        Elementos más grandes son más difíciles de mover.

        Args:
            element: Diccionario con hp/wp opcionales

        Returns:
            float: Factor de peso (min: 1.0, típico: 1.0-4.0)

        Examples:
            {'hp': 2.0, 'wp': 2.0} → 4.0  # Área = 4x
            {'hp': 1.0, 'wp': 1.0} → 1.0  # Tamaño default
        """
        hp = element.get('hp', 1.0)
        wp = element.get('wp', 1.0)
        return hp * wp  # Peso proporcional al área

    def get_centrality_score(self, element: dict, priority: int) -> float:
        """
        Calcula score de centralidad para auto-layout.

        Combina prioridad de conexiones con tamaño del elemento.

        Args:
            element: Diccionario con hp/wp opcionales
            priority: 0=HIGH, 1=NORMAL, 2=LOW

        Returns:
            float: Score de centralidad (mayor = más central)

        Examples:
            HIGH + hp=2.0 → 6.0  # (3-0) * 2.0 * 1.0
            NORMAL + wp=2.0 → 4.0  # (3-1) * 1.0 * 2.0
            LOW + hp=wp=1.0 → 1.0  # (3-2) * 1.0 * 1.0
        """
        hp = element.get('hp', 1.0)
        wp = element.get('wp', 1.0)
        priority_weight = 3 - priority  # HIGH=3, NORMAL=2, LOW=1
        return priority_weight * hp * wp
