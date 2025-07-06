import os, json, svgwrite
from AlmaGag.config import WIDTH, HEIGHT
from AlmaGag.draw.icons import draw_icon, draw_connection

def generate_diagram(json_file):
    if not os.path.exists(json_file):
        print(f"[ERROR] Archivo no encontrado: {json_file}")
        return

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Error al leer el JSON: {e}")
        return

    base_name = os.path.splitext(os.path.basename(json_file))[0]
    output_svg = f"{base_name}.svg"

    dwg = svgwrite.Drawing(output_svg, size=(WIDTH, HEIGHT))
    elements_by_id = {e['id']: e for e in data.get('elements', [])}

    for conn in data.get('connections', []):
        draw_connection(dwg, elements_by_id, conn)
    for elem in data.get('elements', []):
        draw_icon(dwg, elem)

    dwg.save()
    print(f"[OK] Diagrama generado exitosamente: {output_svg}")
