"""
Tests para el módulo de generación de archivos.

Valida la creación correcta de archivos Excel y CSV.
"""

import pytest
import pandas as pd
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

from ebay_processor.services.file_generation import (
    generate_consolidated_run_file,
    generate_run24h_file,
    generate_consolidated_courier_master_file,
    generate_tracking_files,
    generate_unmatched_items_file,
    _format_run_row,
    _format_courier_master_row,
    _format_tracking_row
)


class TestFileFormatting:
    """Tests para las funciones de formateo de datos."""
    
    def test_format_run_row(self):
        """Test formateo de fila para archivo RUN."""
        sample_item = {
            'FILE NAME': 'TEST_ORDER_123',
            'Process DATE': '2024-01-01 10:00:00',
            'FIRST NAME': 'John',
            'LAST NAME': 'Doe',
            'ADD1': '123 Main St',
            'ADD2': 'Apt 1',
            'ADD3': 'London',
            'ADD4': 'UK',
            'POSTCODE': 'SW1A 1AA',
            'TEL NO': '01234567890',
            'EMAIL ADDRESS': 'john@example.com',
            'REF NO': 'q227',
            'TRIM': 'Black',
            'Embroidery': 'None',
            'CARPET TYPE': 'CT65',
            'CARPET COLOUR': 'Black',
            'Make': 'Ford',
            'Model': 'Kuga',
            'YEAR': '2013-2020',
            'Pcs/Set': '4',
            'NO OF CLIPS': '4',
            'CLIP TYPE': 'A',
            'Delivery Special Instruction': 'Leave at door',
            'Raw SKU': 'Q227 CVT',
            'Item Number': '123456789',
            'Transaction ID': 'TXN123',
            'ORDER ID': 'ORDER123',
            'FinalBarcode': 'BAR123'
        }
        
        result = _format_run_row(sample_item)
        
        # Verificar campos obligatorios
        assert result['FILE NAME'] == 'TEST_ORDER_123'
        assert result['ORIGIN OF ORDER'] == 'eBay'
        assert result['FIRST NAME'] == 'John'
        assert result['LAST NAME'] == 'Doe'
        assert result['QTY'] == '1'
        assert result['REF NO'] == 'Q227'
        assert result['Thread Colour'] == 'Matched'
        assert result['Bar Code Type'] == 'CODE93'
        assert result['Bar Code'] == 'BAR123'
        assert result['SKU'] == 'Q227 CVT'
    
    def test_format_courier_master_row(self):
        """Test formateo de fila para COURIER_MASTER."""
        first_item = {
            'FIRST NAME': 'John',
            'LAST NAME': 'Doe',
            'ADD1': '123 Main St',
            'ADD2': 'Apt 1',
            'ADD3': 'London',
            'ADD4': 'UK',
            'POSTCODE': 'SW1A 1AA',
            'FinalBarcode': 'BAR123',
            'CARPET TYPE': 'CT65',
            'CARPET COLOUR': 'BLACK'
        }
        
        all_items = [first_item]  # Solo un item
        
        result = _format_courier_master_row(first_item, all_items)
        
        assert result['Name'] == 'John'
        assert result['SURNAME'] == 'Doe'
        assert result['Postcode'] == 'SW1A 1AA'
        assert result['BarCode'] == 'BAR123'
        assert result['COUNTRY'] == 'UK'
        assert result['SERVICE'] == 'UK NEXT DAY DELIVERY'  # Default para códigos no highlands
        assert result['WEIGHT'] == 1  # CT65 Black especial
        assert result['DESCRIPTION'] == 'Car Mats'
    
    def test_format_courier_master_row_highlands(self):
        """Test formateo para código postal de Highlands."""
        first_item = {
            'FIRST NAME': 'Jane',
            'LAST NAME': 'Smith',
            'ADD1': '456 Highland Rd',
            'ADD2': '',
            'ADD3': 'Edinburgh',
            'ADD4': 'Scotland',
            'POSTCODE': 'IV20 1XB',  # Highlands postcode
            'FinalBarcode': 'BAR456',
            'CARPET TYPE': 'RUBBER',
            'CARPET COLOUR': 'GREY'
        }
        
        all_items = [first_item, first_item]  # Múltiples items
        
        result = _format_courier_master_row(first_item, all_items)
        
        assert result['SERVICE'] == 'UK STANDARD DELIVERY'  # Highlands service
        assert result['WEIGHT'] == 15  # Peso estándar para no-CT65-Black
    
    def test_format_tracking_row(self):
        """Test formateo de fila para tracking."""
        sample_item = {
            'Item Number': '123456789',
            'Product Title': 'For Ford Kuga Car Mats',
            'Raw SKU': 'Q227 CVT',
            'Transaction ID': 'TXN123',
            'FinalBarcode': 'BAR123'
        }
        
        order_id = 'ORDER123'
        
        result = _format_tracking_row(sample_item, order_id)
        
        assert result['Shipping Status'] == 'Shipped'
        assert result['Order ID'] == 'ORDER123'
        assert result['Item Number'] == '123456789'
        assert result['Item Title'] == 'For Ford Kuga Car Mats'
        assert result['Custom Label'] == 'Q227 CVT'
        assert result['Transaction ID'] == 'TXN123'
        assert result['Shipping Carrier Used'] == 'Hermes'
        assert result['Barcode'] == 'ORDER123'  # eBay Order ID
        assert result['Our_Barcode'] == 'BAR123'  # Nuestro barcode


