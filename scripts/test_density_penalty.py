#!/usr/bin/env python3
"""
test_density_penalty.py - Prueba iterativa de valores de penalty por densidad

Este script prueba diferentes valores de penalty para la detección de densidad
local en el optimizador de etiquetas, generando diagramas y capturando métricas.

Uso:
    python scripts/test_density_penalty.py
"""

import os
import sys
import shutil
from pathlib import Path

# Agregar AlmaGag al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from AlmaGag.generator import generate_diagram

# Valores de penalty a probar
PENALTY_VALUES = [30, 50, 70, 100, 150, 200]

# Archivo de prueba
TEST_FILE = "examples/05-arquitectura-gag.gag"

def modify_penalty(penalty_value):
    """Modifica el valor de penalty en label_optimizer.py"""
    optimizer_path = Path(__file__).parent.parent / "AlmaGag" / "layout" / "label_optimizer.py"

    with open(optimizer_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Buscar y reemplazar la línea de density_penalty
    import re
    pattern = r'density_penalty = density \* \d+'
    replacement = f'density_penalty = density * {penalty_value}'

    new_content = re.sub(pattern, replacement, content)

    with open(optimizer_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"[OK] Penalty modificado a: {penalty_value}")

def run_test(penalty_value):
    """Ejecuta generación con un valor de penalty específico"""
    print(f"\n{'='*70}")
    print(f"PROBANDO PENALTY = {penalty_value}")
    print(f"{'='*70}\n")

    # Modificar código
    modify_penalty(penalty_value)

    # Generar diagrama (capturar output)
    import io
    from contextlib import redirect_stdout

    output_buffer = io.StringIO()
    try:
        with redirect_stdout(output_buffer):
            generate_diagram(TEST_FILE, debug=False)  # Sin debug para output limpio
    except Exception as e:
        print(f"[ERROR] Error durante generación: {e}")
        return None

    output = output_buffer.getvalue()

    # Extraer métricas
    metrics = {
        'penalty': penalty_value,
        'collisions': 0,
        'high_scores': 0
    }

    for line in output.split('\n'):
        if 'colisiones detectadas' in line:
            try:
                metrics['collisions'] = int(line.split()[3])
            except:
                pass

    # Copiar PNG generado con nombre específico
    source_png = "debug/outputs/05-arquitectura-gag.png"
    dest_png = f"debug/density-tests/penalty-{penalty_value}.png"

    if os.path.exists(source_png):
        shutil.copy2(source_png, dest_png)
        print(f"[OK] PNG guardado: {dest_png}")
        metrics['png_path'] = dest_png
    else:
        print(f"[ERROR] PNG no encontrado: {source_png}")
        metrics['png_path'] = None

    print(f"  Colisiones: {metrics['collisions']}")

    return metrics

def main():
    print("\n" + "="*70)
    print("TEST ITERATIVO DE PENALTY POR DENSIDAD")
    print("="*70)

    # Cambiar al directorio raíz
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Verificar que existe el archivo de prueba
    if not os.path.exists(TEST_FILE):
        print(f"[ERROR] Archivo de prueba no encontrado: {TEST_FILE}")
        sys.exit(1)

    results = []

    # Ejecutar tests
    for penalty in PENALTY_VALUES:
        metrics = run_test(penalty)
        if metrics:
            results.append(metrics)

    # Mostrar resumen
    print("\n" + "="*70)
    print("RESUMEN DE RESULTADOS")
    print("="*70)
    print(f"\n{'Penalty':<10} {'Colisiones':<15} {'PNG'}")
    print("-" * 70)

    for result in results:
        png_status = "[OK]" if result['png_path'] else "[ERROR]"
        print(f"{result['penalty']:<10} {result['collisions']:<15} {png_status}")

    print("\n" + "="*70)
    print(f"[OK] Tests completados: {len(results)}/{len(PENALTY_VALUES)}")
    print(f"[OK] PNGs guardados en: debug/density-tests/")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
