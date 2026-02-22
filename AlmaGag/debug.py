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
import logging
from datetime import datetime

logger = logging.getLogger('AlmaGag')


def get_gag_version() -> str:
    """
    Obtiene la versión de AlmaGag desde los metadatos del paquete.

    Returns:
        str: Versión de GAG (ej: "2.0.0")
    """
    try:
        from importlib.metadata import version
        return version("AlmaGag")
    except ImportError:
        # Fallback si no se puede obtener desde metadata
        return "3.0.0"


def add_debug_badge(dwg, canvas_width: int, canvas_height: int) -> None:
    """
    Agrega un badge de debug en la esquina superior derecha del SVG.
    También dibuja una franja de fondo azul marino claro para el área de debug.

    El badge muestra:
    - Fecha y hora de generación (en rojo)
    - Versión de GAG utilizada (en rojo)

    Args:
        dwg: Objeto svgwrite.Drawing
        canvas_width: Ancho del canvas en píxeles
        canvas_height: Alto del canvas en píxeles
    """
    # Posición del badge (esquina superior derecha)
    # El texto del badge se extiende ~240px, entonces necesitamos más espacio
    badge_width = 240  # Aumentado de 190 a 240
    badge_x = canvas_width - badge_width - 10  # Margen de 10px desde el borde
    badge_y = 10
    badge_height = 60

    # FRANJA DE DEBUG: Dibuja fondo azul marino claro para toda el área de debug
    # Altura total: 10px (arriba) + 60px (badge) + 10px (abajo) = 80px
    debug_area_height = 10 + badge_height + 10
    dwg.add(dwg.rect(
        insert=(0, 0),
        size=(canvas_width, debug_area_height),
        fill='#E6F2FF',  # Azul marino muy claro
        opacity=0.3
    ))

    # Rectángulo de fondo azul acero claro para el badge (light steel blue)
    dwg.add(dwg.rect(
        insert=(badge_x, badge_y),
        size=(badge_width, badge_height),
        fill='#B0C4DE',  # Light steel blue
        fill_opacity=0.9,
        stroke='#4682B4',  # Steel blue
        stroke_width=2,
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
        fill="#001F3F",  # Navy blue oscuro para contraste con azul acero
        font_weight="bold"
    ))

    # Texto línea 2: Versión de GAG
    version_texto = f"GAG v{get_gag_version()}"
    dwg.add(dwg.text(
        version_texto,
        insert=(badge_x + 10, badge_y + 42),
        font_size="11px",
        font_family="Arial, monospace",
        fill="#001F3F",  # Navy blue oscuro para contraste con azul acero
        font_weight="bold"
    ))


def convert_svg_to_png(svg_path: str, scale: float = 2.0) -> None:
    """
    Convierte un archivo SVG a PNG y lo guarda en la carpeta debug/outputs/.

    La conversión se realiza con una escala 2x para obtener mayor resolución.
    Usa Chrome/Edge/Chromium en modo headless (sin dependencias extra en Windows).

    Args:
        svg_path: Ruta completa al archivo SVG
        scale: Factor de escala para la resolución (default: 2.0 = 2x)
    """
    import subprocess
    import xml.etree.ElementTree as ET

    try:
        # Obtener nombre base del SVG
        svg_name = os.path.basename(svg_path)
        base_name = os.path.splitext(svg_name)[0]

        # Crear carpeta debug/outputs/ en la raíz del proyecto
        # Asumimos que estamos ejecutando desde el directorio del proyecto
        debug_dir = os.path.join(os.getcwd(), 'debug', 'outputs')
        os.makedirs(debug_dir, exist_ok=True)

        # Ruta de salida para el PNG
        png_path = os.path.join(debug_dir, f"{base_name}.png")

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
            logger.warning("Chrome/Edge no encontrado. PNG no generado.")
            logger.warning("  Alternativas:")
            logger.warning("  1. Instalar Chrome: https://www.google.com/chrome/")
            logger.warning("  2. Instalar Cairo + GTK: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
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
            logger.info(f"PNG generado: {png_path}")
        else:
            logger.error(f"Chrome falló al generar PNG")
            if result.stderr:
                logger.error(f"  {result.stderr}")

    except FileNotFoundError:
        logger.error("Archivo SVG no encontrado")
    except subprocess.TimeoutExpired:
        logger.error("Timeout al ejecutar Chrome")
    except (ValueError, OSError, ET.ParseError) as e:
        logger.error(f"No se pudo convertir a PNG: {e}")
