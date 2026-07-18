# SDJF · Tipo `union` (punto de unión / matrimonio) — §H7

## Motivación
Cuando dos progenitores comparten muchos hijos, declararlos con **dos aristas
por hijo** produce un abanico doble cruzado (10 diagonales para 5 hijos): el
layout es correcto pero ruidoso. La notación genealógica clásica lo resuelve
uniendo a los dos padres por una **barra** y bajando **un solo tronco por hijo**
desde el punto de unión.

## Sintaxis
Se declara un arreglo `unions` a nivel raíz del SDJF, y las conexiones a los
hijos salen del `id` de la unión:

```json
{
  "unions": [
    { "id": "u1", "between": ["jose_heraclides", "daria"] }
  ],
  "connections": [
    { "from": "u1", "to": "silvia",   "direction": "forward" },
    { "from": "u1", "to": "lica",     "direction": "forward" }
  ]
}
```

- `id`: identificador del punto de unión (referenciable como `from`/`to`).
- `between`: los dos (o más) `id` de elementos progenitores.

## Semántica
`expand_unions` (en `AlmaGag/layout/unions.py`) traduce cada `union`, **antes**
del layout, a:

1. un **nodo sintético** `id` de tipo `union`, que se dibuja como una barra
   corta y discreta (no un icono grande);
2. una **arista de barra** `progenitor → union` por cada elemento de `between`.

El resto del motor lo trata como un nodo normal: el layout lo coloca por
baricentro entre los padres y los hijos cuelgan de él. Así **10 aristas se
vuelven 5 (+1 barra)** y desaparece el abanico cruzado.

## Compatibilidad
- Retrocompatible: sin `unions`, no cambia nada.
- Idempotente: los nodos/aristas creados se marcan (`_union`, `_union_bar`) para
  no duplicarse en una segunda pasada.
- Funciona con el motor `auto` (y con cualquier motor que posicione por grafo).

## Verificación
`11-stresstest.sdjf` (árbol genealógico) reescrito con `union` rinde
`edge_x_edge = 0` (antes, con el abanico doble, cruces > 0). Ver
`tests/test_union.py`.

## Detección sugerida (futuro)
El clasificador de templates podría **sugerir** una unión cuando detecte el
patrón "dos nodos comparten ≥3 destinos idénticos" — aviso en log, sin
transformar automáticamente (respeta que la intención la declara el autor).
