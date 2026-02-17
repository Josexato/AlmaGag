#!/usr/bin/env python3
"""
test_pipeline_consistency.py - Tests de consistencia del pipeline

Verifica que:
1. Labels de contenedores aparecen exactamente 1 vez (no duplicados)
2. Labels de contenedores están dentro del header reservado (y >= container.y)
3. El SVG usa solo elementos/conexiones optimizados
"""

import os
import sys
import re
from pathlib import Path

import pytest

# Agregar AlmaGag al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from AlmaGag.generator import generate_diagram


def test_no_duplicate_container_labels():
    """Verifica que cada label de contenedor aparece exactamente 1 vez"""
    test_file = "examples/05-arquitectura-gag.gag"

    if not os.path.exists(test_file):
        pytest.skip(f"{test_file} no encontrado")

    # Generar SVG
    generate_diagram(test_file, debug=False)

    # Leer SVG generado
    svg_file = "05-arquitectura-gag.svg"
    with open(svg_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Labels de contenedores esperados
    container_labels = [
        'Layout Module',
        'Routing Module',
        'Analysis Module',
        'Draw Module'
    ]

    for label in container_labels:
        # Buscar patrón >{label}< (texto dentro de tags SVG)
        pattern = f'>{re.escape(label)}<'
        matches = re.findall(pattern, content)
        count = len(matches)
        assert count == 1, f"'{label}' aparece {count} veces (esperado: 1)"


def test_container_labels_inside_header():
    """Verifica que labels de contenedores están dentro del header reservado"""
    test_file = "examples/05-arquitectura-gag.gag"

    if not os.path.exists(test_file):
        pytest.skip(f"{test_file} no encontrado")

    # Generar SVG
    generate_diagram(test_file, debug=False)

    # Leer SVG generado
    svg_file = "05-arquitectura-gag.svg"
    with open(svg_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extraer rectángulos de contenedores y sus labels
    container_pattern = r'<rect fill="url\(#gradient-(\w+)_container\)" height="([\d.]+)".*?y="([\d.]+)"'
    containers = re.findall(container_pattern, content)

    # Patrón para texto (simplificado)
    text_pattern = r'<text[^>]*insert="\(([\d.]+),\s*([\d.]+)\)"[^>]*>(.*?)</text>'
    texts = re.findall(text_pattern, content)

    # Verificar que labels de contenedores conocidos están dentro de sus bounds
    expected_labels = {
        'layout': 'Layout Module',
        'routing': 'Routing Module',
        'analysis': 'Analysis Module',
        'draw': 'Draw Module'
    }

    for container_id, height, y_str in containers:
        container_y = float(y_str)

        label_key = container_id.replace('_container', '')
        if label_key in expected_labels:
            expected_label = expected_labels[label_key]

            for x_str, y_str, text_content in texts:
                if expected_label in text_content:
                    label_y = float(y_str)
                    assert label_y >= container_y, (
                        f"'{expected_label}' está FUERA del header "
                        f"(label_y={label_y:.1f} < container_y={container_y:.1f})"
                    )
                    break


def main():
    """Ejecuta todos los tests de consistencia"""
    print("="*70)
    print("TESTS DE CONSISTENCIA DEL PIPELINE")
    print("="*70)
    print()

    tests = [
        ("No hay labels duplicados", test_no_duplicate_container_labels),
        ("Labels dentro del header", test_container_labels_inside_header)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n[TEST] {name}")
        print("-"*70)
        try:
            if test_func():
                passed += 1
                print(f"[OK] {name}")
            else:
                failed += 1
                print(f"[FAIL] {name}")
        except Exception as e:
            failed += 1
            print(f"[ERROR] {name}: {e}")

    print("\n" + "="*70)
    print(f"RESULTADOS: {passed} passed, {failed} failed")
    print("="*70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
