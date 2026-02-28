"""
LAF (Layout Abstracto Primero) - Sistema de layout basado en minimización de cruces

Este paquete implementa un enfoque de layout en 10 fases:
1. Análisis de estructura (árbol de elementos + métricas)
2. Análisis topológico
3. Ordenamiento por centralidad
4. Layout abstracto (posicionamiento como puntos para minimizar cruces)
5. Optimización de posiciones (Claude-SolFase5) - minimiza distancia de conectores
6. Expansión NdPr (NdPr → elementos individuales)
7. Inflación + Crecimiento de contenedores (dimensiones reales, bottom-up)
8. Redistribución vertical
9. Routing
10. Generación de SVG

Author: José + ALMA + Claude (Claude-SolFase5)
Version: v1.6 (Sprint 11 - renumeración 10 fases)
Date: 2026-02-27
"""

from AlmaGag.layout.laf.structure_analyzer import StructureAnalyzer, StructureInfo
from AlmaGag.layout.laf.abstract_placer import AbstractPlacer
from AlmaGag.layout.laf.position_optimizer import PositionOptimizer
from AlmaGag.layout.laf.inflator import ElementInflator
from AlmaGag.layout.laf.container_grower import ContainerGrower
from AlmaGag.layout.laf.visualizer import GrowthVisualizer

__version__ = '1.6.0'
__all__ = [
    'StructureAnalyzer', 'StructureInfo', 'AbstractPlacer',
    'PositionOptimizer', 'ElementInflator', 'ContainerGrower',
    'GrowthVisualizer'
]
