# Índice de Documentación - AlmaGag

**Versión**: v3.3.0 (código) + SDJF v2.1 (estándar)
**Actualizado**: 2026-02-28

---

## 📚 Documentación Completa

Esta es la guía completa de documentación de AlmaGag, organizada por tipo de documento.

---

## 🚀 Inicio Rápido

**Para usuarios nuevos:**

1. **[README.md](../README.md)** - Visión general y ejemplo mínimo
2. **[Quickstart Guide](guides/QUICKSTART.md)** - Instalación paso a paso
3. **[Galería de Ejemplos](guides/EXAMPLES.md)** - 10 ejemplos visuales

**Para entender el vocabulario:**

- **[CONCEPTS.md](CONCEPTS.md)** ✨ - Glosario unificado (SDJF, GAG, AUTO, LAF, NdDp, NdPr, NdFn, TOI, BWT, Routing Policy)

---

## 📖 Especificaciones del Estándar SDJF

**Formato de archivo `.gag` (JSON)**

### Versiones del Estándar

| Documento | Versión | Estado | Descripción |
|-----------|---------|--------|-------------|
| [SDJF v1.0](spec/SDJF_v1.0_SPEC.md) | 1.0 | ✅ Estable | Especificación base (coordenadas requeridas) |
| [SDJF v2.0](spec/SDJF_v2.0_SPEC.md) | 2.0 | ✅ Estable | Auto-layout + sizing proporcional |
| [SDJF v2.0 Features](spec/SDJF_v2.0_FEATURES.md) | 2.0 | ✅ Referencia | Documento original de features v2.0 |
| [SDJF v2.1](spec/SDJF_v2.1_PROPOSAL.md) | 2.1 | ✅ Implementado | Routing declarativo + waypoints automáticos |

### ¿Qué versión debo usar?

- **Empezando**: Lee [v1.0](spec/SDJF_v1.0_SPEC.md) para entender la base
- **Auto-layout**: Lee [v2.0](spec/SDJF_v2.0_SPEC.md) para coordenadas opcionales
- **Routing declarativo**: Lee [v2.1](spec/SDJF_v2.1_PROPOSAL.md) para 5 tipos de líneas

---

## 🎨 Guías de Uso

**Para aprender a usar AlmaGag**

| Documento | Nivel | Descripción |
|-----------|-------|-------------|
| [Quickstart](guides/QUICKSTART.md) | Principiante | Instalación y primer diagrama |
| [Galería de Ejemplos](guides/EXAMPLES.md) | Todos | 10 ejemplos con explicaciones |

### Temas por Feature

