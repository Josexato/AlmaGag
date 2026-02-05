"""
Script para analizar grupos en el diagrama 05-arquitectura-gag.gag
"""

import json
import sys
sys.path.insert(0, 'D:\\10_Dev\\pythondev\\AlmaGag')

from AlmaGag.layout import Layout
from AlmaGag.layout.laf.structure_analyzer import StructureAnalyzer

# Leer el archivo GAG
with open('docs/diagrams/gags/05-arquitectura-gag.gag', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Crear layout
layout = Layout(
    elements=data['elements'],
    connections=data['connections'],
    canvas=data.get('canvas', {'width': 1400, 'height': 1100})
)

# Analizar estructura
analyzer = StructureAnalyzer(debug=False)
structure_info = analyzer.analyze(layout)

print("="*80)
print("ANÁLISIS DE ESTRUCTURA DEL DIAGRAMA")
print("="*80)

print(f"\n1. ELEMENTOS PRIMARIOS: {len(structure_info.primary_elements)}")
print("-" * 80)
for i, elem_id in enumerate(structure_info.primary_elements, 1):
    elem = layout.elements_by_id[elem_id]
    is_container = 'contains' in elem
    print(f"  {i:2d}. {elem_id:30s} {'[CONTENEDOR]' if is_container else ''}")

print(f"\n2. GRAFO DE CONEXIONES (elementos primarios)")
print("-" * 80)
for from_id, to_list in sorted(structure_info.connection_graph.items()):
    if to_list:
        print(f"  {from_id:30s} -> {', '.join(to_list)}")

print(f"\n3. NIVELES TOPOLÓGICOS")
print("-" * 80)
levels_by_level = {}
for elem_id, level in sorted(structure_info.topological_levels.items(), key=lambda x: x[1]):
    if level not in levels_by_level:
        levels_by_level[level] = []
    levels_by_level[level].append(elem_id)

for level, elem_ids in sorted(levels_by_level.items()):
    print(f"  Nivel {level}: {len(elem_ids)} elementos")
    for elem_id in elem_ids:
        print(f"    - {elem_id}")

# Calcular grupos usando el mismo algoritmo del LAFOptimizer
print(f"\n4. ANÁLISIS DE GRUPOS")
print("-" * 80)

# Construir grafo no dirigido
undirected_graph = {}
for node, neighbors in structure_info.connection_graph.items():
    if node not in undirected_graph:
        undirected_graph[node] = []
    for neighbor in neighbors:
        if neighbor not in undirected_graph:
            undirected_graph[neighbor] = []
        if neighbor not in undirected_graph[node]:
            undirected_graph[node].append(neighbor)
        if node not in undirected_graph[neighbor]:
            undirected_graph[neighbor].append(node)

# Asegurar que todos los elementos están en el grafo
for elem in layout.elements:
    elem_id = elem['id']
    if elem_id not in undirected_graph:
        undirected_graph[elem_id] = []

visited = set()
groups = []

def dfs(node, group):
    if node in visited:
        return
    visited.add(node)
    group.append(node)
    for neighbor in undirected_graph.get(node, []):
        dfs(neighbor, group)

# Explorar solo elementos primarios
for elem_id in structure_info.primary_elements:
    if elem_id not in visited:
        group = []
        dfs(elem_id, group)
        if group:
            groups.append(group)

print(f"Total de grupos: {len(groups)}")
print()

for i, group in enumerate(groups, 1):
    print(f"Grupo {i}: {len(group)} elemento(s)")
    for elem_id in sorted(group):
        print(f"  - {elem_id}")
    print()

print("="*80)
print(f"RESUMEN:")
print(f"  - {len(structure_info.primary_elements)} elementos primarios")
print(f"  - {len(groups)} grupos conectados")
print(f"  - {len(structure_info.topological_levels)} niveles topológicos únicos")
print("="*80)
