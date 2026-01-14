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
  almagag archivo.gag --debug
  almagag archivo.gag --debug --guide-lines 186 236
  python -m AlmaGag.main examples/05-arquitectura-gag.gag --debug
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
        "--guide-lines",
        nargs='+',
        type=int,
        metavar='Y',
        help="Dibuja líneas horizontales de guía en las posiciones Y especificadas (ej: --guide-lines 186 236)"
    )

    args = parser.parse_args()
    generate_diagram(args.input_file, debug=args.debug, guide_lines=args.guide_lines)


if __name__ == "__main__":
    main()