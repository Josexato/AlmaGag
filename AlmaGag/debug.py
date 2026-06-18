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


# ============================================================================
# Layout dump utilities (movido desde generator.py — WISH-ARCH-001 cleanup)
# ============================================================================
import csv
from AlmaGag.config import (
    ICON_WIDTH, ICON_HEIGHT, TEXT_LINE_HEIGHT,
    CONTAINER_ICON_X, CONTAINER_ICON_Y, CONTAINER_LABEL_X, CONTAINER_LABEL_Y,
)
from AlmaGag.utils import extract_item_id


def dump_layout_table(optimized_layout, elements_by_id, containers, phase="FINAL", csv_file=None):
    """
    Genera una tabla con información detallada de todos los elementos del layout.
    Guarda en CSV para análisis posterior.

    Args:
        optimized_layout: Layout optimizado con información de niveles y grupos
        elements_by_id: Diccionario de elementos por ID
        containers: Lista de contenedores
        phase: Nombre de la fase del proceso (ej: "INITIAL", "PHASE_1", "PHASE_2", etc.)
        csv_file: Ruta del archivo CSV donde guardar (si None, genera con timestamp)
    """
    if csv_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"debug/layout_evolution_{timestamp}.csv"
    logger.debug("\n" + "=" * 170)
    logger.debug(f"DUMP DEL LAYOUT - TABLA DE ELEMENTOS [{phase}]")
    logger.debug("=" * 170)

    header = (
        f"{'Phase':<20}{'Indice':<12}{'Nivel':<8}{'Grupo':<8}{'Tipo':<15}"
        f"{'ID':<30}{'Referencial':<30}{'X Local':<12}{'Y Local':<12}"
        f"{'X Global':<12}{'Y Global':<12}{'Ancho':<12}{'Alto':<12}"
    )
    logger.debug(header)
    logger.debug("-" * 170)

    rows = []

    def find_group(elem_id, groups):
        for idx, group_list in enumerate(groups, 1):
            if elem_id in group_list:
                return idx
        return 0

    global_index = 0

    contained_elements = set()
    for container in containers:
        for item in container.get('contains', []):
            item_id = extract_item_id(item)
            contained_elements.add(item_id)

    for element in optimized_layout.elements:
        elem_id = element['id']
        if elem_id in contained_elements:
            continue

        level = optimized_layout.levels.get(elem_id, 0)
        group = find_group(elem_id, optimized_layout.groups)
        is_container = 'contains' in element

        if is_container:
            global_index += 1
            container_index = global_index
            x_global = element.get('x', None)
            y_global = element.get('y', None)
            width = element.get('width', None)
            height = element.get('height', None)
            indice = f"{container_index:02d}.00.00"

            rows.append({
                'phase': phase, 'indice': indice, 'nivel': level, 'grupo': group,
                'tipo': 'Contenedor', 'id': f"{elem_id}.Cnt", 'referencial': 'origen',
                'x_local': 0, 'y_local': 0,
                'x_global': x_global if x_global is not None else 0,
                'y_global': y_global if y_global is not None else 0,
                'width': width if width is not None else 0,
                'height': height if height is not None else 0,
            })

            icon_x_local = CONTAINER_ICON_X
            icon_y_local = CONTAINER_ICON_Y
            icon_x_global = x_global + icon_x_local if x_global is not None else 0
            icon_y_global = y_global + icon_y_local if y_global is not None else 0
            child_num = 1
            icon_indice = f"{container_index:02d}.{child_num:02d}.00"

            rows.append({
                'phase': phase, 'indice': icon_indice, 'nivel': level, 'grupo': group,
                'tipo': 'Icono', 'id': elem_id, 'referencial': f"{elem_id}.Cnt",
                'x_local': icon_x_local, 'y_local': icon_y_local,
                'x_global': icon_x_global, 'y_global': icon_y_global,
                'width': ICON_WIDTH, 'height': ICON_HEIGHT,
            })

            if element.get('label'):
                label_x_local = CONTAINER_LABEL_X
                label_y_local = CONTAINER_LABEL_Y
                label_x_global = x_global + label_x_local if x_global is not None else 0
                label_y_global = y_global + label_y_local if y_global is not None else 0
                lines = element['label'].split('\n')
                label_width = max(len(line) for line in lines) * 8
                label_height = len(lines) * TEXT_LINE_HEIGHT
                label_indice = f"{container_index:02d}.01.01"

                rows.append({
                    'phase': phase, 'indice': label_indice, 'nivel': level, 'grupo': group,
                    'tipo': 'Etiqueta', 'id': f"{elem_id}.Lbl", 'referencial': elem_id,
                    'x_local': label_x_local, 'y_local': label_y_local,
                    'x_global': label_x_global, 'y_global': label_y_global,
                    'width': label_width, 'height': label_height,
                })

            child_index = 1
            for ref in element.get('contains', []):
                child_index += 1
                ref_id = extract_item_id(ref)
                contained_elem = elements_by_id.get(ref_id)
                if not contained_elem:
                    continue

                container_x = element.get('x', None)
                container_y = element.get('y', None)
                elem_x_global = contained_elem.get('x', None)
                elem_y_global = contained_elem.get('y', None)
                if elem_x_global is not None and elem_y_global is not None:
                    elem_x_local = elem_x_global - container_x
                    elem_y_local = elem_y_global - container_y
                else:
                    elem_x_local = 0
                    elem_y_local = 0
                elem_width = contained_elem.get('width', ICON_WIDTH)
                elem_height = contained_elem.get('height', ICON_HEIGHT)
                child_icon_indice = f"{container_index:02d}.{child_index:02d}.00"

                rows.append({
                    'phase': phase, 'indice': child_icon_indice, 'nivel': level, 'grupo': group,
                    'tipo': 'Icono', 'id': ref_id, 'referencial': f"{elem_id}.Cnt",
                    'x_local': elem_x_local, 'y_local': elem_y_local,
                    'x_global': elem_x_global, 'y_global': elem_y_global,
                    'width': elem_width, 'height': elem_height,
                })

                if contained_elem.get('label'):
                    if ref_id in optimized_layout.label_positions:
                        label_pos = optimized_layout.label_positions[ref_id]
                        label_x_global, label_y_global = label_pos[0], label_pos[1]
                        if container_x is not None and container_y is not None:
                            label_x_local = label_x_global - container_x
                            label_y_local = label_y_global - container_y
                        else:
                            label_x_local = 0
                            label_y_local = 0
                    else:
                        label_x_local = elem_x_local + elem_width / 2 if elem_x_local is not None else 0
                        label_y_local = elem_y_local + elem_height + 15 if elem_y_local is not None else 0
                        label_x_global = elem_x_global + elem_width / 2 if elem_x_global is not None else 0
                        label_y_global = elem_y_global + elem_height + 15 if elem_y_global is not None else 0

                    label_text = contained_elem['label']
                    label_lines_csv = label_text.split('\n')
                    label_width_est = max(len(line) for line in label_lines_csv) * 8 if label_lines_csv else 0
                    label_height_est = len(label_lines_csv) * 18
                    child_label_indice = f"{container_index:02d}.{child_index:02d}.01"

                    rows.append({
                        'phase': phase, 'indice': child_label_indice, 'nivel': level, 'grupo': group,
                        'tipo': 'Etiqueta', 'id': f"{ref_id}.Lbl", 'referencial': ref_id,
                        'x_local': label_x_local, 'y_local': label_y_local,
                        'x_global': label_x_global, 'y_global': label_y_global,
                        'width': label_width_est, 'height': label_height_est,
                    })
        else:
            global_index += 1
            element_index = global_index
            x_global = element.get('x', None)
            y_global = element.get('y', None)
            width = element.get('width', ICON_WIDTH)
            height = element.get('height', ICON_HEIGHT)
            normal_indice = f"{element_index:02d}.00.00"

            rows.append({
                'phase': phase, 'indice': normal_indice, 'nivel': level, 'grupo': group,
                'tipo': 'Icono', 'id': elem_id, 'referencial': 'origen',
                'x_local': 0, 'y_local': 0,
                'x_global': x_global, 'y_global': y_global,
                'width': width, 'height': height,
            })

            if element.get('label'):
                label_x_global = x_global + width / 2 if x_global is not None else 0
                label_y_global = y_global + height + 15 if y_global is not None else 0
                label_text = element['label']
                lines = label_text.split('\n')
                label_width_est = max(len(line) for line in lines) * 8
                label_height_est = len(lines) * 18
                normal_label_indice = f"{element_index:02d}.00.01"

                rows.append({
                    'phase': phase, 'indice': normal_label_indice, 'nivel': level, 'grupo': group,
                    'tipo': 'Etiqueta', 'id': f"{elem_id}.Lbl", 'referencial': elem_id,
                    'x_local': 0, 'y_local': 0,
                    'x_global': label_x_global, 'y_global': label_y_global,
                    'width': label_width_est, 'height': label_height_est,
                })

    for row in rows:
        phase_str = str(row['phase'])
        indice_str = str(row['indice'])
        nivel_str = str(row['nivel']) if row['nivel'] is not None else 0
        grupo_str = str(row['grupo']) if row['grupo'] is not None else 0
        x_local_str = f"{row['x_local']:.1f}" if isinstance(row['x_local'], (int, float)) else str(row['x_local'])
        y_local_str = f"{row['y_local']:.1f}" if isinstance(row['y_local'], (int, float)) else str(row['y_local'])
        x_global_str = f"{row['x_global']:.1f}" if isinstance(row['x_global'], (int, float)) else str(row['x_global'])
        y_global_str = f"{row['y_global']:.1f}" if isinstance(row['y_global'], (int, float)) else str(row['y_global'])
        width_str = f"{row['width']:.1f}" if isinstance(row['width'], (int, float)) else str(row['width'])
        height_str = f"{row['height']:.1f}" if isinstance(row['height'], (int, float)) else str(row['height'])
        line = (
            f"{phase_str:<20}{indice_str:<12}{nivel_str:<8}{grupo_str:<8}"
            f"{row['tipo']:<15}{row['id']:<30}{row['referencial']:<30}"
            f"{x_local_str:<12}{y_local_str:<12}{x_global_str:<12}{y_global_str:<12}"
            f"{width_str:<12}{height_str:<12}"
        )
        logger.debug(line)
    logger.debug("=" * 170 + "\n")

    _save_to_csv(rows, csv_file)


