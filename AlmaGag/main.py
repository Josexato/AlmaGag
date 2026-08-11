import sys
import argparse
from AlmaGag.generator import generate_diagram


def main():
    """Punto de entrada CLI para AlmaGag."""
    parser = argparse.ArgumentParser(
        description="AlmaGag - Generador Automatico de Grafos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  almagag archivo.sdjf
  almagag archivo.sdjf --debug                                     # Texto de depuración
  almagag archivo.sdjf --visualdebug                               # Grilla y badge visual
  almagag archivo.sdjf --exportpng                                 # Exportar a PNG
  almagag archivo.sdjf -o docs/diagrams/svgs/diagram.svg           # Especificar salida
  almagag archivo.gag                                              # Formato .gag (con iconos SVG embebidos)
  almagag archivo.sdjf --debug --visualdebug --exportpng           # Todo habilitado
  almagag archivo.sdjf --debug --guide-lines 186 236               # Con líneas guía
  almagag archivo.sdjf --layout-algorithm=legacy --debug           # Motor histórico (ex-LAF)
  almagag archivo.sdjf --epifania                                 # Epifanía: flipbook del layout naciendo por fase
  almagag archivo.sdjf --layout-algorithm=legacy --epifania          # Epifanía de lujo (VC/centralidad, sólo legacy)
  almagag archivo.sdjf --layout-algorithm=hier                     # Forzar la estrategia de flujo
  python -m AlmaGag.main docs/diagrams/gags/05-arquitectura-gag.gag --debug --visualdebug
        """
    )
    parser.add_argument(
        "input_file",
        help="Archivo .sdjf o .gag de entrada (SDJF puro o con iconos embebidos)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa logs detallados del procesamiento (optimizacion, colisiones, decisiones)"
    )
    parser.add_argument(
        "--visualdebug",
        action="store_true",
        help="Activa elementos visuales de debug (grilla, franja de debug, badge)"
    )
    parser.add_argument(
        "--exportpng",
        action="store_true",
        help="Exporta el SVG generado a PNG en la carpeta debug/outputs/"
    )
    parser.add_argument(
        "--guide-lines",
        nargs='+',
        type=int,
        metavar='Y',
        help="Dibuja líneas horizontales de guía en las posiciones Y especificadas (ej: --guide-lines 186 236)"
    )
    parser.add_argument(
        "--dump-iterations",
        action="store_true",
        help="Guarda snapshots JSON de cada iteración del optimizador en debug/iterations/"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        metavar='FILE',
        help="Ruta de salida del archivo SVG (ej: -o docs/diagrams/svgs/diagram.svg). Si no se especifica, se genera en el directorio actual."
    )
    parser.add_argument(
        "--layout-algorithm",
        type=str,
        choices=['select', 'auto', 'hier', 'legacy'],
        default='select',
        help="Estrategia de layout. Default 'select': el motor elige a partir "
             "del JSON (un solo algoritmo, con AUTO como principal). Forzar una "
             "es avanzado/debug: 'auto' (principal, placement general), 'hier' "
             "(flujo dirigido A–J), 'legacy' (motor histórico ex-LAF, congelado)."
    )
    parser.add_argument(
        "--view",
        type=str,
        choices=['auto', 'columns', 'areas', 'lanes', 'matrix'],
        default='auto',
        help="Fuerza la REPRESENTACIÓN (solo por CLI, nunca por el JSON): "
             "'columns' (columnas del grafo dirigido), 'areas' (cajas por fase §I27), "
             "'lanes' (carriles por rol §I28), 'matrix' (fase×rol). "
             "'auto' (default) la decide el algoritmo a partir del JSON "
             "(areas si el archivo declara la metadata)."
    )
    parser.add_argument(
        "--epifania", "--debug-phases", "--visualize-growth",
        dest="visualize_growth",
        action="store_true",
        help="Epifanía — ver cómo NACE la abstracción del layout, paso a paso: un "
             "SVG por fase en debug/epifania/<diagrama>/ (+ index.html). Con "
             "auto/hier es un flipbook del layout real por etapa; con "
             "--layout-algorithm=legacy usa el analizador de lujo (VC/centralidad)."
    )
    parser.add_argument(
        "--color-connections",
        action="store_true",
        help="Colorea cada conexión con un color distinto para facilitar identificación visual"
    )
    parser.add_argument(
        "--centrality-alpha",
        type=float,
        default=None,
        metavar='F',
        help="Peso por distancia en skip connections (default: 0.15, solo LAF)"
    )
    parser.add_argument(
        "--centrality-beta",
        type=float,
        default=None,
        metavar='F',
        help="Peso por hijo extra / hub-ness (default: 0.10, solo LAF)"
    )
    parser.add_argument(
        "--centrality-gamma",
        type=float,
        default=None,
        metavar='F',
        help="Peso por fan-in extra (default: 0.15, 0=desactivado, solo LAF)"
    )
    parser.add_argument(
        "--centrality-max-score",
        type=float,
        default=None,
        metavar='F',
        help="Clamp maximo del score de accesibilidad (default: 100.0, solo LAF)"
    )

    args = parser.parse_args()

    # Construir dict de centralidad solo con los valores explícitos
    centrality_kwargs = {}
    if args.centrality_alpha is not None:
        centrality_kwargs['centrality_alpha'] = args.centrality_alpha
    if args.centrality_beta is not None:
        centrality_kwargs['centrality_beta'] = args.centrality_beta
    if args.centrality_gamma is not None:
        centrality_kwargs['centrality_gamma'] = args.centrality_gamma
    if args.centrality_max_score is not None:
        centrality_kwargs['centrality_max_score'] = args.centrality_max_score

    ok = generate_diagram(
        args.input_file,
        debug=args.debug,
        visualdebug=args.visualdebug,
        exportpng=args.exportpng,
        guide_lines=args.guide_lines,
        dump_iterations=args.dump_iterations,
        output_file=args.output,
        layout_algorithm=args.layout_algorithm,
        view=args.view,
        visualize_growth=args.visualize_growth,
        color_connections=args.color_connections,
        **centrality_kwargs
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
