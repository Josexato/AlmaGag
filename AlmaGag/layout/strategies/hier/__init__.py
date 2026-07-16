"""
Algoritmo de layout jerárquico `hier` (WISH-LAF-002).

Implementación directa y plana de los criterios A1–F18 de la spec
"Criterios AlmaGag" (Claude Design), sin la abstracción de contenedores
virtuales de LAF. Caso de regresión: `14-stresstest.sdjf`.

Pipeline (por fases):
- §A leveling.py   — niveles min-parent + satélites + tomas
- §B columns.py    — ghosts, barycenter, carriles, alineación, bifurcación, tallo
- §C/§D routing    — puertos por proyección + ruteo (Fase 2)
- §E/§F arcs/labels — arcos de ciclo + etiquetas (Fase 3)
"""

from AlmaGag.layout.strategies.hier.optimizer import HierLayoutOptimizer

__all__ = ['HierLayoutOptimizer']
