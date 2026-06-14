# Guía de Inicio Rápido - AlmaGag

## Instalación

### Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Instalar AlmaGag

```bash
cd AlmaGag
pip install -e .
```

Esto instala:
- El comando `almagag` globalmente
- Todas las dependencias necesarias (`svgwrite`)

## Primer Diagrama

### 1. Crear archivo SDJF

Crea un archivo `mi-diagrama.gag`:

```json
{
  "canvas": {"width": 800, "height": 600},
  "elements": [
    {
      "id": "frontend",
      "type": "cloud",
      "x": 150,
      "y": 250,
      "label": "Frontend",
      "color": "lightblue"
    },
    {
      "id": "api",
      "type": "server",
      "x": 400,
      "y": 250,
      "label": "API Rest",
      "color": "gold"
    },
    {
      "id": "database",
      "type": "building",
      "x": 650,
      "y": 250,
      "label": "PostgreSQL",
      "color": "orange"
    }
  ],
  "connections": [
    {
      "from": "frontend",
      "to": "api",
      "label": "HTTPS",
      "direction": "forward"
    },
    {
      "from": "api",
      "to": "database",
      "label": "SQL",
      "direction": "forward"
    }
  ]
}
```

### 2. Generar SVG

```bash
almagag mi-diagrama.gag
```

**Salida:**
```
[OK] AutoLayout v2.1: 0 colisiones detectadas
     - 1 niveles, 3 grupo(s)
     - Prioridades: 0 high, 3 normal, 0 low
[OK] Diagrama generado exitosamente: mi-diagrama.svg
```

### 3. Ver Resultado

Abre `mi-diagrama.svg` en tu navegador o editor de imágenes.

---

## Uso Avanzado

### Algoritmos de Layout ✨ NUEVO v3.0

AlmaGag v3.0 ofrece dos algoritmos de layout automático:

#### 🔹 AUTO (por defecto)
Layout jerárquico iterativo, rápido para diagramas simples.

```bash
almagag diagrama.gag
# o explícitamente:
almagag diagrama.gag --layout-algorithm=auto
```

**Ventajas**:
- ✅ Rápido en diagramas pequeños
- ✅ Preserva coordenadas x,y manuales
- ✅ Ideal para prototipos

#### 🔹 LAF (opcional)
Layout optimizado con minimización de cruces, ideal para diagramas complejos.

```bash
almagag diagrama.gag --layout-algorithm=laf
```

**Ventajas**:
- ✅ -87% cruces de conexiones
- ✅ -24% colisiones
- ✅ Optimizado para >20 elementos
- ✅ Excelente con contenedores anidados

**¿Cuándo usar LAF?**
- Diagrama complejo (>20 elementos)
- Contenedores anidados (3+ niveles)
- Muchas conexiones (>20)
- Minimizar cruces es crítico

Ver [LAYOUT-DECISION-GUIDE.md](./LAYOUT-DECISION-GUIDE.md) para elegir el algoritmo correcto.

---

### Auto-Layout (SDJF v2.0)

No necesitas especificar coordenadas:

```json
{
  "elements": [
    {
      "id": "api",
      "type": "server",
      "label": "API",
      "label_priority": "high",
      "hp": 2.0,
      "color": "gold"
    },
    {
      "id": "cache",
      "type": "cloud",
      "label": "Redis",
      "color": "cyan"
    },
    {
      "id": "logger",
      "type": "cloud",
      "label": "Logger",
      "label_priority": "low",
      "hp": 0.8,
      "color": "gray"
    }
  ],
  "connections": [
    {"from": "api", "to": "cache"},
    {"from": "api", "to": "logger"}
  ]
}
```

El sistema posiciona automáticamente:
- `api` (HIGH, grande) → Centro
- `cache` (NORMAL) → Alrededor
- `logger` (LOW, pequeño) → Periferia

### Sizing Proporcional

Controla el tamaño con `hp` (height) y `wp` (width):

```json
{
  "id": "big-server",
  "type": "server",
  "hp": 2.0,
  "wp": 1.5,
  "label": "Large Server"
}
```

- `hp` = 2.0 → Altura doble (100px en vez de 50px)
- `wp` = 1.5 → Ancho 1.5× (120px en vez de 80px)

### Waypoints (Routing Complejo)

Para líneas que deben evitar elementos:

```json
{
  "from": "A",
  "to": "B",
  "waypoints": [
    {"x": 450, "y": 490},
    {"x": 300, "y": 490}
  ],
  "label": "complex route",
  "direction": "forward"
}
```

---

