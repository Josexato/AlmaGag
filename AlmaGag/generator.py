import os
import json
import logging

from datetime import datetime
from AlmaGag.config import WIDTH, HEIGHT
from AlmaGag.layout import Layout, AutoLayoutOptimizer
from AlmaGag.debug import dump_layout_table

# Logger global para AlmaGag
logger = logging.getLogger('AlmaGag')


def generate_diagram(json_file, debug=False, visualdebug=False, exportpng=False, guide_lines=None, dump_iterations=False, output_file=None, layout_algorithm='auto', visualize_growth=False, color_connections=False, **centrality_kwargs):
    # Configurar logging si debug está activo
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(levelname)s] %(name)s: %(message)s',
            force=True
        )
        logger.setLevel(logging.DEBUG)
        logger.debug("="*70)
        logger.debug("MODO DEBUG ACTIVADO")
        logger.debug("="*70)
    else:
        logging.basicConfig(level=logging.INFO)
        logger.setLevel(logging.INFO)

    if not os.path.exists(json_file):
        logger.error(f"Archivo no encontrado: {json_file}")
        return False

    logger.debug(f"Leyendo archivo: {json_file}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        logger.error(f"Error al leer el JSON: {e}")
        return False

    # WISH-LAYOUT-004 Fase 2: auto-detección de template por estructura del grafo.
    # Prioridad:
    #   1. Override manual: `"layout_template": "<name>"` en SDJF → aplicar ese.
    #   2. Auto-detección: `"layout_template": "auto"` → clasificar grafo y aplicar.
    #   3. Sin declaración → comportamiento agnóstico (AUTO/LAF normal).
    # Los templates respetan coords manuales: solo asignan a elementos sin x/y.
    template_name = data.get('layout_template')
    if template_name == 'auto':
        from AlmaGag.layout.templates import auto_apply_template
        applied, scores = auto_apply_template(data)
        scores_str = ', '.join(f'{n}={s:.2f}' for n, s in scores)
        if applied:
            logger.info(f"Layout template auto-detectado: '{applied}' [scores: {scores_str}]")
        else:
            logger.info(f"Layout template auto-detect: ningún template superó el threshold [scores: {scores_str}] — usando algoritmo agnóstico")
    elif template_name:
        from AlmaGag.layout.templates import apply_template
        if apply_template(template_name, data):
            logger.info(f"Layout template '{template_name}' aplicado (override manual)")
        else:
            logger.warning(f"Layout template '{template_name}' desconocido — ignorado")

    # Extraer iconos SVG embebidos (formato .gag extendido)
    embedded_icons = data.get('icons', None)
    if embedded_icons:
        logger.info(f"{len(embedded_icons)} icono(s) SVG embebido(s) detectado(s)")

    # Determinar ruta de salida
    if output_file:
        # Usar la ruta proporcionada
        output_svg = output_file
        # Crear directorio de salida si no existe
        output_dir = os.path.dirname(output_svg)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Directorio creado: {output_dir}")
    else:
        # Comportamiento por defecto: generar en el directorio actual
        base_name = os.path.splitext(os.path.basename(json_file))[0]
        output_svg = f"{base_name}.svg"

    logger.debug(f"Elementos: {len(data.get('elements', []))}")
    logger.debug(f"Conexiones: {len(data.get('connections', []))}")

    # Leer canvas del JSON o usar valores por defecto
    canvas = data.get('canvas', {})
    canvas_width = canvas.get('width', WIDTH)
    canvas_height = canvas.get('height', HEIGHT)

    all_elements = data.get('elements', [])
    all_connections = data.get('connections', [])

    # === NUEVO FLUJO: Layout + AutoLayoutOptimizer v2.1 ===

    # 1. Crear Layout inmutable
    initial_layout = Layout(
        elements=all_elements,
        connections=all_connections,
        canvas={'width': canvas_width, 'height': canvas_height}
    )

    # Agregar nombre del diagrama para visualizador
    diagram_name = os.path.splitext(os.path.basename(json_file))[0]
    initial_layout._diagram_name = diagram_name

    # 2. Instanciar optimizador (WISH-ARCH-001 resuelto: factoría unificada).
    # Ambos optimizers heredan de LayoutOptimizer y son self-contained.
    from AlmaGag.layout.laf.optimizer import LAFOptimizer
    OPTIMIZERS = {
        'auto': AutoLayoutOptimizer,
        'laf':  LAFOptimizer,
    }
    optimizer_cls = OPTIMIZERS[layout_algorithm]
    optimizer_kwargs = {'verbose': debug, 'visualdebug': visualdebug}
    if layout_algorithm == 'laf':
        optimizer_kwargs['visualize_growth'] = visualize_growth
        optimizer_kwargs.update(centrality_kwargs)
    optimizer = optimizer_cls(**optimizer_kwargs)
    logger.debug(f"{optimizer_cls.__name__} instanciado ({optimizer_kwargs})")

    # 3. Optimizar (retorna NUEVO layout)
    #    NOTA: optimize() ahora maneja auto-layout para coordenadas faltantes (SDJF v2.0)

    # Generar nombre de CSV con timestamp para evitar sobreescritura
    csv_file = None
    if debug:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"debug/layout_evolution_{timestamp}.csv"
        logger.debug(f"[CSV] Archivo de evolución: {csv_file}")

    # Firma unificada: optimize(layout, max_iterations, dump_iterations, input_file).
    # LAF ignora los kwargs que no aplican a su pipeline.
    optimized_layout = optimizer.optimize(
        initial_layout,
        max_iterations=10,
        dump_iterations=dump_iterations,
        input_file=json_file,
    )

    # Mostrar info de estructura (después de auto-layout)
    num_levels = len(set(optimized_layout.levels.values()))
    num_groups = len(optimized_layout.groups)
    high_priority = sum(1 for priority in optimized_layout.priorities.values() if priority == 0)
    normal_priority = sum(1 for priority in optimized_layout.priorities.values() if priority == 1)
    low_priority = sum(1 for priority in optimized_layout.priorities.values() if priority == 2)

    # Mostrar resultados
    remaining = optimized_layout._collision_count if optimized_layout._collision_count is not None else 0

    if remaining > 0:
        logger.warning(f"AutoLayout v2.1: {remaining} colisiones detectadas")
    else:
        logger.info(f"AutoLayout v2.1: 0 colisiones detectadas")

    logger.info(f"     - {num_levels} niveles, {num_groups} grupo(s)")
    logger.info(f"     - Prioridades: {high_priority} high, {normal_priority} normal, {low_priority} low")

    # 5. Obtener canvas final (puede haber sido expandido)
    final_canvas = optimized_layout.canvas
    if final_canvas['width'] > canvas_width or final_canvas['height'] > canvas_height:
        canvas_width = final_canvas['width']
        canvas_height = final_canvas['height']
        logger.info(f"     - Canvas expandido a {canvas_width}x{canvas_height}")

    # 5. Sync canvas back to layout (puede haberse expandido).
    optimized_layout.canvas['width'] = canvas_width
    optimized_layout.canvas['height'] = canvas_height

    # 6. Dump CSV en modo debug (antes de renderizar).
    if debug and csv_file:
        containers = [e for e in optimized_layout.elements if 'contains' in e]
        elements_by_id = {e['id']: e for e in optimized_layout.elements}
        dump_layout_table(optimized_layout, elements_by_id, containers,
                          phase="OPTIMIZED", csv_file=csv_file)

    # 7. Renderizar — cada algoritmo tiene su propio renderer (WISH-ARCH-002).
    optimizer.renderer.render(
        optimized_layout,
        output_svg,
        visualdebug=visualdebug,
        guide_lines=guide_lines,
        debug=debug,
        color_connections=color_connections,
        embedded_icons=embedded_icons,
        exportpng=exportpng,
    )

    return True
