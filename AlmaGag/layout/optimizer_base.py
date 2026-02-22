"""
LayoutOptimizer - Interfaz base para optimizadores de layout

Esta clase abstracta define el contrato que todos los optimizadores deben cumplir.
Los optimizadores son responsables de:
1. Analizar el grafo y escribir características en el layout
2. Calcular posiciones iniciales de etiquetas
3. Detectar colisiones
4. Crear copias candidatas y optimizar iterativamente
5. Retornar el mejor layout encontrado
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from AlmaGag.layout.layout import Layout

logger = logging.getLogger('AlmaGag')


class LayoutOptimizer(ABC):
    """
    Interfaz base para optimizadores de layout.

    Los optimizadores trabajan sobre copias del layout original,
    aplicando diferentes estrategias para minimizar colisiones.

    Attributes:
        verbose (bool): Si True, imprime información de debug
    """

    def __init__(self, verbose: bool = False):
        """
        Inicializa el optimizador.

        Args:
            verbose: Si True, imprime información de debug durante optimización
        """
        self.verbose = verbose

    @abstractmethod
    def optimize(self, layout: Layout, max_iterations: int = 10) -> Layout:
        """
        Optimiza un layout para minimizar colisiones.

        El optimizador:
        - NO modifica el layout de entrada
        - Crea copias en cada iteración
        - Retorna un NUEVO layout optimizado

        Args:
            layout: Layout inicial (se preserva sin modificar)
            max_iterations: Número máximo de iteraciones

        Returns:
            Layout: Nuevo layout optimizado (mejor encontrado)

        Example:
            >>> optimizer = SomeOptimizer()
            >>> original = Layout(elements=[...], connections=[...], canvas={...})
            >>> optimized = optimizer.optimize(original, max_iterations=5)
            >>> # original no ha sido modificado
            >>> # optimized tiene las mejores posiciones encontradas
        """
        pass

    def analyze(self, layout: Layout) -> None:
        """
        Analiza el grafo y escribe características en el layout.

        Este método modifica el layout in-place, escribiendo:
        - layout.graph: Grafo de adyacencia
        - layout.levels: Niveles verticales
        - layout.groups: Grupos conectados
        - layout.priorities: Prioridades calculadas

        Args:
            layout: Layout a analizar (se modifica in-place)
        """
        pass

    def evaluate(self, layout: Layout) -> int:
        """
        Evalúa un layout y calcula sus colisiones.

        Calcula colisiones y cachea los resultados en:
        - layout._collision_count
        - layout._collision_pairs

        Args:
            layout: Layout a evaluar

        Returns:
            int: Número de colisiones detectadas
        """
        pass

    def _log(self, message: str) -> None:
        """
        Imprime mensaje si verbose está activado.

        Args:
            message: Mensaje a imprimir
        """
        if self.verbose:
            logger.debug(f"[{self.__class__.__name__}] {message}")
