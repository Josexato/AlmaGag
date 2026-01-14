# AlmaGag - Generador Automático de Grafos

**Proyecto**: ALMA (Almas y Sentidos)
**Módulo**: GAG - Intérprete de sentidos para Funes
**Versión**: v3.0.0 + SDJF v3.0

---

AlmaGag es un generador de diagramas SVG que transforma archivos JSON (formato SDJF) en gráficos vectoriales mediante auto-layout jerárquico inteligente con optimización de colisiones de etiquetas.

## 🚀 Inicio Rápido

### Instalación

```bash
cd AlmaGag
pip install -e .
```

### Uso

```bash
almagag mi-diagrama.gag
```

### Ejemplo Mínimo

Crear `ejemplo.gag`:

```json
{
  "elements": [
    {
      "id": "api",
      "type": "server",
      "label": "REST API",
      "label_priority": "high",
      "hp": 2.0,
      "color": "gold"
    },
    {
      "id": "db",
      "type": "building",
      "label": "Database",
      "label_priority": "high",
      "hp": 1.8,
      "color": "orange"
    },
    {
      "id": "cache",
      "type": "cloud",
      "label": "Redis",
      "color": "cyan"
    }
  ],
  "connections": [
    {
      "from": "api",
      "to": "db",
      "routing": {"type": "orthogonal"},
      "label": "SQL",
      "direction": "forward"
    },
    {
      "from": "api",
      "to": "cache",
      "routing": {"type": "bezier", "curvature": 0.5},
      "label": "get/set",
      "direction": "bidirectional"
    }
  ]
}
```

Generar:

```bash
almagag ejemplo.gag
```

**Resultado**: `ejemplo.svg` con auto-layout inteligente, sin coordenadas manuales.

---

## ✨ Características Principales

### SDJF v3.0 ✨ NUEVO

- **✅ Layout Jerárquico**: Posicionamiento basado en topología de grafos (BFS)
- **✅ Optimización de Colisiones de Etiquetas**: Sistema inteligente de posicionamiento
  - Generación de posiciones candidatas (8 para conexiones, 3 para contenedores)
  - Scoring basado en colisiones y legibilidad
  - Algoritmo greedy con prioridades
- **✅ Detección Avanzada de Colisiones**: Etiqueta-elemento y etiqueta-etiqueta
- **✅ Debug Automatizado**: Conversión SVG→PNG con Chrome headless

### SDJF v2.1

- **✅ Routing Declarativo**: 5 tipos de líneas sin waypoints manuales
  - `straight`: Líneas rectas (default)
  - `orthogonal`: Líneas H-V o V-H (arquitectura)
  - `bezier`: Curvas suaves (flujos)
  - `arc`: Arcos circulares (self-loops)
  - `manual`: Waypoints explícitos (v1.5 compatible)
- **✅ Auto-waypoints**: Calculados automáticamente después de posicionamiento
- **✅ Corner Radius**: Esquinas redondeadas preparadas

### SDJF v2.0

- **✅ Coordenadas Opcionales**: Auto-layout calcula posiciones automáticamente
- **✅ Sizing Proporcional**: `hp` y `wp` para escalar elementos
- **✅ Prioridades Inteligentes**: HIGH → centro, NORMAL → alrededor, LOW → periferia
- **✅ Weight-Based Optimization**: Elementos grandes resisten movimiento

### SDJF v1.5

- **✅ Contenedores**: Agrupación visual de elementos con `contains`

### SDJF v1.0

- **✅ 4 Tipos de Íconos**: server, building, cloud, firewall
- **✅ Gradientes Automáticos**: Colores CSS y hexadecimales
- **✅ 4 Direcciones de Flechas**: forward, backward, bidirectional, none
- **✅ Fallback BWT**: Banana With Tape para tipos desconocidos

---

## 📖 Documentación Completa

### Especificaciones del Estándar SDJF

- **[SDJF v1.0](docs/spec/SDJF_v1.0_SPEC.md)** - Especificación base
- **[SDJF v2.0](docs/spec/SDJF_v2.0_SPEC.md)** - Coordenadas opcionales + Sizing proporcional
- **[SDJF v2.1](docs/spec/SDJF_v2.1_PROPOSAL.md)** - Routing declarativo + Waypoints automáticos
- **[SDJF v3.0](docs/RELEASE_v3.0.0.md)** - ✅ Layout jerárquico + Optimización de etiquetas

### Guías de Uso

- **[Quickstart](docs/guides/QUICKSTART.md)** - Instalación y primer diagrama
- **[Galería de Ejemplos](docs/guides/EXAMPLES.md)** - 10 ejemplos con explicaciones

### Arquitectura del Código

- **[Arquitectura](docs/architecture/ARCHITECTURE.md)** - Diseño modular y patrones
- **[Evolución](docs/architecture/EVOLUTION.md)** - Historia de versiones

---

## 🎨 Ejemplos

Ver carpeta [`examples/`](examples/) con 11 ejemplos `.gag`:

| Ejemplo | Descripción |
|---------|-------------|
| 01-iconos-registrados | Tipos de íconos disponibles |
| 02-iconos-no-registrados | Fallback BWT |
| 03-conexiones | Direcciones de flechas |
| 04-gradientes-colores | Sistema de colores |
| 05-arquitectura-gag | Diagrama complejo v3.0 (auto-documentación) |
| 06-waypoints | Routing con puntos intermedios |
| 07-containers | Contenedores y agrupación |
| 08-auto-layout | Auto-layout completo (sin coordenadas) |
| 09-proportional-sizing | Sizing proporcional (hp/wp) |
| 10-hybrid-layout | Híbrido: auto + manual + prioridades |
| continentes-america | Ejemplo complejo con múltiples contenedores |

```bash
# Generar ejemplos
almagag examples/08-auto-layout.gag
almagag examples/05-arquitectura-gag.gag
```

Ver [`examples/README.md`](examples/README.md) para más detalles.

---

## 🏗️ Arquitectura

![Arquitectura de GAG](docs/diagrams/svgs/05-arquitectura-gag.svg)

**Flujo de ejecución:**

```
archivo.gag (JSON SDJF v3.0)
    ↓
AlmaGag.main (CLI)
    ↓
AlmaGag.generator (Orquestador)
    ├─ Layout (patrón inmutable)
    ├─ AutoLayoutOptimizer v3.0 Jerárquico
    │   ├─ GraphAnalyzer: topología (niveles, grupos)
    │   ├─ AutoLayoutPositioner: layout jerárquico
    │   ├─ RouterManager: rutas de conexiones (v2.1)
    │   ├─ CollisionDetector: detección de colisiones
    │   └─ Iterative optimization (10 iteraciones)
    ├─ LabelPositionOptimizer v3.0
    │   ├─ Generación de posiciones candidatas
    │   ├─ Scoring basado en colisiones
    │   └─ Asignación greedy por prioridad
    ├─ SVG canvas + markers
    └─ Render (contenedores → shapes → lines → labels)
    ↓
archivo.svg + PNG debug
```

**Módulos principales:**

- `AlmaGag/layout/` - Layout inmutable + Optimización jerárquica (v3.0)
- `AlmaGag/routing/` - Sistema de routing declarativo (5 tipos)
- `AlmaGag/draw/` - Renderizado SVG (íconos, conexiones, contenedores)

Ver [documentación completa de arquitectura](docs/architecture/ARCHITECTURE.md).

---

## 🛠️ Desarrollo

### Estructura del Proyecto

```
AlmaGag/
├── AlmaGag/                  # 📦 Source code (paquete Python)
│   ├── main.py               # CLI entry point
│   ├── generator.py          # Orquestador
│   ├── config.py             # Constantes globales
│   ├── debug.py              # Utilities de debug (SVG→PNG)
│   ├── layout/               # Módulo de Layout (v3.0)
│   │   ├── layout.py         # Clase Layout (inmutable)
│   │   ├── auto_optimizer.py # AutoLayoutOptimizer v3.0
│   │   ├── auto_positioner.py # Posicionamiento jerárquico
│   │   ├── sizing.py         # SizingCalculator (hp/wp)
│   │   ├── geometry.py       # GeometryCalculator + colisiones
│   │   ├── collision.py      # CollisionDetector
│   │   ├── graph_analysis.py # GraphAnalyzer (topología)
│   │   ├── label_optimizer.py # LabelPositionOptimizer v3.0
│   │   ├── container_calculator.py # Cálculo de contenedores
│   │   └── optimizer_base.py # Base classes
│   ├── routing/              # Sistema de routing (v2.1)
│   │   ├── router_manager.py # Coordinador de routers
│   │   ├── router_base.py    # Base: ConnectionRouter, Path
│   │   ├── straight_router.py # Líneas rectas
│   │   ├── orthogonal_router.py # Líneas H-V/V-H
│   │   ├── bezier_router.py  # Curvas Bézier
│   │   ├── arc_router.py     # Arcos circulares
│   │   └── manual_router.py  # Waypoints manuales
│   └── draw/                 # Módulo de renderizado
│       ├── icons.py          # Dispatcher + gradientes
│       ├── connections.py    # Líneas + routing types
│       ├── container.py      # Contenedores (v1.5)
│       ├── server.py, building.py, cloud.py, firewall.py
│       └── bwt.py            # Banana With Tape (fallback)
│
├── docs/                     # 📚 Documentación
│   ├── INDEX.md              # Índice de documentación
│   ├── CHANGELOG.md          # Historial de cambios
│   ├── RELEASE_v3.0.0.md     # Release notes v3.0
│   ├── guides/               # Guías de usuario
│   │   ├── QUICKSTART.md
│   │   └── EXAMPLES.md
│   ├── spec/                 # Especificaciones SDJF
│   │   ├── SDJF_v1.0_SPEC.md, v2.0, v2.1
│   │   ├── SVG_TO_BWT_SPEC.md
│   │   └── CONTAINER_GROUPING_STRATEGY.md
│   ├── architecture/         # Arquitectura del código
│   │   ├── ARCHITECTURE.md
│   │   ├── EVOLUTION.md
│   │   └── SDJF_v2.1_IMPLEMENTATION_SUMMARY.md
│   └── diagrams/             # Diagramas de arquitectura interna
│       ├── roadmap-versions.gag
│       ├── routing-architecture.gag
│       ├── svg-to-bwt-flow.gag
│       └── outputs/          # SVGs generados
│
├── examples/                 # 🎨 Ejemplos (11 archivos .gag)
│   ├── README.md             # Catálogo de ejemplos
│   ├── 01-iconos-registrados.gag
│   ├── 05-arquitectura-gag.gag
│   └── ...
│
├── tests/                    # 🧪 Tests
│   ├── README.md
│   ├── __init__.py
│   ├── fixtures/             # Test .gag files
│   ├── unit/                 # Unit tests (futuro)
│   └── legacy/data/          # Datos históricos
│
├── debug/                    # 🐛 Debug outputs
│   ├── README.md
│   ├── notes/                # Notas de debug
│   ├── outputs/              # PNG/SVG generados (gitignored)
│   └── screenshots/          # Screenshots de documentación
│
├── scripts/                  # 🔧 Utility scripts
│   └── legacy/               # Scripts deprecated
│
├── pyproject.toml            # Configuración del paquete
├── requirements.txt
├── .gitignore
└── README.md
```