def _save_to_csv(rows, csv_file):
    """Guarda las filas del layout en un CSV."""
    if not rows:
        return
    csv_dir = os.path.dirname(csv_file)
    if csv_dir and not os.path.exists(csv_dir):
        os.makedirs(csv_dir)
    file_exists = os.path.exists(csv_file)
    fieldnames = ['phase', 'indice', 'nivel', 'grupo', 'tipo', 'id', 'referencial',
                  'x_local', 'y_local', 'x_global', 'y_global', 'width', 'height']
    try:
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)
        logger.debug(f"[CSV] Datos guardados en: {csv_file} ({len(rows)} filas)")
    except (IOError, OSError) as e:
        logger.error(f"[CSV] Error al guardar CSV: {e}")


# ============================================================================
# Visual debug helpers (movido desde generator.py)
# ============================================================================

def draw_grid(dwg, width, height, grid_size=20):
    """Dibuja una rejilla de guía en el fondo del diagrama."""
    grid_group = dwg.g(id='grid', opacity=0.4)
    for x in range(0, int(width) + 1, grid_size):
        grid_group.add(dwg.line(start=(x, 0), end=(x, height), stroke='#C0C0C0', stroke_width=1))
    for y in range(0, int(height) + 1, grid_size):
        grid_group.add(dwg.line(start=(0, y), end=(width, y), stroke='#C0C0C0', stroke_width=1))
    dwg.add(grid_group)


