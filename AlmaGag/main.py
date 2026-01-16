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
  almagag archivo.gag --debug                              # Texto de depuración
  almagag archivo.gag --visualdebug                        # Grilla y badge visual
  almagag archivo.gag --exportpng                          # Exportar a PNG
  almagag archivo.gag --debug --visualdebug --exportpng    # Todo habilitado
  almagag archivo.gag --debug --guide-lines 186 236        # Con líneas guía
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

    args = parser.parse_args()
    generate_diagram(
        args.input_file,
        debug=args.debug,
        visualdebug=args.visualdebug,
        exportpng=args.exportpng,
        guide_lines=args.guide_lines
    )


if __name__ == "__main__":
    main()