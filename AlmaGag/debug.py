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
        return "2.0.0"


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
    Si cairosvg no está instalado, muestra una advertencia pero no falla.

    Args:
        svg_path: Ruta completa al archivo SVG
        scale: Factor de escala para la resolución (default: 2.0 = 2x)
    """
    try:
        import cairosvg
    except (ImportError, OSError) as e:
        if isinstance(e, ImportError):
            print("[WARN] cairosvg no está instalado. PNG no generado.")
            print("      Instalar con: pip install cairosvg")
        else:
            print("[WARN] Librería Cairo no encontrada en el sistema. PNG no generado.")
            print("      En Windows: Descargar GTK+ desde https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
            print("      En Linux: sudo apt-get install libcairo2")
            print("      En macOS: brew install cairo")
        return

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

        # Convertir SVG a PNG con escala para mayor resolución
        cairosvg.svg2png(
            url=svg_path,
            write_to=png_path,
            scale=scale
        )

        print(f"[OK] PNG generado: {png_path}")

    except OSError as e:
        print(f"[WARN] No se pudo crear carpeta debugs/: {e}")
    except Exception as e:
        print(f"[ERROR] No se pudo convertir a PNG: {e}")
