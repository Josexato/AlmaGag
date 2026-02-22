"""
AlmaGag.utils

Funciones utilitarias compartidas por múltiples módulos del sistema.
"""

from AlmaGag.config import TEXT_CHAR_WIDTH, TEXT_LINE_HEIGHT


def extract_item_id(item):
    """
    Extrae el ID de un item que puede ser string o dict con campo 'id'.

    Los elementos en listas 'contains' pueden estar como:
      - string directo: "element_id"
      - dict con metadata: {"id": "element_id", "scope": "..."}

    Args:
        item: str o dict con campo 'id'

    Returns:
        str: El ID del elemento
    """
    return item['id'] if isinstance(item, dict) else item


def calculate_label_dimensions(label):
    """
    Calcula las dimensiones aproximadas de un label multilinea.

    Args:
        label: Texto del label (puede contener '\\n')

    Returns:
        tuple: (width, height, lines) donde:
            - width: ancho estimado en pixels
            - height: alto estimado en pixels
            - lines: lista de lineas del texto
    """
    lines = label.split('\n')
    width = max((len(line) for line in lines), default=0) * TEXT_CHAR_WIDTH
    height = len(lines) * TEXT_LINE_HEIGHT
    return width, height, lines