- **Íconos y colores** → [Ejemplos 01-04](guides/EXAMPLES.md#01---iconos-registrados)
- **Conexiones y flechas** → [Ejemplo 03](guides/EXAMPLES.md#03---tipos-de-conexiones)
- **Waypoints** → [Ejemplo 06](guides/EXAMPLES.md#06---waypoints-sdjf-v15)
- **Contenedores** → [Ejemplo 07](guides/EXAMPLES.md#07---contenedores-sdjf-v20)
- **Auto-layout** → [Ejemplo 08](guides/EXAMPLES.md#08---auto-layout-completo-sdjf-v20)
- **Sizing proporcional** → [Ejemplo 09](guides/EXAMPLES.md#09---sizing-proporcional-sdjf-v20)
- **Layout híbrido** → [Ejemplo 10](guides/EXAMPLES.md#10---layout-híbrido-sdjf-v20)

---

## 🧠 Algoritmos de Layout

**Para elegir entre AUTO y LAF** ✨ NUEVO v3.0

| Documento | Nivel | Descripción |
|-----------|-------|-------------|
| [Guía de Decisión](guides/LAYOUT-DECISION-GUIDE.md) | Todos | ¿Cuándo usar AUTO vs LAF? Árbol de decisión simple |
| [Módulo `layout/`](architecture/modules/layout/README.md) ✨ | Desarrolladores | README de la capa: decisión arquitectónica + tabla AUTO/LAF |
| [AUTO en detalle](architecture/modules/layout/auto/AUTO.md) ✨ | Desarrolladores | Algoritmo AUTO: pipeline, coords manuales, workaround Dashboard |
| [LAF en detalle](architecture/modules/layout/laf/LAF.md) ✨ | Desarrolladores | Algoritmo LAF: 11 fases, hiperparámetros, limitaciones |
| [Biblioteca routing](architecture/modules/routing/ROUTING.md) ✨ | Desarrolladores | 5 tipos declarativos: straight, orthogonal, bezier, arc, manual |
| [Comparación Técnica LAF](architecture/modules/layout/laf/COMPARISON.md) | Avanzado | Análisis profundo con métricas y benchmarks |
| [Progreso LAF](architecture/modules/layout/laf/PROGRESS.md) | Técnico | Historia de desarrollo en 8 sprints |
| [Referencia CLI](guides/CLI-REFERENCE.md) | Todos | Documentación completa de opciones de línea de comandos |

### ¿Cuándo usar qué?

#### Usa AUTO cuando:
- Diagrama simple (<10 elementos)
- Necesitas preservar coordenadas x,y manuales
- Prototipado rápido
- Pocas conexiones (<10)

```bash
almagag diagrama.gag
# o explícitamente:
almagag diagrama.gag --layout-algorithm=auto
```

#### Usa LAF cuando:
- Diagrama complejo (>20 elementos)
- Contenedores anidados (3+ niveles)
- Muchas conexiones (>20)
- Minimizar cruces es crítico
- Producción / Presentaciones

```bash
almagag diagrama.gag --layout-algorithm=laf
```

**Quick Start LAF**:
```bash
# Generar con LAF
almagag arquitectura.gag --layout-algorithm=laf --exportpng

# Ver proceso LAF paso a paso
almagag complejo.gag --layout-algorithm=laf --visualize-growth

# Debug LAF completo
almagag arch.gag --layout-algorithm=laf --debug --dump-iterations
```

**Mejoras de LAF vs AUTO**: -87% cruces, -24% colisiones, -80% routing calls, -87% expansiones canvas

---

## 🏗️ Arquitectura del Código

**Para desarrolladores contribuyendo al proyecto**

| Documento | Audiencia | Descripción |
|-----------|-----------|-------------|
| [Architecture](architecture/ARCHITECTURE.md) | Desarrolladores | Diseño modular completo |
| [Evolution](architecture/EVOLUTION.md) | Todos | Historia de versiones |
| [Implementation Strategy](architecture/IMPLEMENTATION_STRATEGY.md) | Implementadores | Guía técnica v2.1 |

### Diagramas de Arquitectura

- **[Arquitectura actual](diagrams/svgs/05-arquitectura-gag.svg)** - Flujo de ejecución v2.1
- **[Historia de arquitecturas](architecture/history/)** - Versiones anteriores

---

## 🗺️ Roadmap y Planificación

**Para entender la dirección del proyecto**

| Documento | Descripción |
|-----------|-------------|
| [ROADMAP.md](ROADMAP.md) | Plan completo de desarrollo |
| [Diagrama de Roadmap](diagrams/svgs/roadmap-versions.svg) | Visualización de versiones |
| [Arquitectura v2.1](diagrams/svgs/routing-architecture.svg) | Diseño del módulo routing |

### Resumen del Roadmap

- **✅ Completado**: v1.0, v1.5, v2.0, v2.1 (código y estándar)
- **🔄 En desarrollo**: v2.2 (collision avoidance)
- **📅 Planificado**: v2.3 (optimizaciones avanzadas), v3.0 (temas)

---

## 📂 Estructura de Documentación

```
docs/
├── INDEX.md                      # Este archivo
├── CONCEPTS.md                   # ✨ Glosario unificado (punto de entrada conceptual)
├── ROADMAP.md                    # Plan de desarrollo
├── TECHNICAL_DEBT.md             # Deuda técnica conocida (LAF-001..LAF-009)
├── DIAGRAM_REVIEW.md             # Revisión visual de diagramas (DIAG-001+)
│
├── spec/                         # Especificaciones SDJF
│   ├── SDJF_v1.0_SPEC.md
│   ├── SDJF_v2.0_SPEC.md
│   ├── SDJF_v2.0_FEATURES.md
│   └── SDJF_v2.1_PROPOSAL.md
│
├── guides/                       # Guías de uso
│   ├── QUICKSTART.md
│   ├── EXAMPLES.md
│   ├── CLI-REFERENCE.md          # Referencia completa CLI
│   └── LAYOUT-DECISION-GUIDE.md  # Guía de decisión AUTO vs LAF
│
├── architecture/                 # Arquitectura del código
│   ├── ARCHITECTURE.md           # Visión general del sistema
│   ├── EVOLUTION.md              # Historial de evolución
│   ├── IMPLEMENTATION_STRATEGY.md
│   ├── modules/                  # ✨ Docs por módulo
│   │   ├── layout/
│   │   │   ├── README.md         # Decisión arquitectónica + tabla AUTO/LAF
│   │   │   ├── auto/
│   │   │   │   ├── AUTO.md       # Algoritmo AUTO en detalle
│   │   │   │   └── routing.md    # AutoRoutingPolicy
│   │   │   └── laf/
│   │   │       ├── LAF.md        # Algoritmo LAF (11 fases)
│   │   │       ├── routing.md    # LAFRoutingPolicy
│   │   │       ├── PROGRESS.md   # Historia de desarrollo LAF
│   │   │       └── COMPARISON.md # Comparación LAF vs AUTO
│   │   └── routing/
│   │       └── ROUTING.md        # Biblioteca compartida (5 routers)
│   └── history/                  # Diagramas históricos
│
└── diagrams/                     # Diagramas y ejemplos visuales
    ├── gags/                     # Archivos fuente .gag
    │   ├── 01-iconos-registrados.gag
    │   ├── 02-iconos-no-registrados.gag
    │   ├── 03-conexiones.gag
    │   ├── 04-gradientes-colores.gag
    │   ├── 05-arquitectura-gag.gag  # ✨ Actualizado con componentes LAF
    │   ├── 06-waypoints.gag
    │   ├── 07-containers.gag
    │   ├── 08-auto-layout.gag
    │   ├── 09-proportional-sizing.gag
    │   ├── 10-hybrid-layout.gag
    │   ├── execution-flow.gag
    │   ├── layout-optimization-flow.gag
    │   ├── roadmap-versions.gag
    │   ├── routing-architecture.gag
    │   └── system-architecture.gag
    └── svgs/                     # SVG generados
        ├── 01-iconos-registrados.svg
        ├── 02-iconos-no-registrados.svg
        ├── 03-conexiones.svg
        ├── 04-gradientes-colores.svg
        ├── 05-arquitectura-gag.svg   # ✨ Regenerado con LAF
        ├── 06-waypoints.svg
        ├── 07-containers.svg
        ├── 08-auto-layout.svg
        ├── 09-proportional-sizing.svg
        ├── 10-hybrid-layout.svg
        ├── execution-flow.svg
        ├── layout-optimization-flow.svg
        ├── roadmap-versions.svg
        ├── routing-architecture.svg
        └── system-architecture.svg
```

---

## 🎯 Rutas de Aprendizaje

### Ruta 1: Usuario Nuevo

1. [README.md](../README.md) - Visión general
2. [Quickstart](guides/QUICKSTART.md) - Instalación
3. [SDJF v1.0](spec/SDJF_v1.0_SPEC.md) - Formato básico
4. [Galería](guides/EXAMPLES.md) - Ejemplos visuales
5. [SDJF v2.0](spec/SDJF_v2.0_SPEC.md) - Features avanzados

### Ruta 2: Desarrollador Contribuyente

1. [README.md](../README.md) - Contexto
2. [Architecture](architecture/ARCHITECTURE.md) - Diseño del sistema
3. [ROADMAP.md](ROADMAP.md) - Plan de desarrollo
4. [Implementation Strategy](architecture/IMPLEMENTATION_STRATEGY.md) - Guía técnica
5. Código fuente en `AlmaGag/`

### Ruta 3: Implementador v2.1

1. [SDJF v2.1 Proposal](spec/SDJF_v2.1_PROPOSAL.md) - Qué implementar
2. [ROADMAP.md](ROADMAP.md) - Timeline y fases
3. [Implementation Strategy](architecture/IMPLEMENTATION_STRATEGY.md) - Cómo implementar
4. [Architecture](architecture/ARCHITECTURE.md) - Dónde integrar
5. Comenzar con Fase 1

---

## 🔍 Búsqueda Rápida

### Por Concepto

- **Auto-layout**: [v2.0 Spec](spec/SDJF_v2.0_SPEC.md), [Ejemplo 08](guides/EXAMPLES.md#08---auto-layout-completo-sdjf-v20)
- **Sizing (hp/wp)**: [v2.0 Spec](spec/SDJF_v2.0_SPEC.md#proportional-sizing), [Ejemplo 09](guides/EXAMPLES.md#09---sizing-proporcional-sdjf-v20)
- **Waypoints**: [v1.5 Info](spec/SDJF_v1.0_SPEC.md#waypoints), [v2.1 Proposal](spec/SDJF_v2.1_PROPOSAL.md)
- **Routing**: [v2.1 Proposal](spec/SDJF_v2.1_PROPOSAL.md)
- **Contenedores**: [Ejemplo 07](guides/EXAMPLES.md#07---contenedores-sdjf-v20)
- **Prioridades**: [v2.0 Spec](spec/SDJF_v2.0_SPEC.md#auto-layout)

### Por Pregunta

- **¿Cómo instalo?** → [Quickstart](guides/QUICKSTART.md#instalación)
- **¿Cómo hago mi primer diagrama?** → [Quickstart](guides/QUICKSTART.md#primer-diagrama)
- **¿Qué tipos de íconos hay?** → [SDJF v1.0](spec/SDJF_v1.0_SPEC.md#tipos-de-íconos-disponibles)
- **¿Cómo funciona auto-layout?** → [SDJF v2.0](spec/SDJF_v2.0_SPEC.md#auto-layout)
- **¿Cómo contribuyo?** → [ROADMAP](ROADMAP.md#contribuciones)
- **¿Cuál es el roadmap?** → [ROADMAP.md](ROADMAP.md)
- **¿Cómo funciona el código?** → [Architecture](architecture/ARCHITECTURE.md)

---

## 📊 Diagrams

### Roadmap

![Roadmap de Versiones](diagrams/svgs/roadmap-versions.svg)

Muestra la evolución de SDJF desde v1.0 hasta v3.0 planificado.

### Arquitectura v2.1

![Arquitectura del Módulo Routing](diagrams/svgs/routing-architecture.svg)

Muestra el diseño propuesto del módulo `routing/` para v2.1.

### Arquitectura v2.1 (Código Actual)

![Arquitectura GAG](diagrams/svgs/05-arquitectura-gag.svg)

Diagrama auto-documentado del flujo de ejecución actual.

---

## 🤝 Contribuir

¿Quieres contribuir? Lee:

1. [ROADMAP.md](ROADMAP.md) - Qué necesita el proyecto
2. [Architecture](architecture/ARCHITECTURE.md) - Cómo está estructurado
3. [Implementation Strategy](architecture/IMPLEMENTATION_STRATEGY.md) - Guía técnica

**Áreas prioritarias:**
- [ ] Implementación v2.2 (collision avoidance con A*)
- [ ] Tests visuales automáticos
- [ ] Nuevos tipos de íconos
- [ ] Documentación de ejemplos
- [ ] Optimizaciones de performance

---

## 📄 Licencia

[Especificar licencia aquí]

---

## 📞 Contacto

Este proyecto es parte de ALMA. Para reportar bugs o sugerir mejoras, abre un issue en el repositorio.

---

**AlmaGag** - Generación automática de diagramas con layout jerárquico inteligente (AUTO/LAF) y routing declarativo
**Versión**: v3.3.0 + SDJF v2.1 | **Actualizado**: 2026-02-28
