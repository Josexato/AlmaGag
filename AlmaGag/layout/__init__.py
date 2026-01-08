"""
AlmaGag Layout Module

Este módulo separa las responsabilidades de almacenamiento y optimización de diagramas:

- Layout: Contenedor inmutable del estado del diagrama
- LayoutOptimizer: Interfaz base para optimizadores
- AutoLayoutOptimizer: Implementación del optimizador automático v2.1
- AutoLayoutPositioner: Auto-layout para coordenadas opcionales (SDJF v2.0)
- SizingCalculator: Cálculos de dimensiones con hp/wp (SDJF v2.0)
- GeometryCalculator: Cálculos geométricos (bounding boxes, intersecciones)
- CollisionDetector: Detección de colisiones entre elementos
- GraphAnalyzer: Análisis de estructura del grafo
"""

from AlmaGag.layout.layout import Layout
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.layout.auto_positioner import AutoLayoutPositioner
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.layout.optimizer_base import LayoutOptimizer
from AlmaGag.layout.auto_optimizer import AutoLayoutOptimizer

__all__ = [
    'Layout',
    'SizingCalculator',
    'AutoLayoutPositioner',
    'GeometryCalculator',
    'CollisionDetector',
    'GraphAnalyzer',
    'LayoutOptimizer',
    'AutoLayoutOptimizer',
]
