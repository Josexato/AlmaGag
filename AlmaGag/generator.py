import os
import json
import logging

from datetime import datetime
from AlmaGag.config import WIDTH, HEIGHT
from AlmaGag.layout import Layout, AutoLayoutOptimizer
from AlmaGag.debug import dump_layout_table

# Logger global para AlmaGag
logger = logging.getLogger('AlmaGag')


def select_strategy(data, view='auto'):
    """Un solo algoritmo: elige la mejor estrategia de layout a partir del JSON.

    El usuario normalmente NO elige algoritmo — corre `almagag archivo.json` y
    el motor decide. Sólo si un parámetro de comando fuerza algo (una vista o un
    `--layout-algorithm` explícito) se respeta esa elección.

    Política (conservadora, no regresiona los canónicos de arquitectura):
    - una vista explícita (`--view`) → esa vista es de hier
    - `areas` + `contains` → hier: la vista por ámbitos monta los
      contenedores DENTRO de sus áreas (WISH-ARCH-009)
    - contenedores (`contains`) sin áreas → AUTO
    - metadata de fases (`areas`) → flujo por ámbitos (hier)
    - nodos de decisión (rombos) → flowchart → hier
    - flujo CON CICLO, sin coords manuales → hier (niveles + arcos de ciclo)
    - en cualquier otro caso → AUTO (placement general)

    §O53 — precedencia DECLARADA: cuando dos señales del JSON piden motores
    distintos (p.ej. `considerations`→AUTO contra `areas`→hier, el conflicto
    N46⇄I27), la de mayor precedencia gana pero la anulada se nombra en un
    WARNING — nunca se pierde en silencio.
    """
    elements = data.get('elements', [])
    soft = 'considerations' if data.get('considerations') else (
        'constraints' if data.get('constraints') else None)
    if view and view != 'auto':
        if soft:
            logger.warning(
                f"§O53: la vista '--view {view}' fuerza hier — señal anulada: "
                f"'{soft}' (align/near/avoid, §④) sólo la aplica AUTO")
        return 'hier'                       # las vistas (areas/lanes/matrix) son de hier
    if soft:
        if data.get('areas'):
            logger.info(
                f"§O53: '{soft}' fuerza AUTO — 'areas' (§I27) se representa "
                "como zonas near (§N46): cajas punteadas rotuladas, no la "
                "vista por ámbitos de hier")
        return 'auto'                       # consideraciones (align/near/avoid): sólo AUTO
    if any('contains' in e for e in elements):
        if data.get('areas'):
            # WISH-ARCH-009: las áreas ganan — escenografía primero. Antes
            # `contains` forzaba AUTO y las cajas de fase se anulaban.
            logger.info(
                "§O53: 'areas' + 'contains' — la vista por ámbitos (hier) "
                "monta los contenedores DENTRO de sus áreas (ARCH-009)")
            return 'hier'
        return 'auto'                       # contenedores sin áreas: AUTO
    if data.get('areas'):
        return 'hier'
    types = {e.get('type') for e in elements}
    if types & {'decision', 'diamond'}:
        return 'hier'
    # Un flujo dirigido CON CICLO y sin coordenadas manuales es el dominio de
    # hier (niveles + arcos de ciclo E15–E17); auto lo aplana a una fila y rutea
    # en diagonal perforando iconos. Estrecho a ciclos: los DAGs sin ciclo se
    # dejan en auto (hier los renderiza peor — ver K37). Medido: 14-stresstest
    # 5→1 cruces, layout-optimization-flow 7→3, sin solapes nuevos.
    if not any(('x' in e or 'y' in e) for e in elements) and \
            _has_cycle(elements, data.get('connections', [])):
        return 'hier'
    return 'auto'


def _has_cycle(elements, connections) -> bool:
    """True si el grafo dirigido tiene un ciclo (SCC de 2+ o self-loop)."""
    ids = [e['id'] for e in elements]
    idset = set(ids)
    out = {i: [] for i in ids}
    for c in connections:
        f, t = c.get('from'), c.get('to')
        if f == t and f in idset:
            return True                     # self-loop
        if f in out and t in idset:
            out[f].append(t)
    from AlmaGag.layout.strategies.hier.scc import strongly_connected_components
    return any(len(s) >= 2 for s in strongly_connected_components(ids, out))


