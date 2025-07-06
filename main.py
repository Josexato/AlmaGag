import sys
from AlmaGag.generator import generate_diagram

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python main.py archivo.json")
    else:
        generate_diagram(sys.argv[1])