"""
Debug utilities for AlmaGag SVG generation.

Provides functionality to:
- Add debug badges to SVG files showing generation date and version
- Convert SVG files to PNG format for visual inspection

Autor: José + ALMA
Versión: 1.0
Fecha: 2026-01-09
"""

import os
from datetime import datetime


def get_gag_version() -> str:
    """
    Obtiene la versión de AlmaGag desde los metadatos del paquete.

    Returns:
        str: Versión de GAG (ej: "2.0.0")
    """
    try:
        from importlib.metadata import version
        return version("AlmaGag")
    except Exception:
        # Fallback si no se puede obtener desde metadata
        return "3.0.0"


def add_debug_badge(dwg, canvas_width: int, canvas_height: int) -> None:
    """
    Agrega un badge de debug en la esquina superior derecha del SVG.

    El badge muestra:
    - Fecha y hora de generación (en rojo)
    - Versión de GAG utilizada (en rojo)

    Args:
        dwg: Objeto svgwrite.Drawing
        canvas_width: Ancho del canvas en píxeles
        canvas_height: Alto del canvas en píxeles
    """
    # Posición del badge (esquina superior derecha)
    badge_x = canvas_width - 200
    badge_y = 10
    badge_width = 190
    badge_height = 60

    # Rectángulo de fondo semi-transparente
    dwg.add(dwg.rect(
        insert=(badge_x, badge_y),
        size=(badge_width, badge_height),
        fill='white',
        fill_opacity=0.85,
        stroke='#CCCCCC',
        stroke_width=1,
        rx=5,
        ry=5
    ))

    # Texto línea 1: Fecha de generación
    fecha_texto = f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    dwg.add(dwg.text(
        fecha_texto,
        insert=(badge_x + 10, badge_y + 22),
        font_size="11px",
        font_family="Arial, monospace",
        fill="#FF0000"  # ROJO
    ))

    # Texto línea 2: Versión de GAG
    version_texto = f"GAG v{get_gag_version()}"
    dwg.add(dwg.text(
        version_texto,
        insert=(badge_x + 10, badge_y + 42),
        font_size="11px",
        font_family="Arial, monospace",
        fill="#FF0000"  # ROJO
    ))


def convert_svg_to_png(svg_path: str, scale: float = 2.0) -> None:
    """
    Convierte un archivo SVG a PNG y lo guarda en la carpeta debugs/.

    La conversión se realiza con una escala 2x para obtener mayor resolución.
    Usa Chrome/Edge/Chromium en modo headless (sin dependencias extra en Windows).

    Args:
        svg_path: Ruta completa al archivo SVG
        scale: Factor de escala para la resolución (default: 2.0 = 2x)
    """
    import subprocess
    import xml.etree.ElementTree as ET

    try:
        # Obtener directorio y nombre base del SVG
        svg_dir = os.path.dirname(svg_path)
        svg_name = os.path.basename(svg_path)
        base_name = os.path.splitext(svg_name)[0]

        # Crear carpeta debugs/ si no existe
        debugs_dir = os.path.join(svg_dir, 'debugs')
        os.makedirs(debugs_dir, exist_ok=True)

        # Ruta de salida para el PNG
        png_path = os.path.join(debugs_dir, f"{base_name}.png")

        # Leer dimensiones del SVG
        tree = ET.parse(svg_path)
        root = tree.getroot()
        width = int(float(root.get('width', '800')))
        height = int(float(root.get('height', '600')))

        # Aplicar escala
        width = int(width * scale)
        height = int(height * scale)

        # Convertir ruta absoluta para Chrome
        svg_abs_path = os.path.abspath(svg_path)
        png_abs_path = os.path.abspath(png_path)

        # Buscar Chrome/Edge/Chromium en ubicaciones comunes de Windows
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]

        chrome_exe = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_exe = path
                break

        if chrome_exe is None:
            print("[WARN] Chrome/Edge no encontrado. PNG no generado.")
            print("      Alternativas:")
            print("      1. Instalar Chrome: https://www.google.com/chrome/")
            print("      2. Instalar Cairo + GTK: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
            return

        # Ejecutar Chrome en modo headless para captura
        cmd = [
            chrome_exe,
            '--headless',
            '--disable-gpu',
            f'--screenshot={png_abs_path}',
            f'--window-size={width},{height}',
            f'file:///{svg_abs_path.replace(chr(92), "/")}'  # Convertir \ a /
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and os.path.exists(png_path):
            print(f"[OK] PNG generado: {png_path}")
        else:
            print(f"[ERROR] Chrome falló al generar PNG")
            if result.stderr:
                print(f"      {result.stderr}")

    except FileNotFoundError:
        print("[ERROR] Archivo SVG no encontrado")
    except subprocess.TimeoutExpired:
        print("[ERROR] Timeout al ejecutar Chrome")
    except Exception as e:
        print(f"[ERROR] No se pudo convertir a PNG: {e}")
