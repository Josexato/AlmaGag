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
  almagag archivo.gag
  almagag archivo.gag --debug                                      # Texto de depuración
  almagag archivo.gag --visualdebug                                # Grilla y badge visual
  almagag archivo.gag --exportpng                                  # Exportar a PNG
  almagag archivo.gag -o docs/diagrams/svgs/diagram.svg            # Especificar salida
  almagag archivo.gag -o output/diagram.svg --exportpng            # Salida + PNG
  almagag archivo.gag --debug --visualdebug --exportpng            # Todo habilitado
  almagag archivo.gag --debug --guide-lines 186 236                # Con líneas guía
  almagag archivo.gag --layout-algorithm=laf --debug               # Usar LAF (minimiza cruces)
  almagag archivo.gag --layout-algorithm=laf --visualize-growth    # LAF + visualización de fases
  python -m AlmaGag.main examples/05-arquitectura-gag.gag --debug --visualdebug
        """
    )
    parser.add_argument(
        "input_file",
        help="Archivo .gag (JSON SDJF) de entrada"
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
        choices=['auto', 'laf'],
        default='auto',
        help="Algoritmo de layout: 'auto' (sistema actual) o 'laf' (Layout Abstracto Primero - minimiza cruces)"
    )
    parser.add_argument(
        "--visualize-growth",
        action="store_true",
        help="Genera SVGs de cada fase del proceso LAF (solo con --layout-algorithm=laf)"
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
        visualize_growth=args.visualize_growth,
        **centrality_kwargs
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
