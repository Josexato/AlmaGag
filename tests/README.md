# Tests

Esta carpeta contiene fixtures de test y casos de prueba para AlmaGag.

## Estructura

```
tests/
├── fixtures/          # Archivos .gag para test fixtures
├── unit/              # Unit tests (futuro)
└── legacy/            # Datos históricos y tests antiguos
    └── data/          # Datos de test de versiones anteriores
```

## Test Fixtures

Los test fixtures son archivos `.gag` diseñados para validar funcionalidades específicas:

| Fixture | Propósito |
|---------|-----------|
| `test-auto-layout.gag` | Valida layout automático jerárquico |
| `test-routing-types.gag` | Valida todos los tipos de routing |
| `test-routing-v2.1.gag` | Valida características de routing v2.1 |
| `test-weighted-optimization.gag` | Valida optimización con pesos |

## Ejecutar tests

### Generar fixtures manualmente:

```bash
almagag tests/fixtures/test-auto-layout.gag
```

### Ejecutar todos los tests (futuro):

```bash
python scripts/run_tests.py
```

## Legacy Data

La carpeta `legacy/data/` contiene casos de test históricos de versiones anteriores del formato SDJF.
