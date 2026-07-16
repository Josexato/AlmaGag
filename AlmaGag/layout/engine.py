"""
LayoutEngine — el motor ÚNICO de AlmaGag (WISH-ARCH-002).

AlmaGag tiene un solo algoritmo desde el punto de vista del usuario: corre
`almagag archivo.json` y el motor elige la mejor representación a partir del
JSON. Internamente eso se resuelve delegando en una ESTRATEGIA de placement:

- `auto`  — placement general (Sugiyama + resolución de colisiones + contenedores).
            Es el motor base / caso por defecto.
- `hier`  — estrategia de FLUJO (pipeline plano por niveles/columnas, criterios
            A–J, y las vistas areas/lanes/matrix). Ya NO es un algoritmo peer:
            es la estrategia que el motor usa para flujos dirigidos.
- `laf`   — CONGELADA. Se conserva sólo como override de debug / lente de fases
            (`--layout-algorithm=laf`), no se elige nunca automáticamente.

La estrategia se decide en `generator.select_strategy(...)` a partir del JSON y
llega en `layout._strategy`; un override explícito por CLI la fuerza. Este
engine sólo orquesta: construye la estrategia elegida, delega `optimize()` y
expone su `renderer` para que el generator dibuje. La salida es idéntica a la de
correr esa estrategia directamente (fusión estructural, cero regresión).
"""

import importlib
import logging

logger = logging.getLogger('AlmaGag')


# Registro declarativo de estrategias del motor. `kind` documenta su rol:
#   base   — placement general (el motor por defecto)
#   flow   — flujo dirigido (niveles/columnas, criterios A–J, vistas)
#   frozen — congelada: sólo override de debug, nunca auto-elegida
# `extra=True` marca las que reciben kwargs adicionales (centralidad + fases).
_STRATEGIES = {
    'auto': {'cls': 'AlmaGag.layout.auto.optimizer.AutoLayoutOptimizer',            'kind': 'base'},
    'hier': {'cls': 'AlmaGag.layout.strategies.hier.optimizer.HierLayoutOptimizer', 'kind': 'flow'},
    'laf':  {'cls': 'AlmaGag.layout.laf.optimizer.LAFOptimizer',                    'kind': 'frozen', 'extra': True},
}


def _load(dotted):
    module, _, name = dotted.rpartition('.')
    return getattr(importlib.import_module(module), name)


class LayoutEngine:
    """Puerta única: elige la estrategia de placement y delega en ella."""

    def __init__(self, verbose: bool = False, visualdebug: bool = False,
                 strategy: str = None, visualize_growth: bool = False,
                 **centrality_kwargs):
        self.verbose = verbose
        self.visualdebug = visualdebug
        self._forced = strategy               # None → decidir desde layout._strategy
        self._visualize_growth = visualize_growth
        self._centrality_kwargs = centrality_kwargs
        self.renderer = None                  # se fija al delegar (para el generator)
        self.chosen = None

    def _build(self, name):
        """Instancia la estrategia del registro con SUS kwargs correctos."""
        spec = _STRATEGIES.get(name)
        if spec is None:
            raise ValueError(f"estrategia de layout desconocida: {name!r} "
                             f"(válidas: {sorted(_STRATEGIES)})")
        kwargs = {'verbose': self.verbose, 'visualdebug': self.visualdebug}
        if spec.get('extra'):     # sólo la estrategia congelada (laf) los acepta
            kwargs['visualize_growth'] = self._visualize_growth
            kwargs.update(self._centrality_kwargs)
        return _load(spec['cls'])(**kwargs)

    def optimize(self, layout, **kwargs):
        """Elige la estrategia (override CLI > `layout._strategy` > 'auto'),
        delega, y adopta su renderer. Devuelve el layout optimizado."""
        name = self._forced or getattr(layout, '_strategy', None) or 'auto'
        strategy = self._build(name)
        result = strategy.optimize(layout, **kwargs)
        self.renderer = strategy.renderer     # el generator hace engine.renderer.render(...)
        self.chosen = name
        if self.verbose:
            logger.debug(f"[ENGINE] estrategia '{name}' → "
                         f"{type(strategy).__name__}")
        return result