### Extensibilidad

**Agregar nuevo tipo de ícono:**

1. Crear `draw/mi_icono.py`:

```python
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient

def draw_mi_icono(dwg, x, y, color, element_id):
    fill = create_gradient(dwg, element_id, color)
    dwg.add(dwg.circle(center=(x + ICON_WIDTH/2, y + ICON_HEIGHT/2),
                       r=25, fill=fill, stroke='black'))
```

2. Usar en SDJF:

```json
{
  "id": "elem1",
  "type": "mi_icono",
  "label": "Custom Icon"
}
```

No requiere modificar código existente (dynamic import).

---

## 🗺️ Roadmap

### ✅ v3.0 - Layout Jerárquico + Optimización de Etiquetas (Implementado)

- **✅ Layout jerárquico**: Posicionamiento basado en topología de grafos (BFS)
- **✅ Label collision optimizer**: Sistema inteligente de posicionamiento de etiquetas
- **✅ Detección avanzada de colisiones**: Etiqueta-elemento y etiqueta-etiqueta
- **✅ Debug automatizado**: PNG generation con Chrome headless
- **✅ Reorganización completa**: Estructura de repositorio profesional

Ver [release notes v3.0.0](docs/RELEASE_v3.0.0.md) y [CHANGELOG](docs/CHANGELOG.md).

### ✅ v2.1 - Routing Declarativo (Implementado)

- **✅ Routing declarativo**: `{"routing": {"type": "orthogonal"}}`
- **✅ 5 tipos de líneas**: `straight`, `orthogonal`, `bezier`, `arc`, `manual`
- **✅ Auto-waypoints**: Calculados después de posicionamiento

Ver [especificación completa](docs/spec/SDJF_v2.1_PROPOSAL.md) y [resumen de implementación](docs/architecture/SDJF_v2.1_IMPLEMENTATION_SUMMARY.md).

### v3.1 (Próximo) - Smart Routing

- **Avoid elements**: Routing inteligente evitando colisiones con A*
- **Corner radius avanzado**: SVG path smoothing completo
- **Smart routing**: Preferencias automáticas según tipos de elementos
- **Unit tests**: Suite completa de tests automatizados

### Futuro

- ~~Autolayout~~ ✅ Implementado v2.0
- ~~Routing declarativo~~ ✅ Implementado v2.1
- ~~Layout jerárquico~~ ✅ Implementado v3.0
- ~~Label collision optimizer~~ ✅ Implementado v3.0
- Temas predefinidos (Cloud, Tech, Minimal)
- Animación SVG (timeline de aparición)
- Íconos SVG externos personalizados

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.

Copyright © 2025 José Cáceres - ALMA (Almas y Sentidos)

---

## 🤝 Contribuir

Este proyecto es parte de ALMA. Para reportar bugs o sugerir mejoras, abre un issue en el repositorio.

---

## 📚 Enlaces Rápidos

| Recurso | Enlace |
|---------|--------|
| Guía de inicio | [docs/guides/QUICKSTART.md](docs/guides/QUICKSTART.md) |
| Especificación v2.0 | [docs/spec/SDJF_v2.0_SPEC.md](docs/spec/SDJF_v2.0_SPEC.md) |
| Galería de ejemplos | [docs/guides/EXAMPLES.md](docs/guides/EXAMPLES.md) |
| Arquitectura | [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) |
| Propuesta v2.1 | [docs/spec/SDJF_v2.1_PROPOSAL.md](docs/spec/SDJF_v2.1_PROPOSAL.md) |

---

**AlmaGag** - Generación automática de diagramas con layout jerárquico inteligente y optimización de etiquetas
**Versión**: v3.0.0 + SDJF v3.0 | **Actualizado**: 2026-01-10
