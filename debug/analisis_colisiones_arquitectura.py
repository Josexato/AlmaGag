#!/usr/bin/env python
"""
Análisis comprehensivo de colisiones en 05-arquitectura-gag.svg

Este script analiza el dump de iteraciones para identificar:
1. Colisiones entre elementos contenedores y sus hijos (esperadas)
2. Colisiones entre elementos libres redistribuidos (PROBLEMA)
3. Colisiones con etiquetas
4. Evolución de colisiones a través de iteraciones

Autor: José + Claude
Fecha: 2026-01-16
"""

import json
import sys
from typing import List, Tuple, Dict

def load_iteration_dump(filepath: str) -> dict:
    """Carga el dump de iteraciones."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_bbox_overlap(
    x1: float, y1: float, w1: float, h1: float,
    x2: float, y2: float, w2: float, h2: float
) -> Tuple[bool, float, float]:
    """
    Verifica si dos bounding boxes se solapan.

    Returns:
        (overlaps, overlap_x, overlap_y)
    """
    # No hay overlap si uno está completamente a un lado del otro
    if x1 + w1 <= x2 or x2 + w2 <= x1:
        return False, 0, 0
    if y1 + h1 <= y2 or y2 + h2 <= y1:
        return False, 0, 0

    # Calcular área de solapamiento
    overlap_x = min(x1 + w1, x2 + w2) - max(x1, x2)
    overlap_y = min(y1 + h1, y2 + h2) - max(y1, y2)

    return True, overlap_x, overlap_y

def analyze_element_collisions(elements: List[dict]) -> List[Dict]:
    """
    Analiza colisiones entre elementos.

    Returns:
        Lista de diccionarios con información de cada colisión
    """
    collisions = []

    for i, elem1 in enumerate(elements):
        x1, y1 = elem1['x'], elem1['y']
        w1 = elem1.get('width') or 80
        h1 = elem1.get('height') or 50

        for elem2 in elements[i+1:]:
            x2, y2 = elem2['x'], elem2['y']
            w2 = elem2.get('width') or 80
            h2 = elem2.get('height') or 50

            overlaps, ox, oy = check_bbox_overlap(x1, y1, w1, h1, x2, y2, w2, h2)

            if overlaps:
                collision_info = {
                    'elem1': elem1['id'],
                    'elem2': elem2['id'],
                    'elem1_pos': (x1, y1, w1, h1),
                    'elem2_pos': (x2, y2, w2, h2),
                    'overlap': (ox, oy),
                    'overlap_area': ox * oy,
                    'is_container_child': False
                }

                # Verificar si es una relación contenedor-hijo
                # (esto NO debería contar como colisión real)
                if (elem1.get('width') and elem1.get('height') and
                    elem1.get('width') > 150):  # Probablemente es contenedor
                    # Verificar si elem2 está completamente dentro de elem1
                    if (x2 >= x1 and y2 >= y1 and
                        x2 + w2 <= x1 + w1 and y2 + h2 <= y1 + h1):
                        collision_info['is_container_child'] = True

                if (elem2.get('width') and elem2.get('height') and
                    elem2.get('width') > 150):  # Probablemente es contenedor
                    # Verificar si elem1 está completamente dentro de elem2
                    if (x1 >= x2 and y1 >= y2 and
                        x1 + w1 <= x2 + w2 and y1 + h1 <= y2 + h2):
                        collision_info['is_container_child'] = True

                collisions.append(collision_info)

    return collisions

def categorize_collisions(collisions: List[Dict]) -> Dict:
    """Categoriza las colisiones por tipo."""
    categories = {
        'container_children': [],  # Contenedor con hijos (esperado)
        'same_y_overlap': [],      # Elementos en mismo Y con overlap
        'full_overlap': [],        # Solapamiento total
        'partial_overlap': []      # Solapamiento parcial
    }

    for col in collisions:
        if col['is_container_child']:
            categories['container_children'].append(col)
        else:
            # Verificar si están en aproximadamente la misma Y
            y1 = col['elem1_pos'][1]
            y2 = col['elem2_pos'][1]

            ox, oy = col['overlap']
            w1, h1 = col['elem1_pos'][2], col['elem1_pos'][3]
            w2, h2 = col['elem2_pos'][2], col['elem2_pos'][3]

            # Solapamiento total = ambos elementos tienen misma posición
            if ox >= min(w1, w2) * 0.99 and oy >= min(h1, h2) * 0.99:
                categories['full_overlap'].append(col)
            elif abs(y1 - y2) < 5:  # Mismo Y (± 5px)
                categories['same_y_overlap'].append(col)
            else:
                categories['partial_overlap'].append(col)

    return categories

def print_collision_report(data: dict):
    """Imprime reporte comprehensivo de colisiones."""
    print("=" * 80)
    print("ANÁLISIS DE COLISIONES: 05-arquitectura-gag.svg")
    print("=" * 80)
    print(f"Archivo: {data['metadata']['input_file']}")
    print(f"Colisiones iniciales: {data['metadata']['initial_collisions']}")
    print(f"Colisiones finales: {data['metadata']['final_collisions']}")
    print(f"Reducción: {data['metadata']['initial_collisions'] - data['metadata']['final_collisions']} colisiones")
    print(f"Canvas: {data['metadata']['canvas_initial']['width']}x{data['metadata']['canvas_initial']['height']}")
    print()

    # Analizar estado inicial
    initial_state = data['iterations'][0]['state']
    elements = initial_state['elements']

    print("=" * 80)
    print("POSICIONES DE ELEMENTOS")
    print("=" * 80)

    # Agrupar por Y
    by_y = {}
    for elem in elements:
        y = round(elem['y'], 1)
        if y not in by_y:
            by_y[y] = []
        by_y[y].append(elem)

    for y in sorted(by_y.keys()):
        elems = by_y[y]
        print(f"\nY = {y:.1f} ({len(elems)} elementos):")
        for elem in sorted(elems, key=lambda e: e['x']):
            w = elem.get('width') or 80
            h = elem.get('height') or 50
            print(f"  X={elem['x']:7.1f}: {elem['id']:<25} size={w:.0f}x{h:.0f}")

    print()
    print("=" * 80)
    print("ANÁLISIS DE COLISIONES ENTRE ICONOS")
    print("=" * 80)

    collisions = analyze_element_collisions(elements)
    categories = categorize_collisions(collisions)

    print(f"\nTotal colisiones detectadas: {len(collisions)}")
    print(f"  - Contenedor-hijo (esperadas): {len(categories['container_children'])}")
    print(f"  - Solapamiento total: {len(categories['full_overlap'])}")
    print(f"  - Mismo Y con overlap: {len(categories['same_y_overlap'])}")
    print(f"  - Solapamiento parcial: {len(categories['partial_overlap'])}")

    # Detalles de colisiones reales (no contenedor-hijo)
    real_collisions = len(collisions) - len(categories['container_children'])
    print(f"\nCOLISIONES REALES (excluyendo contenedor-hijo): {real_collisions}")

    if categories['full_overlap']:
        print(f"\n{'-' * 80}")
        print("SOLAPAMIENTO TOTAL (elementos en misma posicion):")
        print(f"{'-' * 80}")
        for col in categories['full_overlap']:
            x1, y1, w1, h1 = col['elem1_pos']
            x2, y2, w2, h2 = col['elem2_pos']
            print(f"  {col['elem1']:<20} ({x1:.1f}, {y1:.1f})")
            print(f"  {col['elem2']:<20} ({x2:.1f}, {y2:.1f})")
            print(f"  -> Overlap: {col['overlap'][0]:.1f}x{col['overlap'][1]:.1f}px (100% solapamiento)")
            print()

    if categories['same_y_overlap']:
        print(f"\n{'-' * 80}")
        print("ELEMENTOS EN MISMO Y CON OVERLAP:")
        print(f"{'-' * 80}")
        for col in categories['same_y_overlap']:
            x1, y1, w1, h1 = col['elem1_pos']
            x2, y2, w2, h2 = col['elem2_pos']
            ox, oy = col['overlap']
            print(f"  {col['elem1']:<20} ({x1:.1f}, {y1:.1f}) size {w1:.0f}x{h1:.0f}")
            print(f"  {col['elem2']:<20} ({x2:.1f}, {y2:.1f}) size {w2:.0f}x{h2:.0f}")
            print(f"  -> Overlap: {ox:.1f}x{oy:.1f}px")
            spacing = x2 - (x1 + w1)
            print(f"  -> Spacing: {spacing:.1f}px (debería ser >= 0)")
            print()

    if categories['partial_overlap']:
        print(f"\n{'-' * 80}")
        print("SOLAPAMIENTOS PARCIALES:")
        print(f"{'-' * 80}")
        for col in categories['partial_overlap'][:10]:  # Mostrar primeros 10
            x1, y1, w1, h1 = col['elem1_pos']
            x2, y2, w2, h2 = col['elem2_pos']
            ox, oy = col['overlap']
            print(f"  {col['elem1']:<20} ({x1:.1f}, {y1:.1f}) size {w1:.0f}x{h1:.0f}")
            print(f"  {col['elem2']:<20} ({x2:.1f}, {y2:.1f}) size {w2:.0f}x{h2:.0f}")
            print(f"  -> Overlap: {ox:.1f}x{oy:.1f}px")
            print()

    print()
    print("=" * 80)
    print("DIAGNÓSTICO DEL PROBLEMA")
    print("=" * 80)

    # Diagnosticar problema de redistribución
    y_719_elements = [e for e in elements if abs(e['y'] - 719.5) < 1]
    if len(y_719_elements) > 4:
        print("\nWARNING  PROBLEMA DETECTADO: Redistribución a una sola franja")
        print(f"    {len(y_719_elements)} elementos redistribuidos a Y=719.5")
        print("    Causa: Solo hay 1 franja libre disponible, pero múltiples niveles")
        print("    Solución: Dividir la franja libre en sub-franjas verticales")
        print()
        print("    Elementos afectados:")
        for elem in sorted(y_719_elements, key=lambda e: e['x']):
            print(f"      - {elem['id']:<20} X={elem['x']:.1f}")

    # Verificar colisiones de contenedor-hijo
    if categories['container_children']:
        print(f"\nOK Colisiones contenedor-hijo detectadas: {len(categories['container_children'])}")
        print("  Estas son esperadas y NO deberían contarse en el total de colisiones")
        print("  Posible BUG: El detector de colisiones cuenta estas colisiones incorrectamente")

    print()
    print("=" * 80)
    print("RECOMENDACIONES")
    print("=" * 80)
    print()
    print("1. Modificar _position_free_elements_by_topology() para dividir")
    print("   franjas libres en sub-franjas cuando hay múltiples niveles")
    print()
    print("2. Excluir colisiones contenedor-hijo del conteo total")
    print()
    print("3. Considerar expandir canvas verticalmente cuando se detectan")
    print("   múltiples niveles en redistribución")
    print()

if __name__ == '__main__':
    # Buscar el dump más reciente
    import os
    import glob

    dumps = glob.glob('debug/iterations/05-arquitectura-gag_iterations_*.json')
    if not dumps:
        print("ERROR: No se encontró dump de iteraciones")
        print("Ejecuta: python -m AlmaGag.main docs/diagrams/gags/05-arquitectura-gag.gag --dump-iterations")
        sys.exit(1)

    latest_dump = max(dumps, key=os.path.getctime)
    print(f"Analizando: {latest_dump}\n")

    data = load_iteration_dump(latest_dump)
    print_collision_report(data)
