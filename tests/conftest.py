"""
Configuración de pytest y fixtures compartidas para todos los tests.
"""

import pytest
import pandas as pd
import tempfile
import os
from datetime import datetime
from unittest.mock import MagicMock


@pytest.fixture(scope="session")
def test_data_dir():
    """Directorio con datos de prueba."""
    return os.path.join(os.path.dirname(__file__), 'test_data')


@pytest.fixture
def sample_catalog_data():
    """DataFrame con datos de catálogo de prueba."""
    return pd.DataFrame({
        'Template': ['q227', 'v94', 'zz164', 'x24', 'l13', 'ms-q80', 'q7', 'l2'],
        'COMPANY': ['ford', 'audi', 'ford', 'kia', 'audi', 'audi', 'seat', 'audi'],
        'MODEL': ['kuga', 'a1', 'transit', 'sportage', 'a1 pq25', 'a1', 'leon', 'tt'],
        'YEAR': ['2013-2020', '2009-2018', '2015-2019', '2010-2015', '2009-2018', '2009-2018', '2008-2012', '2006-2014'],
        'MATS': ['4', '4', '4', '4', '4', '5', '4', '4'],
        'NO OF CLIPS': ['4', '4', '8', '4', '4', '4', '4', '4'],
        'Type': ['A', 'D', 'D', 'A', 'D', 'D', 'A', 'D'],
        'ForcedMatchSKU': ['', '', '', '', '', '', '', ''],
        'Template_Normalized': ['Q227', 'V94', 'ZZ164', 'X24', 'L13', 'MSQ80', 'Q7', 'L2'],
        '_normalized_forced_sku': ['', '', '', '', '', '', '', '']
    })


@pytest.fixture
def sample_order_data():
    """Lista con datos de órdenes de prueba."""
    return [
        {
            'ORDER ID': 'ORDER001',
            'FILE NAME': 'EBAY_ORDER_001',
            'Process DATE': '2024-01-01 10:00:00',
            'FIRST NAME': 'John',
            'LAST NAME': 'Doe',
            'ADD1': '123 Main St',
            'ADD2': '',
            'ADD3': 'London',
            'ADD4': 'UK',
            'POSTCODE': 'SW1A 1AA',
            'TEL NO': '01234567890',
            'EMAIL ADDRESS': 'john@example.com',
            'REF NO': 'Q227',
            'TRIM': 'Black',
            'CARPET TYPE': 'CT65',
            'CARPET COLOUR': 'Black',
            'Make': 'Ford',
            'Model': 'Kuga',
            'YEAR': '2013-2020',
            'Pcs/Set': '4',
            'NO OF CLIPS': '4',
            'CLIP TYPE': 'A',
            'Raw SKU': 'Q227 CVT',
            'Item Number': '123456789',
            'Transaction ID': 'TXN001',
            'FinalBarcode': 'BAR001',
            'Product Title': 'For Ford Kuga Car Mats'
        }
    ]


@pytest.fixture
def temp_output_dir():
    """Directorio temporal para outputs de test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config():
    """Configuración mock para tests."""
    return {
        'ebay': {
            'app_id': 'test_app_id',
            'cert_id': 'test_cert_id',
            'token': 'test_token',
            'base_url': 'https://api.sandbox.ebay.com',
            'timeout': 30
        },
        'paths': {
            'data_dir': 'test_data',
            'output_dir': 'test_output',
            'master_file': 'test_ktypemaster.csv'
        },
        'excel_formatting': True,
        'debug': True
    }


@pytest.fixture
def mock_logger():
    """Logger mock para tests."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


# Comentamos el setup automático de logging por ahora
# @pytest.fixture(autouse=True)
# def setup_test_logging(mock_logger, monkeypatch):
#     """Setup automático de logging para tests."""
#     monkeypatch.setattr('ebay_processor.utils.logger.get_logger', lambda name: mock_logger)


@pytest.fixture
def sample_sku_test_cases():
    """Casos de prueba para extracción de SKUs."""
    return [
        # (input_sku, expected_output)
        ("V94", "V94"),
        ("Q227 CVT", "Q227"),
        ("ZZ164HOLES", "ZZ164HOLES"),
        ("X24", "X24"),
        ("CT65 Q80", "Q80"),
        ("VAW0307 001 X205", "X205"),
        ("G-VAW0198 003 X5", "X5"),
        ("8435", "L2"),  # Mapeo especial
        ("R-VAW0212", "R-VAW0212"),  # Excepción
        ("MS-ABC123", "MS-ABC123"),
        ("Q7 OC-Black-Carpet-Black with Grey Trim", "Q7"),
        ("V214 - Black-Black with Grey Trim", "V214"),
    ]


@pytest.fixture
def sample_failing_skus():
    """SKUs que sabemos que están fallando en el sistema real."""
    return [
        "ZZ126-4 - Black with Blue Trim - VAW",
        "AB124-Black-Carpet-Black with Black Trim", 
        "8590BM-grey-velour-bootmat-grey-trim",
        "8683BM-black-velour-bootmat-red-trim",
        "R-VAW0325",
        "UNKNOWN_PATTERN_123"
    ]


@pytest.fixture
def sample_ebay_api_response():
    """Respuesta mock de eBay API."""
    return {
        'orders': [
            {
                'orderId': 'ORDER123456',
                'orderFulfillmentStatus': 'NOT_STARTED',
                'creationDate': '2024-01-01T10:00:00.000Z',
                'buyer': {
                    'username': 'testbuyer123'
                },
                'pricingSummary': {
                    'total': {'value': '49.99', 'currency': 'GBP'}
                },
                'lineItems': [
                    {
                        'lineItemId': 'ITEM123456',
                        'sku': 'Q227 CVT - Black with Black Trim',
                        'title': 'For Ford Kuga 2013-2020 - Tailored Car Floor Mats',
                        'quantity': 1,
                        'itemId': '123456789012',
                        'transactionId': 'TXN123456'
                    }
                ],
                'shippingAddress': {
                    'fullName': 'John Doe',
                    'addressLine1': '123 Main Street',
                    'addressLine2': 'Flat 1',
                    'city': 'London',
                    'stateOrProvince': 'Greater London',
                    'postalCode': 'SW1A 1AA',
                    'countryCode': 'GB'
                }
            }
        ],
        'total': 1,
        'limit': 50,
        'offset': 0
    }


# Configuración de pytest
def pytest_configure(config):
    """Configuración global de pytest."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require API access"
    )


def pytest_collection_modifyitems(config, items):
    """Modificar items de colección para agregar markers automáticamente."""
    for item in items:
        # Marcar tests de API
        if "api" in item.nodeid or "API" in item.nodeid:
            item.add_marker(pytest.mark.api)
        
        # Marcar tests de integración
        if "integration" in item.nodeid or "Integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Marcar tests lentos
        if "slow" in item.name or item.get_closest_marker("slow"):
            item.add_marker(pytest.mark.slow) 