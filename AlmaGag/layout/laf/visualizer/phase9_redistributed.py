"""LAF Visualizer — auto-extraído de visualizer.py (WISH-ARCH-003 sub-tarea B)."""

import os
import math
import logging
import svgwrite
from typing import Dict, List, Tuple
from copy import deepcopy
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.utils import extract_item_id
from AlmaGag.layout.laf.structure_analyzer import StructureInfo

logger = logging.getLogger('AlmaGag')


def generate(viz, output_path):
    """
    Genera SVG de Fase 9: Redistribución vertical.
    """
    snapshot = viz.snapshots['phase9']
    layout = snapshot['layout']
    structure_info = snapshot.get('structure_info')

    filename = os.path.join(output_path, "phase9_redistributed.svg")

    canvas_width = layout.canvas.get('width', 2000)
    canvas_height = layout.canvas.get('height', 2000)

    dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

    dwg.add(dwg.text(
        'LAF Phase 9: Vertical Redistribution',
        insert=(20, 30), font_size='20px', font_weight='bold', fill='#212529'
    ))

    ndfn_labels = viz._build_ndfn_labels(layout, structure_info)
    viz._draw_straight_connections(dwg, layout)
    viz._draw_elements_with_ndfn(dwg, layout, ndfn_labels)

    dwg.add(dwg.text(
        'Phase 9/11', insert=(canvas_width - 100, 30),
        font_size='14px', fill='#6c757d'
    ))

    dwg.save()
    if viz.debug:
        logger.debug(f"[VISUALIZER] Generado: {filename}")
