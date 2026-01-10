#!/usr/bin/env python3
"""
run_tests.py - Ejecuta test fixtures de AlmaGag

Este script recorre todos los archivos .gag en tests/fixtures/
y valida que se generen correctamente sin errores.

Uso:
    python scripts/run_tests.py
    python scripts/run_tests.py --verbose  # Modo verbose
"""

import os
import sys
import glob
import argparse
from pathlib import Path

# Agregar AlmaGag al path para poder importar
sys.path.insert(0, str(Path(__file__).parent.parent))

from AlmaGag.generator import generate_diagram


def main():
    parser = argparse.ArgumentParser(
        description="Ejecuta test fixtures de AlmaGag"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Modo verbose (muestra output completo)"
    )
    args = parser.parse_args()

    # Obtener directorio de test fixtures
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    fixtures_dir = project_root / "tests" / "fixtures"

    if not fixtures_dir.exists():
        print(f"[ERROR] No se encontro la carpeta tests/fixtures/ en {fixtures_dir}")
        sys.exit(1)

    # Obtener todos los archivos .gag
    gag_files = sorted(fixtures_dir.glob("*.gag"))

    if not gag_files:
        print("[WARN] No se encontraron archivos .gag en tests/fixtures/")
        sys.exit(0)

    print(f"[TEST] Ejecutando {len(gag_files)} test fixtures\n")
    print("=" * 70)

    # Cambiar al directorio raiz para que debug/outputs/ funcione
    os.chdir(project_root)

    success_count = 0
    error_count = 0
    errors = []

    # Ejecutar cada test fixture
    for i, gag_file in enumerate(gag_files, 1):
        filename = gag_file.name
        test_name = filename.replace(".gag", "")

        if not args.verbose:
            print(f"[{i}/{len(gag_files)}] {test_name}...", end=" ")
        else:
            print(f"\n[{i}/{len(gag_files)}] Testing: {filename}")
            print("-" * 70)

        try:
            # Capturar output si no es verbose
            if not args.verbose:
                # Redirigir stdout temporalmente
                import io
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()

            generate_diagram(str(gag_file))

            if not args.verbose:
                sys.stdout = old_stdout

            success_count += 1
            if not args.verbose:
                print("[PASS]")
            else:
                print(f"[PASS] {filename}")

        except Exception as e:
            if not args.verbose:
                sys.stdout = old_stdout

            error_count += 1
            errors.append({
                'file': filename,
                'error': str(e),
                'type': type(e).__name__
            })

            if not args.verbose:
                print("[FAIL]")
            else:
                print(f"[FAIL] {filename}")
                print(f"    {type(e).__name__}: {e}")

    # Resumen final
    print("\n" + "=" * 70)
    print("\n[RESULTADOS]")
    print(f"   Total:    {len(gag_files)}")
    print(f"   Passed:   {success_count}")
    print(f"   Failed:   {error_count}")

    # Mostrar errores detallados
    if errors:
        print("\n" + "=" * 70)
        print("\n[ERRORES DETALLADOS]\n")
        for i, err in enumerate(errors, 1):
            print(f"{i}. {err['file']}")
            print(f"   Tipo: {err['type']}")
            print(f"   Mensaje: {err['error']}")
            print()

    # Exit code
    if error_count == 0:
        print("\n[OK] Todos los tests pasaron!")
        sys.exit(0)
    else:
        print(f"\n[WARN] {error_count} test(s) fallaron")
        sys.exit(1)


if __name__ == "__main__":
    main()
