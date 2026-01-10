import sys
from AlmaGag.generator import generate_diagram


def main():
    """Punto de entrada CLI para AlmaGag."""
    if len(sys.argv) != 2:
        print("Uso: almagag archivo.gag")
        print("     python -m AlmaGag.main archivo.gag")
        print("\nEjemplos:")
        print("  almagag roadmap-25-06-22.gag")
        print("  almagag docs/examples/05-arquitectura-gag.gag")
    else:
        generate_diagram(sys.argv[1])


if __name__ == "__main__":
    main()