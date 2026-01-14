# Scripts de Documentación

Scripts para regenerar toda la documentación SVG del proyecto AlmaGag.

## 📋 Descripción

Estos scripts procesan todos los archivos `.gag` en `docs/diagrams/gags/` y generan sus correspondientes archivos `.svg` en `docs/diagrams/svgs/`.

## 🚀 Uso

### Python (Multiplataforma)

```bash
# Desde la raíz del proyecto
python scripts/generate_docs.py

# Con output detallado
python scripts/generate_docs.py --verbose
```

**Ventajas:**
- Funciona en Windows, Linux y Mac
- Output colorizado y claro
- Manejo robusto de errores
- Reporte detallado al final

### Windows (Batch)

```cmd
REM Desde la raíz del proyecto
scripts\generate_docs.bat
```

### Linux/Mac (Bash)

```bash
# Hacer el script ejecutable (solo la primera vez)
chmod +x scripts/generate_docs.sh

# Ejecutar
./scripts/generate_docs.sh

# Con output detallado
./scripts/generate_docs.sh --verbose
```

## 📂 Archivos Procesados

El script regenera automáticamente:

1. **execution-flow.svg** - Flujo de ejecución completo
2. **system-architecture.svg** - Arquitectura del sistema
3. **layout-optimization-flow.svg** - Flujo de optimización de layout
4. **routing-architecture.svg** - Arquitectura de routing
5. **roadmap-versions.svg** - Roadmap de versiones
6. Y cualquier otro `.gag` que esté en `docs/diagrams/gags/`

## 📊 Output Ejemplo

```
======================================================================
            Generador de Documentación SVG - AlmaGag
======================================================================

ℹ Encontrados 7 archivos .gag en docs/diagrams/gags

[1/7] Procesando: execution-flow.gag
✓ Generado: execution-flow.svg → docs/diagrams/svgs/

[2/7] Procesando: layout-optimization-flow.gag
✓ Generado: layout-optimization-flow.svg → docs/diagrams/svgs/

...

======================================================================
                           Reporte Final
======================================================================

  Total procesados:  7
  Exitosos:          7
  Errores:           0

✓ Toda la documentación se generó correctamente
```

## 🔧 Requisitos

- Python 3.7+
- AlmaGag instalado (debe poder ejecutarse con `python -m AlmaGag.main`)
- Los archivos `.gag` deben estar en `docs/diagrams/gags/`

## 🐛 Solución de Problemas

### Error: "No se encontraron archivos .gag"

**Solución:** Verifica que estás ejecutando el script desde la raíz del proyecto y que existen archivos `.gag` en `docs/diagrams/gags/`.

### Error: "ModuleNotFoundError: No module named 'AlmaGag'"

**Solución:** Asegúrate de estar en el directorio raíz del proyecto o instala AlmaGag con `pip install -e .`

### Los SVG no se generan correctamente

**Solución:** Ejecuta con `--verbose` para ver los errores detallados:
```bash
python scripts/generate_docs.py --verbose
```

## 📝 Cuándo Usar

Ejecuta este script cuando:
- Modifiques algún archivo `.gag` de documentación
- Actualices el código de AlmaGag y quieras verificar que la documentación se sigue generando correctamente
- Hagas un release y quieras asegurar que toda la documentación está actualizada
- Clones el repositorio en una nueva máquina

## 🔄 Integración con Git

Es recomendable regenerar la documentación antes de hacer commit si modificaste código que afecta el rendering:

```bash
# Regenerar documentación
python scripts/generate_docs.py

# Verificar cambios
git status docs/diagrams/svgs/

# Si hay cambios, agregarlos al commit
git add docs/diagrams/svgs/
git commit -m "docs: Actualizar SVG de documentación"
```

## 📌 Notas

- Los scripts NO modifican los archivos `.gag`, solo generan los `.svg`
- Los SVG generados sobrescriben los existentes en `docs/diagrams/svgs/`
- El script de Python es el más completo y recomendado
- Los scripts de Bash y Batch son alternativas más ligeras
