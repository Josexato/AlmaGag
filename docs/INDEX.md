# Índice de Documentación - AlmaGag

**Versión**: v3.5.0 (código)
**Actualizado**: 2026-08-02

---

## 📚 Documentación Completa

Esta es la guía completa de documentación de AlmaGag, organizada por tipo de documento.

---

## 🚀 Inicio Rápido

**Para usuarios nuevos:**

1. **[README.md](../README.md)** - Visión general y ejemplo mínimo
2. **[Quickstart Guide](guides/QUICKSTART.md)** - Instalación paso a paso
3. **[Galería de Ejemplos](guides/EXAMPLES.md)** - 12 ejemplos visuales

**Para entender el vocabulario:**

- **[CONCEPTS.md](CONCEPTS.md)** - Glosario v3.5 (formato, motor, dibujo/emisión, calidad y proceso)

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
| [**FORMATO_ARCHIVOS.md**](spec/FORMATO_ARCHIVOS.md) | **vigente** | ★ Referencia | La spec viva del formato — empezar por aquí |

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
| [Galería de Ejemplos](guides/EXAMPLES.md) | Todos | 12 ejemplos con explicaciones |

### Temas por Feature

- **Íconos y colores** → [Ejemplos 01-04](guides/EXAMPLES.md#01---iconos-registrados)
- **Conexiones y flechas** → [Ejemplo 03](guides/EXAMPLES.md#03---tipos-de-conexiones)
- **Waypoints** → [Ejemplo 06](guides/EXAMPLES.md#06---waypoints-sdjf-v15)
- **Contenedores** → [Ejemplo 07](guides/EXAMPLES.md#07---contenedores-sdjf-v20)
- **Auto-layout** → [Ejemplo 08](guides/EXAMPLES.md#08---auto-layout-completo-sdjf-v20)
- **Sizing proporcional** → [Ejemplo 09](guides/EXAMPLES.md#09---sizing-proporcional-sdjf-v20)
- **Layout híbrido** → [Ejemplo 10](guides/EXAMPLES.md#10---layout-híbrido-sdjf-v20)

---

## 🧠 Motor de layout (el motor elige solo)

Desde v3.4 **no se elige algoritmo**: el default `select` decide la
estrategia desde el JSON (`contains`/`considerations` → `auto`; `areas`,
`decision` o ciclo sin coordenadas → `hier`; `legacy` ex-LAF, congelado,
sólo debug).

| Documento | Nivel | Descripción |
|-----------|-------|-------------|
| [Guía de decisión](guides/LAYOUT-DECISION-GUIDE.md) | Todos | Cómo decide el motor y cómo influir desde el JSON |
| [Referencia CLI](guides/CLI-REFERENCE.md) | Todos | Flags reales (`--view`, `--exportpng`, `--epifania`…) |
| [Contrato del skill](guides/SKILL-ALMAGAG.md) | Autores | Capacidades v3.5 (grupos N–R) que el skill puede asumir |
| [Biblioteca routing](architecture/modules/routing/ROUTING.md) | Desarrolladores | Tipos declarativos de línea |
| Histórico LAF | Técnico | `architecture/modules/layout/laf/` (motor congelado como `legacy`) |

```bash
almagag diagrama.sdjf                 # el motor elige
almagag diagrama.sdjf --view lanes    # forzar una REPRESENTACIÓN (hier)
almagag diagrama.sdjf --epifania      # ver el proceso por fases
```

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

- **✅ Completado**: v1.0 → v3.5 (motor único `select`, estrategias auto/hier,
  zonas anidadas §P59/§P60, anticolisión global §P61, semántica §Q63,
  tokens de tema §O57, emisión §O50-O58, review de Claude Design completo)
- **📅 Siguiente**: `TECHNICAL_DEBT.md` — WISH-DRAW-002 (flujos resaltados),
  WISH-LAYOUT-008 (unificación de etiquetas)

---

## 📂 Estructura de Documentación

```
docs/
├── INDEX.md                      # Este archivo
├── CONCEPTS.md                   # Glosario
├── ROADMAP.md                    # Plan de desarrollo
├── TECHNICAL_DEBT.md             # Deuda técnica (BUGS-*, WISH-*)
├── DIAGRAM_REVIEW.md             # HISTÓRICO: revisión visual jun-2026
├── architecture/history/         # ARCHITECTURE y FLUJO_EJECUCION antiguos
├── CHANGELOG.md · RELEASE_v3.0.0.md
│
├── spec/
│   ├── FORMATO_ARCHIVOS.md       # ★ Spec vigente de .sdjf/.gag
│   ├── SDJF_v1.0_SPEC.md · SDJF_v2.0_SPEC.md · SDJF_v2.1_PROPOSAL.md
│   └── SDJF_UNION_TYPE.md · SVG_TO_BWT_SPEC.md · CONTAINER_GROUPING_STRATEGY.md
│
├── guides/
│   ├── QUICKSTART.md · EXAMPLES.md · CLI-REFERENCE.md
│   ├── LAYOUT-DECISION-GUIDE.md  # Cómo decide el motor
│   └── SKILL-ALMAGAG.md          # ★ Contrato del skill (v3.5, grupos N–R)
│
├── architecture/
│   ├── ARCHITECTURE.md · EVOLUTION.md · WISH-ARCH-004-el-mapa.md
│   └── modules/                  # layout/ (auto·hier·legacy) · routing/
│       └── layout/laf/           # HISTÓRICO (motor congelado como legacy)
│
├── reviews/                      # Reviews de Claude Design por iteración
│   ├── iteracion-3/ · iteracion-4/ · iteracion-5/
│   ├── grupo-O/ · grupo-P/       # criterios O50–O58 · P59–P62 + Q63–Q65
│   └── auditoria-2026-08-02/     # Auditoría docs⇄código
│
└── diagrams/
    ├── gags/                     # 34 fixtures fuente (.sdjf y .gag)
    └── svgs/                     # SVG generados (scripts/generate_docs.py)
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
- [ ] Tickets abiertos de `TECHNICAL_DEBT.md` (tanda auditoría 2026-08-02)
- [ ] WISH-DRAW-002: flujos de información resaltados
- [ ] WISH-LAYOUT-008: unificar los sistemas de etiquetas

---

## 📄 Licencia

MIT — ver [LICENSE](../LICENSE).

---

## 📞 Contacto

Este proyecto es parte de ALMA. Para reportar bugs o sugerir mejoras, abre un issue en el repositorio.

---

**AlmaGag** - Generación automática de diagramas con layout jerárquico inteligente (AUTO/LAF) y routing declarativo
**Versión**: v3.3.0 + SDJF v2.1 | **Actualizado**: 2026-02-28
