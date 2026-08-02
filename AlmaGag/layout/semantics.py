"""
§Q63 — `semantic_type` declarado; inferencia sólo con el mapa DEL ARCHIVO.

Regla de frontera (§R, refinada por el autor): el vocabulario que conecta
texto de labels con clases semánticas NUNCA vive en el código de AlmaGag —
sería el motor cargando juicio editorial (y un idioma, y un dominio). El
vocabulario viaja:

1. **Declarado** (camino preferido): cada conexión trae `semantic_type`;
   el motor pinta y arma la leyenda §N48. Cero inferencia.
2. **Mapa embebido** (camino opcional): el archivo carga su propia sección
   `semantics` — igual que los iconos `icons{}` — y el motor la aplica
   MECÁNICAMENTE, avisando (nunca en silencio) y sin pisar lo declarado.
   Sin match → clase neutra (el motor no adivina).

Formato de la sección (dos formas por clase):

    "semantics": {
      "transporte": {"keywords": ["FO", "MW", "Mbps"], "color": "#1f6fd0"},
      "soporte":    ["soporte", "reposicion", "FAT"]
    }

Match: subcadena, case-insensitive, contra el label completo de la
conexión. La primera clase que matchea (orden de aparición en el archivo)
gana. `color` es opcional y respeta un `color` ya presente en la conexión;
puede ser un token del `theme` §O57 (esta pasada corre antes que el tema).
"""

import logging

logger = logging.getLogger('AlmaGag')


def apply_embedded_semantics(data) -> int:
    """Aplica la sección `semantics` del archivo a las conexiones sin
    `semantic_type`. Devuelve cuántas conexiones se clasificaron. Muta
    `data` in-place. Sin sección (o vacía) es un no-op silencioso."""
    spec = data.get('semantics')
    if not isinstance(spec, dict) or not spec:
        return 0

    classes = []
    for name, val in spec.items():
        if isinstance(val, dict):
            keywords = val.get('keywords', [])
            color = val.get('color')
        else:
            keywords, color = val, None
        keywords = [str(k).lower() for k in keywords if k]
        if keywords:
            classes.append((name, keywords, color))
    if not classes:
        return 0

    n = 0
    for conn in data.get('connections', []):
        if conn.get('semantic_type'):
            continue                      # lo declarado JAMÁS se pisa
        label = str(conn.get('label', '')).lower()
        if not label:
            continue
        for name, keywords, color in classes:
            if any(k in label for k in keywords):
                conn['semantic_type'] = name
                if color and not conn.get('color'):
                    conn['color'] = color
                n += 1
                break                     # sin match → neutra, no se adivina

    if n:
        logger.warning(f"§Q63 [semantic]: {n} enlace(s) con semantic_type "
                       f"inferido del label vía el mapa `semantics` del "
                       f"archivo — declararlo explícito es lo correcto")
    return n
