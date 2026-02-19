#!/usr/bin/env python3
"""
generate_examples.py - Regenera todos los ejemplos de AlmaGag

Este script recorre todos los archivos .gag en la carpeta examples/
y genera sus correspondientes SVG.

Uso:
    python scripts/generate_examples.py
    python scripts/generate_examples.py --clean  # Elimina SVG antes de generar
"""

import os
import sys
import glob
import argparse
from pathlib import Path

# Agregar AlmaGag al path para poder importar
sys.path.insert(0, str(Path(__file__).parent.parent))

from AlmaGag.generator import generate_diagram


def clean_svgs(examples_dir):
    """Elimina todos los SVG en el directorio de ejemplos."""
    svg_files = glob.glob(os.path.join(examples_dir, "*.svg"))
    for svg_file in svg_files:
        try:
            os.remove(svg_file)
            print(f"[CLEAN] Eliminado: {os.path.basename(svg_file)}")
        except Exception as e:
            print(f"[ERROR] No se pudo eliminar {svg_file}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Genera todos los ejemplos de AlmaGag"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Elimina SVG existentes antes de generar"
    )
    args = parser.parse_args()

    # Obtener directorio de ejemplos
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    examples_dir = project_root / "examples"

    if not examples_dir.exists():
        print(f"[ERROR] No se encontró la carpeta examples/ en {examples_dir}")
        sys.exit(1)

    # Limpiar SVG si se solicitó
    if args.clean:
        print("\n[CLEAN] Limpiando SVG existentes...")
        clean_svgs(examples_dir)
        print()

    # Obtener todos los archivos .sdjf y .gag
    gag_files = sorted(list(examples_dir.glob("*.sdjf")) + list(examples_dir.glob("*.gag")))

    if not gag_files:
        print("[WARN] No se encontraron archivos .sdjf/.gag en examples/")
        sys.exit(0)

    print(f"[INFO] Encontrados {len(gag_files)} archivos\n")
    print("=" * 70)

    # Cambiar al directorio raíz para que debug/outputs/ funcione
    os.chdir(project_root)

    success_count = 0
    error_count = 0

    # Generar cada ejemplo
    for i, gag_file in enumerate(gag_files, 1):
        filename = gag_file.name
        print(f"\n[{i}/{len(gag_files)}] Generando: {filename}")
        print("-" * 70)

        try:
            generate_diagram(str(gag_file))
            success_count += 1
            print(f"[OK] Exito: {filename}")
        except Exception as e:
            error_count += 1
            print(f"[ERROR] Error: {filename}")
            print(f"    {type(e).__name__}: {e}")

    # Resumen final
    print("\n" + "=" * 70)
    print("\n[RESUMEN]")
    print(f"   Exitosos: {success_count}/{len(gag_files)}")
    print(f"   Errores:  {error_count}/{len(gag_files)}")

    if error_count == 0:
        print("\n[OK] Todos los ejemplos generados exitosamente!")
        sys.exit(0)
    else:
        print(f"\n[WARN] {error_count} ejemplo(s) fallaron")
        sys.exit(1)


if __name__ == "__main__":
    main()
