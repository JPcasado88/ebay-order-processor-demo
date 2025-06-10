# Tests - eBay Order Processor

Esta suite de tests valida la funcionalidad completa del procesador de órdenes de eBay.

## 🏗️ Estructura

```
tests/
├── __init__.py                 # Módulo de tests
├── conftest.py                 # Fixtures compartidas
├── test_sku_matching.py        # Tests de matching de SKUs
├── test_file_generation.py     # Tests de generación de archivos
├── test_api_integration.py     # Tests de integración API
└── README.md                   # Esta documentación
```

## 🚀 Cómo Ejecutar

### Opción 1: Script personalizado (Recomendado)
```bash
# Todos los tests
python run_tests.py

# Solo tests unitarios rápidos
python run_tests.py --unit --fast

# Tests de integración con cobertura
python run_tests.py --integration --coverage

# Tests específicos
python run_tests.py --file test_sku_matching.py
python run_tests.py --test test_v_codes_extraction
```

### Opción 2: pytest directo
```bash
# Todos los tests
pytest tests/

# Tests rápidos únicamente
pytest -m "not slow" tests/

# Tests con cobertura
pytest --cov=ebay_processor tests/

# Test específico
pytest tests/test_sku_matching.py::TestSKUIdentifierExtraction::test_v_codes_extraction
```

## 📋 Tipos de Tests

### 🧪 Tests Unitarios (`-m unit`)
- **Extracción de SKUs**: Valida patrones de identificación
- **Normalización**: Tests de funciones de string utils
- **Formateo de datos**: Verificación de transformaciones

### 🔗 Tests de Integración (`-m integration`)
- **Flujo completo**: SKU → Match → Archivo
- **Matching con catálogo real**: Usando datos de `ktypemaster3.csv`
- **Generación de archivos**: Excel/CSV con datos reales

### 🌐 Tests de API (`-m api`)
- **eBay API**: Autenticación, órdenes, actualización de estados
- **Rate limiting**: Manejo de límites de velocidad
- **Error handling**: Recuperación de errores de red

## 🏷️ Marcadores Disponibles

- `@pytest.mark.unit` - Tests unitarios rápidos
- `@pytest.mark.integration` - Tests de integración
- `@pytest.mark.api` - Tests que requieren API
- `@pytest.mark.slow` - Tests que tardan más tiempo

## 📊 Cobertura de Código

Para generar reportes de cobertura:

```bash
# Reporte HTML
python run_tests.py --coverage

# Solo reporte en terminal
pytest --cov=ebay_processor --cov-report=term-missing tests/
```

Los reportes se generan en:
- `htmlcov/index.html` - Reporte HTML interactivo
- Terminal - Resumen con líneas faltantes

## 🔧 Configuración

### Dependencias para Tests
```bash
pip install pytest pytest-cov pytest-html pytest-xdist
```

### Variables de Entorno
- `TESTING=true` - Modo test (auto-configurado)
- `LOG_LEVEL=DEBUG` - Nivel de logging para tests

### Configuración pytest.ini
- Marcadores personalizados
- Filtros de warnings
- Configuración de logging
- Paths de test

## 📝 Casos de Test Importantes

### SKU Matching
Los tests validan estos patrones críticos:
- ✅ `V94` → `V94`
- ✅ `Q227 CVT` → `Q227`
- ✅ `VAW0307 001 X205` → `X205`
- ✅ `G-VAW0198 003 X5` → `X5`
- ✅ `8435` → `L2` (mapeo especial)

### Casos Edge
- SKUs con colores/trim: `V214 - Black-Black with Grey Trim`
- Patrones bootmat: `8590BM-grey-velour-bootmat-grey-trim`
- Códigos highlands: `IV20 1XB` (servicio especial)

## 🐛 Debugging Tests

### Test fallido individual
```bash
pytest -v -s tests/test_sku_matching.py::test_specific_function
```

### Ver logs durante tests
```bash
pytest --log-cli-level=DEBUG tests/
```

### Parar en primer fallo
```bash
pytest -x tests/
```

## 📈 Métricas de Calidad

### Objetivos de Cobertura
- **Extracción SKU**: >95%
- **Matching**: >90%
- **Generación archivos**: >85%
- **APIs**: >80%

### Performance
- Tests unitarios: <5s total
- Tests integración: <30s total
- Tests API: <60s total (con mocks)

## 🔄 Integración Continua

### Pre-commit hooks
```bash
# Ejecutar tests rápidos antes de commit
python run_tests.py --fast
```

### GitHub Actions / CI
```yaml
- name: Run tests
  run: |
    python run_tests.py --unit --fast
    python run_tests.py --integration --coverage
```

## 📚 Recursos Adicionales

- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python.org/3/library/unittest.html)

## 🆘 Troubleshooting

### ImportError al ejecutar tests
```bash
# Asegúrate de estar en el directorio correcto
cd ebay_order_processor/
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Tests lentos
```bash
# Ejecutar solo tests rápidos
python run_tests.py --fast
```

### Mocks no funcionan
- Verificar imports en `conftest.py`
- Comprobar paths en `monkeypatch.setattr`

---

**¡Happy Testing!** 🎉

Para preguntas o problemas, consulta la documentación del proyecto principal. 