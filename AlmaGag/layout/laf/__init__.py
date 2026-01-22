"""
LAF (Layout Abstracto Primero) - Sistema de layout basado en minimización de cruces

Este paquete implementa un enfoque de layout en 4 fases:
1. Análisis de estructura (árbol de elementos + métricas)
2. Layout abstracto (posicionamiento como puntos para minimizar cruces)
3. Inflación de elementos (asignar dimensiones reales con spacing proporcional)
4. Crecimiento de contenedores (expandir contenedores bottom-up)

Author: José + ALMA
Version: v1.1 (Sprint 3)
Date: 2026-01-17
"""

from AlmaGag.layout.laf.structure_analyzer import StructureAnalyzer, StructureInfo
from AlmaGag.layout.laf.abstract_placer import AbstractPlacer
from AlmaGag.layout.laf.inflator import ElementInflator
from AlmaGag.layout.laf.container_grower import ContainerGrower
from AlmaGag.layout.laf.visualizer import GrowthVisualizer

__version__ = '1.3.0'
__all__ = ['StructureAnalyzer', 'StructureInfo', 'AbstractPlacer', 'ElementInflator', 'ContainerGrower', 'GrowthVisualizer']
