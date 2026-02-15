"""
Script para verificar cómo se están formando los 13 grupos
"""

import json
import sys
sys.path.insert(0, 'D:\\10_Dev\\pythondev\\AlmaGag')

from AlmaGag.layout import Layout
from AlmaGag.layout.laf_optimizer import LAFOptimizer
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.auto_positioner import AutoLayoutPositioner
from AlmaGag.layout.container_calculator import ContainerCalculator
from AlmaGag.routing.router_manager import ConnectionRouterManager
from AlmaGag.layout.label_optimizer import LabelPositionOptimizer
from AlmaGag.layout.graph_analysis import GraphAnalyzer

# Leer el archivo GAG
with open('docs/diagrams/gags/05-arquitectura-gag.gag', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Crear layout
layout = Layout(
    elements=data['elements'],
    connections=data['connections'],
    canvas=data.get('canvas', {'width': 1400, 'height': 1100})
)

# Crear componentes necesarios para LAF
sizing = SizingCalculator()
geometry = GeometryCalculator(sizing)
collision_detector = CollisionDetector(geometry)
graph_analyzer = GraphAnalyzer()
positioner = AutoLayoutPositioner(sizing, graph_analyzer, visualdebug=False)
container_calculator = ContainerCalculator(sizing, geometry)
router_manager = ConnectionRouterManager()
label_optimizer = LabelPositionOptimizer(geometry, 1400, 1100, debug=False)

optimizer = LAFOptimizer(
    positioner=positioner,
    container_calculator=container_calculator,
    router_manager=router_manager,
    collision_detector=collision_detector,
    label_optimizer=label_optimizer,
    geometry=geometry,
    visualize_growth=False,
    debug=False
)

# Ejecutar solo la parte de análisis
from AlmaGag.layout.laf.structure_analyzer import StructureAnalyzer
analyzer = StructureAnalyzer(debug=False)
structure_info = analyzer.analyze(layout)

# Poblar análisis
optimizer._populate_layout_analysis(layout, structure_info)

print("="*80)
print("ANÁLISIS DE GRUPOS ACTUAL")
print("="*80)

print(f"\nTotal de grupos: {len(layout.groups)}")
print(f"Total de elementos: {len(layout.elements)}")
print(f"Elementos primarios: {len(structure_info.primary_elements)}")

for i, group in enumerate(layout.groups, 1):
    print(f"\nGrupo {i}: {len(group)} elemento(s)")
    for elem_id in sorted(group):
        elem = layout.elements_by_id.get(elem_id)
        is_container = 'contains' in elem if elem else False
        is_primary = elem_id in structure_info.primary_elements

        status = []
        if is_container:
            status.append("CONTENEDOR")
        if is_primary:
            status.append("PRIMARIO")
        else:
            status.append("CONTENIDO")

        print(f"  - {elem_id:30s} [{', '.join(status)}]")

print("\n" + "="*80)
