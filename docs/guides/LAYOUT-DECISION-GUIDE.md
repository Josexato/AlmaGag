# Guía de Decisión: ¿AUTO o LAF?

Esta guía te ayudará a elegir el algoritmo de layout correcto para tu diagrama.

## Decisión Rápida (Árbol de Decisión)

```
¿Tu diagrama tiene más de 20 elementos?
├─ SÍ → Usa LAF
└─ NO ↓

¿Tienes contenedores anidados (3+ niveles)?
├─ SÍ → Usa LAF
└─ NO ↓

¿Tienes más de 20 conexiones entre elementos?
├─ SÍ → Usa LAF
└─ NO ↓

¿Es crítico minimizar cruces de conexiones?
├─ SÍ → Usa LAF
└─ NO ↓

¿Tienes coordenadas x,y manuales que quieres preservar?
├─ SÍ → Usa AUTO
└─ NO → Usa LAF (más optimizado en general)
```

**Comando para AUTO**:
```bash
almagag diagrama.gag
# o explícitamente:
almagag diagrama.gag --layout-algorithm=auto
```

**Comando para LAF**:
```bash
almagag diagrama.gag --layout-algorithm=laf
```

---

## Comparación Visual Rápida

### Diagrama Simple (8 elementos, 6 conexiones)

| **AUTO** | **LAF** |
|----------|---------|
| ✅ Rápido (0.2s) | ⚠️ Overhead (0.4s) |
| ✅ Suficientemente bueno | ✅ Perfecto pero innecesario |
| 🎯 **Recomendado** | ⚪ Overkill |

**Veredicto**: Usa **AUTO** para diagramas simples.

---

### Diagrama Complejo (25 elementos, 35 conexiones, contenedores anidados)

| **AUTO** | **LAF** |
|----------|---------|
| ⚠️ 12 cruces | ✅ 2 cruces (-83%) |
| ⚠️ 8 colisiones | ✅ 2 colisiones (-75%) |
| ⚠️ Lento (1.5s) | ✅ Rápido (0.8s) |
| ⚠️ 25 routing calls | ✅ 5 routing calls (-80%) |
| ⚪ Funcional | 🎯 **Recomendado** |

**Veredicto**: Usa **LAF** para diagramas complejos.

---

## Tabla de Decisión Detallada

| Criterio | AUTO | LAF | Ganador |
|----------|------|-----|---------|
| **Elementos** | < 10 | > 20 | AUTO para pequeños, LAF para grandes |
| **Conexiones** | < 10 | > 20 | AUTO para pocas, LAF para muchas |
| **Anidación** | 1-2 niveles | 3+ niveles | LAF para jerarquías profundas |
| **Cruces** | No críticos | Crítico minimizar | LAF reduce 87% cruces |
| **Colisiones** | Acepta iteraciones | Minimización agresiva | LAF reduce 24% colisiones |
| **Performance** | Rápido (<0.5s) | Optimizado para complejos | AUTO para simples, LAF para complejos |
| **Coordenadas manuales** | ✅ Soporta | ❌ Ignora | AUTO si necesitas coordenadas manuales |
| **Prototipos rápidos** | ✅ Ideal | ⚠️ Overhead | AUTO para sketching |
| **Producción** | ✅ Bueno | ✅ Mejor | LAF para calidad final |

---

## Casos de Uso Reales

### ✅ Usa AUTO cuando...

#### 1. **Diagrama de Flujo Simple**
```
┌─────┐    ┌─────┐    ┌─────┐
│Start│ -> │ Do  │ -> │ End │
└─────┘    └─────┘    └─────┘
```
- 3 elementos, 2 conexiones
- Lineal, sin complejidad
- **Comando**: `almagag flujo.gag`

#### 2. **Sketch Rápido**
```gag
# Prototipo rápido con posiciones manuales
server web1 {
  label: "Web Server"
  x: 100
  y: 100
}

database db1 {
  label: "Database"
  x: 300
  y: 100
}
```
- Quieres control manual de posiciones
- **Comando**: `almagag sketch.gag`

#### 3. **Documentación Interna Simple**
- Diagrama para README de proyecto pequeño
- 5-8 componentes sin anidación
- No requiere calidad de presentación premium
- **Comando**: `almagag architecture.gag --exportpng`

---

### ✅ Usa LAF cuando...

