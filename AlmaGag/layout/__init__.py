"""
AlmaGag Layout Module

Este módulo separa las responsabilidades de almacenamiento y optimización de diagramas:

- Layout: Contenedor inmutable del estado del diagrama
- LayoutOptimizer: Interfaz base para optimizadores
- AutoLayoutOptimizer: Implementación del optimizador automático v2.1
- GeometryCalculator: Cálculos geométricos (bounding boxes, intersecciones)
- CollisionDetector: Detección de colisiones entre elementos
- GraphAnalyzer: Análisis de estructura del grafo
"""

from AlmaGag.layout.layout import Layout
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.layout.optimizer_base import LayoutOptimizer
from AlmaGag.layout.auto_optimizer import AutoLayoutOptimizer

__all__ = [
    'Layout',
    'GeometryCalculator',
    'CollisionDetector',
    'GraphAnalyzer',
    'LayoutOptimizer',
    'AutoLayoutOptimizer',
]