def generate_diagram(json_file, debug=False, visualdebug=False, exportpng=False, guide_lines=None, dump_iterations=False, output_file=None, layout_algorithm='select', view='auto', visualize_growth=False, color_connections=False, **centrality_kwargs):
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

    # v3.9 — consistencia del término «flow» (decisión del autor, 11-ago):
    # una palabra = un concepto. Guardas de migración que ENSEÑAN:
    if 'flows' in data:
        raise ValueError(
            "[formato] 'flows' se renombró a 'journeys' en v3.9 — misma "
            "estructura ({id, label, color, path}); sólo cambia la clave")
    if data.get('layout_template') == 'flow':
        logger.warning("[formato] el template 'flow' se renombró a 'steps' "
                       "en v3.9 — se ignora; declarar layout_template: "
                       "'steps'")
        data['layout_template'] = None
    for _c in data.get('connections', []):
        if _c.get('semantic_type') in ('data_flow', 'control_flow'):
            _new = _c['semantic_type'].replace('_flow', '_link')
            logger.warning(f"[formato] semantic_type '{_c['semantic_type']}' "
                           f"se renombró a '{_new}' en v3.9 — se tratará "
                           f"como clase custom sin color")

    # BUGS-ARCH-002: campos que deben ser OBJETO pero llegan como string
    # (errores naturales de autor) se coercen con aviso — nunca un
    # AttributeError crudo que mata la corrida sin decir dónde.
    for _c in data.get('connections', []):
        _r = _c.get('routing')
        if isinstance(_r, str):
            logger.warning(f"[formato] routing como string ('{_r}') — "
                           f"interpretado como {{\"type\": \"{_r}\"}}")
            _c['routing'] = {'type': _r}
        elif _r is not None and not isinstance(_r, dict):
            logger.warning(f"[formato] routing inválido ({type(_r).__name__})"
                           f" en {_c.get('from')}→{_c.get('to')} — se ignora")
            _c.pop('routing', None)
    if isinstance(data.get('roles'), dict):
        for _k, _v in list(data['roles'].items()):
            if isinstance(_v, str):
                logger.warning(f"[formato] roles['{_k}'] como string — "
                               f"interpretado como {{\"label\": \"{_v}\"}} "
                               f"SIN color; declarar {{\"label\", \"color\"}} "
                               f"para conservarlo")
                data['roles'][_k] = {'label': _v}

    # BUGS-VAL-007 (X90): el schema habla — toda clave declarada que el motor
    # no reconoce se NOMBRA antes de seguir; nunca silencio. Corre sobre el
    # JSON del autor, antes de que el pipeline inyecte claves internas.
    from AlmaGag.validation.schema import audit_schema
    audit_schema(data)

    # §H7: expandir `unions` (matrimonio) a nodo de barra + aristas padre→union
    # ANTES de decidir estrategia/template, para que el motor las trate como
    # nodos/aristas normales. No-op si el JSON no declara `unions`.
    from AlmaGag.layout.unions import expand_unions
    n_unions = expand_unions(data)
    if n_unions:
        logger.info(f"§H7: {n_unions} union(es) expandida(s) a nodo de barra")

    # §Q63: mapa `semantics` embebido en el archivo (como `icons{}`) — el
    # motor lo aplica mecánicamente a conexiones SIN semantic_type, con
    # WARNING; el vocabulario nunca vive en el código. Corre ANTES del tema
    # para que los colores del mapa puedan ser tokens §O57.
    from AlmaGag.layout.semantics import apply_embedded_semantics
    apply_embedded_semantics(data)

    # §O57: resolver tokens de tema (`theme` top-level + `"color": "<token>"`)
    # sobre el JSON crudo — el resto del pipeline sólo ve hex/nombres CSS.
    from AlmaGag.layout.theme import apply_theme
    apply_theme(data)

    # Decidir la estrategia sobre el JSON CRUDO (antes de que el template inyecte
    # coords). Si el motor elegido es hier, hier hace su propio placement por
    # niveles/columnas y el `layout_template` (que asigna coords pensadas para
    # AUTO) sólo lo estorbaría — se saltea. Este pre-cálculo también es el que se
    # usa después para el LayoutEngine (no se recalcula sobre data ya modificada).
    resolved_strategy = select_strategy(data, view) if layout_algorithm == 'select' else layout_algorithm

    # WISH-LAYOUT-004 Fase 2: auto-detección de template por estructura del grafo.
    # Prioridad:
    #   1. Override manual: `"layout_template": "<name>"` en SDJF → aplicar ese.
    #   2. Auto-detección: `"layout_template": "auto"` → clasificar grafo y aplicar.
    #   3. Sin declaración → comportamiento agnóstico (AUTO/LAF normal).
    # Los templates respetan coords manuales: solo asignan a elementos sin x/y.
    # Sólo se aplican cuando el motor es AUTO (hier ignora coords inyectadas).
    template_name = data.get('layout_template')
    if resolved_strategy == 'hier':
        if template_name:
            logger.info(f"Layout template '{template_name}' omitido: motor hier hace su propio placement")
    elif template_name == 'auto':
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

    # §Q64: inventario de BWTs activos — types sin icono resoluble. Usarlos
    # es legítimo (BWT deliberado mientras se decide su representación); el
    # inventario es la señal de promoción al catálogo (mismo type en ≥2
    # fixtures). El detalle por elemento lo avisa §O55 al dibujar.
    from AlmaGag.draw.icons import unresolved_icon_types
    bwt_types = unresolved_icon_types(data.get('elements', []), embedded_icons)
    if bwt_types:
        logger.info(f"§Q64: {len(bwt_types)} type(s) en BWT (inventario para "
                    f"el catálogo): {', '.join(bwt_types)}")

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
        canvas={'width': canvas_width, 'height': canvas_height,
                # WISH-LAYOUT-012 (V78): orientación de lectura declarada
                **({'flow': str(canvas['flow']).lower()}
                   if isinstance(canvas, dict) and canvas.get('flow') else {}),
                # WISH-DRAW-004 (V82): leyenda libre del autor
                **({'legend': canvas['legend']}
                   if isinstance(canvas, dict) and canvas.get('legend') else {}),
                # WISH-LAYOUT-021 (X91b): macro-plano declarado del lienzo
                **({'partition': canvas['partition']}
                   if isinstance(canvas, dict) and canvas.get('partition') else {})}
    )

    # Agregar nombre del diagrama para visualizador
    diagram_name = os.path.splitext(os.path.basename(json_file))[0]
    initial_layout._diagram_name = diagram_name

    # §I27/§I30: ámbitos por fase (areas) y leyenda de roles (opcionales; sólo
    # los consume el algoritmo hier). Retrocompatible: si faltan, camino normal.
    initial_layout._areas = data.get('areas')
    initial_layout._journeys = data.get('journeys')
    initial_layout._roles = data.get('roles')
    initial_layout._lanes = data.get('lanes')
    # §④ consideraciones BLANDAS (align/near/avoid): sólo las consume AUTO y las
    # aplica detrás de una guarda (sólo si no aumentan colisiones). Si el JSON no
    # las declara, queda [] y nada cambia (cero regresión).
    from AlmaGag.layout.considerations import (
        extract_considerations, areas_to_near_seeds)
    # §O53 (mediano plazo): si el motor quedó en AUTO habiendo `areas` (una
    # señal las anuló — blanda, `contains`, o el CLI forzó auto), las áreas
    # se siembran como zonas near §N46 — la caja de fase no se pierde,
    # cambia de traje. La siembra ya excluye a los miembros CONTENEDORES de
    # la grilla near (la grilla asume elementos normales), así que la vía
    # mixta «áreas + contenedores» convive: la fase es zona, el cluster
    # denso es contenedor.
    if resolved_strategy == 'auto' and data.get('areas'):
        n_zonas = areas_to_near_seeds(data)
        if n_zonas:
            logger.info(f"§O53: {n_zonas} área(s) sembrada(s) como zona(s) "
                        "near (§N46) para el motor AUTO")
    initial_layout._considerations = extract_considerations(data)
    # Vista del layout (§I): la REPRESENTACIÓN se decide sola a partir del JSON
    # y sólo se fuerza por parámetro de COMANDO (`--view`), nunca por un campo
    # del archivo. El JSON describe *qué es* (incluida la metadata semántica
    # areas/roles); el algoritmo decide *cómo se ve*; el CLI puede pisarlo.
    resolved_view = view if (view and view != 'auto') else 'auto'
    if resolved_view == 'auto':
        resolved_view = 'areas' if data.get('areas') else 'columns'
    initial_layout._layout_view = resolved_view

    # 2. Motor ÚNICO (WISH-ARCH-002): el generator ve UN solo optimizer, el
    # `LayoutEngine`. Si no se forzó una estrategia por CLI (`select`, el
    # default), el motor la elige a partir del JSON (`select_strategy`) y viaja
    # en `layout._strategy`. `auto/laf/hier` explícitos la fuerzan (avanzado/
    # debug); hier ya no es un algoritmo peer sino la estrategia de flujo.
    from AlmaGag.layout.engine import LayoutEngine
    if layout_algorithm == 'select':
        # Reusar la estrategia decidida sobre el JSON crudo (antes del template),
        # no recalcular sobre `data` ya modificada por el template.
        logger.info(f"     - Estrategia auto-seleccionada: {resolved_strategy}")
        initial_layout._strategy = resolved_strategy
        forced = None
    else:
        forced = layout_algorithm                 # override explícito por CLI
    optimizer = LayoutEngine(verbose=debug, visualdebug=visualdebug, strategy=forced,
                             visualize_growth=visualize_growth, **centrality_kwargs)

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

    # Mostrar resultados: §H6 tres contadores separados (no un único
    # 'colisiones' ambiguo) y con el nombre del motor real (no "AutoLayout"
    # cuando corrió hier/legacy).
    from AlmaGag.layout.metrics import (
        quality_counters, emission_metrics, INK_WARN_PCT, ASPECT_RANGE)
    q = quality_counters(optimized_layout)
    em = emission_metrics(optimized_layout)
    engine = getattr(optimizer, 'chosen', None) or resolved_strategy or 'auto'
    # §O52: la línea de métricas incluye densidad de tinta y aspecto de la
    # lámina estimada (bbox+margen, espejo del recorte §O51).
    # BUGS-LOG-001 (hallazgo del Skiller, v3.12): label_own_line se calculaba
    # (§H6/W87) pero jamás llegaba al log — «leer 4 contadores» era imposible
    # desde la línea de métricas. Se imprime como canal de diagnóstico; NO
    # suma al umbral de WARNING (decisión §H6: no es un solape de bboxes).
    line = (f"[{engine}] cruces(arista×arista)={q['edge_x_edge']} "
            f"arista×nodo={q['edge_x_node']} labels={q['label_overlap']} "
            f"own-line={q['label_own_line']} "
            f"tinta={em['ink_pct']:.1f}% aspecto={em['aspect']:.2f}")
    if q['edge_x_edge'] + q['edge_x_node'] + q['label_overlap'] > 0:
        logger.warning(line)
    else:
        logger.info(line)
    if em['ink_pct'] < INK_WARN_PCT:
        logger.warning(f"§O52: tinta {em['ink_pct']:.1f}% < {INK_WARN_PCT:.0f}% "
                       "— lámina mayormente vacía")
    if not (ASPECT_RANGE[0] <= em['aspect'] <= ASPECT_RANGE[1]):
        logger.warning(f"§O52: aspecto {em['aspect']:.2f} fuera de "
                       f"[{ASPECT_RANGE[0]}, {ASPECT_RANGE[1]}] — lámina "
                       "desproporcionada")

    logger.info(f"     - {num_levels} niveles, {num_groups} grupo(s)")
    logger.info(f"     - Prioridades: {high_priority} high, {normal_priority} normal, {low_priority} low")

    # 5. Obtener canvas final (puede haber sido expandido)
    final_canvas = optimized_layout.canvas
    if optimizer.chosen == 'hier':
        # hier ajusta su propio canvas al contenido (§G22/§J33): respetarlo tal
        # cual, sin inflarlo al canvas declarado (evita láminas medio vacías).
        canvas_width = final_canvas['width']
        canvas_height = final_canvas['height']
    elif final_canvas['width'] > canvas_width or final_canvas['height'] > canvas_height:
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