#### 1. **Arquitectura de Microservicios**
```gag
# 25 microservicios, 40 conexiones
# 3 capas: frontend, backend, data
# Múltiples contenedores por capa

firewall frontend {
  label: "Frontend Layer"
  contains: [web1, web2, web3, cdn]
}

firewall backend {
  label: "Backend Layer"
  contains: [api1, api2, auth, gateway, cache]
}

firewall data {
  label: "Data Layer"
  contains: [db1, db2, queue, storage]
}

# ... 40 conexiones entre servicios
```
- **Problema con AUTO**: 15+ cruces, difícil de leer
- **Solución LAF**: 2 cruces, layout limpio
- **Comando**: `almagag microservices.gag --layout-algorithm=laf`

#### 2. **Diagrama de Despliegue AWS**
```gag
# VPC con subnets públicas/privadas
# 30+ recursos: EC2, RDS, S3, ALB, etc.
# Anidación: VPC > AZ > Subnet > Instances

building vpc {
  label: "VPC Production"

  container az1 {
    label: "us-east-1a"

    firewall public_subnet {
      contains: [alb, nat_gateway]
    }

    firewall private_subnet {
      contains: [ec2_1, ec2_2, cache]
    }
  }

  container az2 {
    # ...similar structure
  }
}
```
- **Problema con AUTO**: Contenedores se superponen, cruces caóticos
- **Solución LAF**: Anidación limpia, minimización de cruces
- **Comando**: `almagag aws-deployment.gag --layout-algorithm=laf --exportpng`

#### 3. **Modelo de Datos Complejo**
```gag
# 20+ entidades con relaciones many-to-many
# Múltiples conexiones por entidad
```
- **Problema con AUTO**: Spaghetti de conexiones
- **Solución LAF**: Minimización de cruces hace legible el diagrama
- **Comando**: `almagag data-model.gag --layout-algorithm=laf`

#### 4. **Presentación Ejecutiva**
- Cliente espera calidad premium
- Diagrama se proyectará en sala de juntas
- Importa la estética y claridad
- **Comando**: `almagag presentation.gag --layout-algorithm=laf --exportpng`

---

## Comparación de Métricas

Resultados de pruebas en 10 diagramas reales del proyecto AlmaGag:

### Diagrama: 05-arquitectura-gag.gag
(Arquitectura completa de AlmaGag: 18 elementos, 22 conexiones, 3 niveles de anidación)

| Métrica | AUTO | LAF | Mejora LAF |
|---------|------|-----|------------|
| **Cruces** | 15 | 2 | **-87%** ✅ |
| **Colisiones** | 8 | 6 | **-25%** ✅ |
| **Llamadas routing** | 25 | 5 | **-80%** ✅ |
| **Expansiones canvas** | 8 | 1 | **-87%** ✅ |
| **Tiempo ejecución** | 1.2s | 0.7s | **-42%** ✅ |
| **Iteraciones** | 12 | 4 | **-67%** ✅ |

**Conclusión**: LAF es significativamente mejor para este tipo de diagrama.

### Diagrama: test-container-2-elementos.gag
(Contenedor simple con 2 servidores: 2 elementos, 1 conexión, 1 nivel de anidación)

| Métrica | AUTO | LAF | Diferencia |
|---------|------|-----|------------|
| **Cruces** | 0 | 0 | Empate |
| **Colisiones** | 0 | 0 | Empate |
| **Llamadas routing** | 1 | 1 | Empate |
| **Tiempo ejecución** | 0.15s | 0.35s | AUTO más rápido |

**Conclusión**: AUTO es más eficiente para diagramas triviales.

---

## Guía de Migración: AUTO → LAF

Si tienes un diagrama existente en AUTO y quieres migrar a LAF:

### Paso 1: Generar ambas versiones

```bash
# Versión AUTO (current)
almagag diagrama.gag --layout-algorithm=auto -o output/diagrama-auto.svg

# Versión LAF (nueva)
almagag diagrama.gag --layout-algorithm=laf -o output/diagrama-laf.svg
```

### Paso 2: Comparar visualmente

Abre ambos SVGs lado a lado y compara:
- ✅ Cruces de conexiones (menos es mejor)
- ✅ Claridad de jerarquía
- ✅ Uso del espacio
- ⚠️ Pérdida de coordenadas manuales (si las tenías)

### Paso 3: Comparar métricas

```bash
# Con debug y dump de iteraciones
almagag diagrama.gag --layout-algorithm=auto --dump-iterations --debug > auto.log
almagag diagrama.gag --layout-algorithm=laf --dump-iterations --debug > laf.log

# Comparar CSVs
diff debug/layout_evolution_*.csv
```

### Paso 4: Decidir

- Si LAF mejora cruces >50% → **Migra a LAF**
- Si LAF reduce tiempo >30% → **Migra a LAF**
- Si tienes coordenadas manuales críticas → **Mantén AUTO**
- Si el diagrama es trivial (<5 elementos) → **Mantén AUTO**