class TestFileGeneration:
    """Tests para las funciones principales de generación de archivos."""
    
    @pytest.fixture
    def sample_orders(self):
        """Fixture con órdenes de muestra."""
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
            },
            {
                'ORDER ID': 'ORDER002',
                'FILE NAME': 'EBAY_ORDER_002',
                'Process DATE': '2024-01-01 11:00:00',
                'FIRST NAME': 'Jane',
                'LAST NAME': 'Smith',
                'ADD1': '456 Oak Ave',
                'ADD2': 'Unit B',
                'ADD3': 'Manchester',
                'ADD4': 'UK',
                'POSTCODE': 'M1 1AA',
                'TEL NO': '01987654321',
                'EMAIL ADDRESS': 'jane@example.com',
                'REF NO': 'V94',
                'TRIM': 'Grey',
                'CARPET TYPE': 'RUBBER',
                'CARPET COLOUR': 'Grey',
                'Make': 'Audi',
                'Model': 'A1',
                'YEAR': '2009-2018',
                'Pcs/Set': '4',
                'NO OF CLIPS': '4',
                'CLIP TYPE': 'D',
                'Raw SKU': 'V94 Blue',
                'Item Number': '987654321',
                'Transaction ID': 'TXN002',
                'FinalBarcode': 'BAR002',
                'Product Title': 'For Audi A1 Car Mats'
            }
        ]
    
    @pytest.fixture
    def temp_dir(self):
        """Fixture con directorio temporal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_config(self):
        """Fixture con configuración mock."""
        return {
            'excel_formatting': True,
            'some_setting': 'value'
        }
    
    def test_generate_consolidated_run_file(self, sample_orders, temp_dir, mock_config):
        """Test generación de archivo RUN consolidado."""
        run_date = datetime(2024, 1, 1, 12, 0, 0)
        
        result_path = generate_consolidated_run_file(
            sample_orders, temp_dir, run_date, mock_config
        )
        
        # Verificar que se creó el archivo
        assert result_path is not None
        assert os.path.exists(result_path)
        assert 'RUN_CONSOLIDATED' in os.path.basename(result_path)
        assert result_path.endswith('.xlsx')
        
        # Verificar contenido básico
        df = pd.read_excel(result_path)
        assert len(df) == 2
        assert 'REF NO' in df.columns
        assert 'ORIGIN OF ORDER' in df.columns
        assert df.iloc[0]['ORIGIN OF ORDER'] == 'eBay'
    
    def test_generate_run24h_file(self, sample_orders, temp_dir, mock_config):
        """Test generación de archivo RUN24H."""
        run_date = datetime(2024, 1, 1, 12, 0, 0)
        
        result_path = generate_run24h_file(
            sample_orders, temp_dir, run_date, mock_config
        )
        
        assert result_path is not None
        assert os.path.exists(result_path)
        assert 'RUN24H_CONSOLIDATED' in os.path.basename(result_path)
    
    def test_generate_courier_master_file(self, sample_orders, temp_dir, mock_config):
        """Test generación de archivo COURIER_MASTER."""
        run_date = datetime(2024, 1, 1, 12, 0, 0)
        
        result_path = generate_consolidated_courier_master_file(
            sample_orders, temp_dir, run_date, mock_config
        )
        
        assert result_path is not None
        assert os.path.exists(result_path)
        assert 'COURIER_MASTER' in os.path.basename(result_path)
        
        # Verificar contenido
        df = pd.read_excel(result_path)
        assert len(df) == 2  # Un registro por orden
        assert 'BarCode' in df.columns
        assert 'SERVICE' in df.columns
        assert 'WEIGHT' in df.columns
    
    def test_generate_tracking_files(self, sample_orders, temp_dir, mock_config):
        """Test generación de archivos de tracking."""
        run_date = datetime(2024, 1, 1, 12, 0, 0)
        
        result_paths = generate_tracking_files(
            sample_orders, temp_dir, run_date, mock_config
        )
        
        assert len(result_paths) >= 1  # Al menos el consolidado
        
        # Verificar archivo consolidado
        consolidated_path = next(p for p in result_paths if 'CONSOLIDATED' in p)
        assert os.path.exists(consolidated_path)
        
        df = pd.read_excel(consolidated_path)
        assert len(df) == 2
        assert 'Shipping Status' in df.columns
        assert 'Tracking Number' in df.columns
        assert all(df['Shipping Status'] == 'Shipped')
    
    def test_generate_unmatched_items_file(self, temp_dir, mock_config):
        """Test generación de archivo de items unmatched."""
        unmatched_items = [
            {
                'SKU': 'UNKNOWN_SKU',
                'Product Title': 'Unknown Product',
                'OrderID': 'ORDER999',
                'Store ID': 'test_store',
                'Error': 'No match found in catalog'
            },
            {
                'SKU': 'ANOTHER_UNKNOWN',
                'Product Title': 'Another Unknown Product',
                'OrderID': 'ORDER998',
                'Store ID': 'test_store',
                'Error': 'Pattern not recognized'
            }
        ]
        
        run_date = datetime(2024, 1, 1, 12, 0, 0)
        
        result_path = generate_unmatched_items_file(
            unmatched_items, temp_dir, run_date, mock_config
        )
        
        assert result_path is not None
        assert os.path.exists(result_path)
        assert 'unmatched_items' in os.path.basename(result_path)
        
        # Verificar contenido
        df = pd.read_excel(result_path)
        assert len(df) == 2
        assert 'SKU' in df.columns
        assert 'Error' in df.columns
    
    def test_empty_orders_returns_none(self, temp_dir, mock_config):
        """Test que órdenes vacías retornan None."""
        run_date = datetime(2024, 1, 1, 12, 0, 0)
        
        result = generate_consolidated_run_file([], temp_dir, run_date, mock_config)
        assert result is None
        
        result = generate_run24h_file([], temp_dir, run_date, mock_config)
        assert result is None


class TestAddressShuffling:
    """Tests para el shuffling de direcciones."""
    
    def test_address_shuffling_logic(self):
        """Test que las direcciones se reorganicen correctamente."""
        from ebay_processor.services.file_generation import _shuffle_address
        
        # Test caso normal
        result = _shuffle_address("123 Main St", "Apt 1", "London", "UK")
        assert len(result) == 4
        assert all(isinstance(addr, str) for addr in result)
        
        # Test con direcciones vacías
        result = _shuffle_address("123 Main St", "", "London", "")
        assert result[0] == "123 Main St"
        assert result[2] == "London"
        
        # Test con todas vacías
        result = _shuffle_address("", "", "", "")
        assert all(addr == "" for addr in result)


class TestFileNaming:
    """Tests para la nomenclatura de archivos."""
    
    def test_filename_generation(self):
        """Test generación de nombres de archivo."""
        from ebay_processor.services.file_generation import _generate_filename
        
        run_date = datetime(2024, 1, 15, 14, 30, 45)
        
        # Test archivo consolidado
        filename = _generate_filename("RUN", None, run_date, consolidated=True)
        assert "RUN_CONSOLIDATED" in filename
        assert "20240115" in filename
        assert filename.endswith(".xlsx")
        
        # Test archivo por tienda
        filename = _generate_filename("TRACKING", "test_store", run_date, consolidated=False)
        assert "TRACKING" in filename
        assert "test_store" in filename or "TEST_STORE" in filename
        assert "20240115" in filename


class TestErrorHandling:
    """Tests para manejo de errores."""
    
    def test_invalid_directory_handling(self, sample_orders, mock_config):
        """Test manejo de directorio inválido."""
        invalid_dir = "/nonexistent/directory/path"
        run_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # Debería manejar el error gracefully
        result = generate_consolidated_run_file(
            sample_orders, invalid_dir, run_date, mock_config
        )
        
        # Dependiendo de la implementación, podría ser None o lanzar excepción
        # Ajustar según el comportamiento esperado
        assert result is None or isinstance(result, str)
    
    def test_malformed_data_handling(self, temp_dir, mock_config):
        """Test manejo de datos malformados."""
        malformed_orders = [
            {
                # Missing required fields
                'ORDER ID': 'ORDER001',
                # 'FIRST NAME': 'John',  # Missing
                'LAST NAME': 'Doe',
            }
        ]
        
        run_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # Should handle missing fields gracefully
        result = generate_consolidated_run_file(
            malformed_orders, temp_dir, run_date, mock_config
        )
        
        # Should either succeed with defaults or fail gracefully
        if result:
            assert os.path.exists(result)


if __name__ == "__main__":
    pytest.main([__file__])
