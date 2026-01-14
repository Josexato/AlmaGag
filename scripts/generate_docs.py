#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para regenerar toda la documentación en SVG desde archivos .gag

Uso:
    python scripts/generate_docs.py [--verbose]

El script:
1. Busca todos los .gag en docs/diagrams/gags/
2. Genera cada uno con AlmaGag
3. Mueve los SVG resultantes a docs/diagrams/svgs/
4. Muestra un reporte de lo generado
"""

import os
import sys
import subprocess
import glob
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Colores para output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}[OK]{Colors.END} {text}")

def print_error(text):
    print(f"{Colors.RED}[ERROR]{Colors.END} {text}")

def print_info(text):
    print(f"{Colors.YELLOW}[INFO]{Colors.END} {text}")

def generate_svg(gag_file, verbose=False):
    """
    Genera SVG desde un archivo .gag usando AlmaGag

    Args:
        gag_file: Ruta al archivo .gag
        verbose: Si es True, muestra output detallado

    Returns:
        True si la generación fue exitosa, False en caso contrario
    """
    try:
        cmd = ["python", "-m", "AlmaGag.main", str(gag_file)]

        if verbose:
            print(f"    Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, text=True)
        else:
            result = subprocess.run(cmd, check=True, text=True,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)

        return True

    except subprocess.CalledProcessError as e:
        print_error(f"Error generando {gag_file.name}")
        if verbose:
            print(f"    Código de salida: {e.returncode}")
        return False
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        return False

def move_svg_to_docs(svg_name, target_dir):
    """
    Mueve un SVG generado al directorio de documentación

    Args:
        svg_name: Nombre del archivo SVG
        target_dir: Directorio destino

    Returns:
        True si el movimiento fue exitoso, False en caso contrario
    """
    # Buscar el SVG en el directorio actual
    source = Path(svg_name)

    if not source.exists():
        print_error(f"SVG no encontrado: {svg_name}")
        return False

    # Mover al directorio de documentación
    target = target_dir / svg_name

    try:
        # Usar replace() en lugar de rename() para sobrescribir
        source.replace(target)
        return True
    except Exception as e:
        print_error(f"Error moviendo {svg_name}: {e}")
        return False

def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print_header("Generador de Documentación SVG - AlmaGag")

    # Rutas
    project_root = Path(__file__).parent.parent
    gags_dir = project_root / "docs" / "diagrams" / "gags"
    svgs_dir = project_root / "docs" / "diagrams" / "svgs"

    # Verificar que existan los directorios
    if not gags_dir.exists():
        print_error(f"Directorio no encontrado: {gags_dir}")
        sys.exit(1)

    if not svgs_dir.exists():
        print_info(f"Creando directorio: {svgs_dir}")
        svgs_dir.mkdir(parents=True)

    # Cambiar al directorio raíz del proyecto
    os.chdir(project_root)

    # Buscar todos los archivos .gag
    gag_files = sorted(gags_dir.glob("*.gag"))

    if not gag_files:
        print_error(f"No se encontraron archivos .gag en {gags_dir}")
        sys.exit(1)

    print_info(f"Encontrados {len(gag_files)} archivos .gag en {gags_dir.relative_to(project_root)}")
    print()

    # Contadores
    success_count = 0
    error_count = 0

    # Procesar cada archivo
    for i, gag_file in enumerate(gag_files, 1):
        print(f"[{i}/{len(gag_files)}] Procesando: {Colors.BOLD}{gag_file.name}{Colors.END}")

        # Generar SVG
        if generate_svg(gag_file, verbose):
            # El SVG se genera en el directorio actual con el mismo nombre
            svg_name = gag_file.stem + ".svg"

            # Mover al directorio de docs
            if move_svg_to_docs(svg_name, svgs_dir):
                print_success(f"Generado: {svg_name} → {svgs_dir.relative_to(project_root)}/")
                success_count += 1
            else:
                error_count += 1
        else:
            error_count += 1

        print()

    # Reporte final
    print_header("Reporte Final")

    print(f"  Total procesados:  {Colors.BOLD}{len(gag_files)}{Colors.END}")
    print(f"  {Colors.GREEN}Exitosos:{Colors.END}        {success_count}")
    print(f"  {Colors.RED}Errores:{Colors.END}          {error_count}")
    print()

    if error_count == 0:
        print_success("Toda la documentación se generó correctamente")
        return 0
    else:
        print_error(f"Algunos archivos fallaron ({error_count}/{len(gag_files)})")
        return 1

if __name__ == "__main__":
    sys.exit(main())