### Paso 5: Actualizar comandos

```bash
# En scripts, Makefiles, CI/CD:
# Antes:
# almagag diagrama.gag

# Después:
# almagag diagrama.gag --layout-algorithm=laf
```

---

## Debugging de Decisiones

### ¿No estás seguro cuál usar?

Prueba ambos con visualización completa:

```bash
# AUTO con debug completo
almagag diagrama.gag \
  --layout-algorithm=auto \
  --debug \
  --visualdebug \
  --dump-iterations \
  -o output/auto.svg

# LAF con debug completo
almagag diagrama.gag \
  --layout-algorithm=laf \
  --debug \
  --visualdebug \
  --dump-iterations \
  --visualize-growth \
  -o output/laf.svg

# Comparar resultados
echo "Comparando métricas..."
cat debug/layout_evolution_*.csv
```

Luego observa:
1. **Visualmente**: ¿Cuál se ve más claro?
2. **Métricas**: ¿Cuál tiene menos cruces/colisiones?
3. **Tiempo**: ¿Cuál es más rápido?

---

## FAQs

### ¿Puedo cambiar de algoritmo en un proyecto existente?

**Sí**, es completamente seguro. Los algoritmos solo afectan posicionamiento automático, no el contenido del diagrama.

```bash
# Simplemente agrega el flag
almagag mi-diagrama-existente.gag --layout-algorithm=laf
```

### ¿LAF preserva mis coordenadas x,y manuales?

**No**, LAF ignora coordenadas manuales para optimizar globalmente. Si necesitas coordenadas manuales específicas, usa AUTO.

### ¿Puedo mezclar AUTO y LAF en el mismo proyecto?

**Sí**, absolutamente:

```bash
# Diagramas simples con AUTO
almagag simple-flow.gag -o output/simple-flow.svg

# Diagramas complejos con LAF
almagag complex-architecture.gag --layout-algorithm=laf -o output/architecture.svg
```

### ¿LAF funciona con todos los tipos de elementos?

**Sí**, LAF soporta todos los tipos de elementos de AlmaGag:
- `server`, `database`, `client`, `service`
- `container`, `building`, `firewall` (anidación)
- Todas las direcciones de conexiones

### ¿Qué pasa si LAF no mejora mi diagrama?

Posibles razones:
1. **Diagrama muy simple**: AUTO ya es óptimo
2. **Pocas conexiones**: LAF optimiza cruces; si no hay cruces, no hay mucha mejora
3. **Necesitas coordenadas manuales**: LAF las ignora

**Solución**: Usa AUTO para ese diagrama específico.

### ¿Cuánto más lento es LAF?

- **Diagramas pequeños (<10 elementos)**: LAF es ~2x más lento (0.3s vs 0.15s) - poco relevante
- **Diagramas medianos (10-20 elementos)**: Similar (~0.5s)
- **Diagramas grandes (>20 elementos)**: LAF es más rápido por menos routing calls

**Conclusión**: En producción, la diferencia de velocidad es insignificante.

---

## Resumen de Decisión

### Usa AUTO si:
- ✅ Diagrama simple (<10 elementos)
- ✅ Pocas conexiones (<10)
- ✅ Necesitas coordenadas x,y manuales
- ✅ Prototipado rápido
- ✅ No te importan cruces de conexiones

### Usa LAF si:
- ✅ Diagrama complejo (>20 elementos)
- ✅ Muchas conexiones (>20)
- ✅ Contenedores anidados (3+ niveles)
- ✅ Minimizar cruces es crítico
- ✅ Producción / Presentaciones
- ✅ Quieres la mejor calidad posible

### Regla de Oro

**"Cuando tengas duda, usa LAF. Solo usa AUTO si tienes una razón específica (coordenadas manuales, diagrama trivial)."**

LAF es el futuro de AlmaGag. AUTO se mantiene por compatibilidad y casos específicos.

---

## Recursos Adicionales

- [CLI-REFERENCE.md](./CLI-REFERENCE.md) - Documentación completa de opciones CLI
- [LAF-COMPARISON.md](../LAF-COMPARISON.md) - Análisis técnico profundo de LAF
- [LAF-PROGRESS.md](../LAF-PROGRESS.md) - Historia de desarrollo de LAF
- [EXAMPLES.md](./EXAMPLES.md) - Ejemplos prácticos con ambos algoritmos
- [QUICKSTART.md](./QUICKSTART.md) - Inicio rápido con AlmaGag

---

**AlmaGag v3.0.0** - Sistema de Diagramas de Arquitectura
