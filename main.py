import sys
from AlmaGag.generator import generate_diagram

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m AlmaGag.main archivo.gag")
        print("\nEjemplos:")
        print("  python -m AlmaGag.main roadmap-25-06-22.gag")
        print("  python -m AlmaGag.main data/primos.gag")
    else:
        generate_diagram(sys.argv[1])