## Opciones de Línea de Comando

### Uso Básico

```bash
almagag archivo.gag
```

### Opciones Principales

| Opción | Descripción |
|--------|-------------|
| `--layout-algorithm {auto\|laf}` | Selecciona algoritmo de layout |
| `--debug` | Logs detallados |
| `--visualdebug` | Grilla + badge en SVG |
| `--exportpng` | Genera PNG además de SVG |
| `-o <ruta>` | Especifica archivo de salida |

**Ejemplos**:
```bash
# Layout con LAF
almagag diagrama.gag --layout-algorithm=laf

# Debug completo
almagag diagrama.gag --debug --visualdebug

# Exportar PNG
almagag diagrama.gag --exportpng

# Salida personalizada
almagag diagrama.gag -o output/mi-diagrama.svg
```

Ver [CLI-REFERENCE.md](./CLI-REFERENCE.md) para documentación completa de todas las opciones.

### Uso con Python

```bash
python -m AlmaGag.main archivo.gag
```

---

## Ejemplos Incluidos

```bash
# Íconos disponibles
almagag docs/examples/01-iconos-registrados.gag

# Tipos de conexiones
almagag docs/examples/03-conexiones.gag

# Auto-layout completo
almagag docs/examples/08-auto-layout.gag

# Sizing proporcional
almagag docs/examples/09-proportional-sizing.gag

# Layout híbrido (auto + manual)
almagag docs/examples/10-hybrid-layout.gag
```

---

## Tipos de Íconos Disponibles

| Tipo | Forma | Uso Típico |
|------|-------|------------|
| `server` | Rectángulo | Servidores, APIs |
| `building` | Rectángulo | Bases de datos, storage |
| `cloud` | Elipse | Servicios cloud, cache |
| `firewall` | Rectángulo | Firewalls, gateways |

Si un tipo no existe, se muestra **Banana With Tape** (plátano con cinta) como indicador visual.

---

## Direcciones de Conexión

```json
{
  "direction": "forward"       // A → B
}
{
  "direction": "backward"      // A ← B
}
{
  "direction": "bidirectional" // A ↔ B
}
{
  "direction": "none"          // A — B (sin flechas)
}
```

---

## Colores

Soporta nombres CSS y hexadecimales:

```json
"color": "lightblue"    // Nombre CSS
"color": "#3498DB"      // Hexadecimal
"color": "gold"         // Nombre CSS
"color": "#FF5733"      // Hexadecimal
```

Todos los colores generan gradientes automáticamente (claro → oscuro).

---

## Solución de Problemas

### Error: "comando no encontrado: almagag"

Instala en modo editable:
```bash
pip install -e .
```

O usa Python directamente:
```bash
python -m AlmaGag.main archivo.gag
```

### Warning: "No se pudo dibujar 'router'"

El tipo de ícono no existe. Opciones:
1. Usar un tipo disponible: `server`, `building`, `cloud`, `firewall`
2. Crear tu propio tipo en `draw/mi_tipo.py`
3. Aceptar el fallback BWT (Banana With Tape)

### Warning: "N colisiones detectadas"

El auto-layout no pudo resolver todas las colisiones. Opciones:
1. **Probar LAF**: `almagag diagrama.gag --layout-algorithm=laf` (reduce colisiones en 24%)
2. Aumentar tamaño del canvas
3. Especificar coordenadas manualmente para elementos problemáticos
4. Ajustar prioridades con `label_priority`
5. Usar `hp`/`wp` para cambiar tamaños

---

## Siguientes Pasos

### Algoritmos de Layout ✨ NUEVO
- **Guía de decisión AUTO vs LAF**: Ver `docs/guides/LAYOUT-DECISION-GUIDE.md`
- **Comparación técnica**: Ver `docs/architecture/modules/layout/laf/COMPARISON.md`
- **Referencia CLI completa**: Ver `docs/guides/CLI-REFERENCE.md`

### Especificaciones SDJF
- **SDJF v3.0**: Ver `docs/RELEASE_v3.0.0.md`
- **SDJF v2.0**: Ver `docs/spec/SDJF_v2.0_SPEC.md`
- **SDJF v2.1**: Ver `docs/spec/SDJF_v2.1_PROPOSAL.md`

### Recursos Adicionales
- **Arquitectura del código**: Ver `docs/architecture/ARCHITECTURE.md`
- **Galería de ejemplos**: Ver `docs/guides/EXAMPLES.md`

---

**Versión**: AlmaGag v3.0.0 + SDJF v3.0
**Actualizado**: 2026-01-21