def draw_guide_lines(dwg, width, guide_lines):
    """Dibuja líneas horizontales de guía en posiciones Y específicas."""
    if not guide_lines:
        return
    guide_group = dwg.g(id='guide_lines', opacity=0.8)
    for y in guide_lines:
        guide_group.add(dwg.line(
            start=(0, y), end=(width, y),
            stroke='#FF0000', stroke_width=1.5, stroke_dasharray='5,5',
        ))
        guide_group.add(dwg.text(
            f'Y={y}', insert=(5, y - 3),
            font_size='10px', font_family='Arial, sans-serif',
            fill='#FF0000', font_weight='bold',
        ))
    dwg.add(guide_group)


def draw_debug_free_ranges(dwg, free_ranges, width):
    """Dibuja franjas libres de redistribución en modo debug."""
    if not free_ranges:
        return
    light_steel_blue = '#B0C4DE'
    ranges_group = dwg.g(id='debug_free_ranges', opacity=0.15)
    for i, (y_start, y_end) in enumerate(free_ranges):
        height = y_end - y_start
        ranges_group.add(dwg.rect(
            insert=(0, y_start), size=(width, height),
            fill=light_steel_blue, stroke='#4682B4',
            stroke_width=2, stroke_dasharray='5,5',
        ))
        text_bg_width = 250
        text_bg_height = 20
        ranges_group.add(dwg.rect(
            insert=(8, y_start + 2), size=(text_bg_width, text_bg_height),
            fill='white', opacity=0.8, rx=3, ry=3,
        ))
        ranges_group.add(dwg.text(
            f'Franja {i+1}: Y[{y_start:.0f}-{y_end:.0f}] h={height:.0f}px',
            insert=(10, y_start + 16),
            font_size='12px', font_family='Arial, sans-serif',
            fill='#2F4F4F', font_weight='bold',
        ))
    dwg.add(ranges_group)
