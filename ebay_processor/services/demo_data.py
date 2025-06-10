"""
Demo Data Service
=================

Provides realistic sample order data for demo mode.
This data is designed to showcase the complexity of the SKU matching algorithm
and file generation capabilities without exposing real client data.
"""

from datetime import datetime, timedelta
import random


class DemoDataService:
    """Service for providing demo order data that showcases system capabilities."""
    
    def __init__(self):
        self.demo_orders = self._generate_demo_orders()
    
    def get_sample_orders(self, store_name='demo_store_1', days_back=7):
        """
        Get sample orders for demo mode.
        Returns realistic order data that will trigger various SKU matching scenarios.
        """
        # Filter orders for the requested store and date range
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        store_orders = [
            order for order in self.demo_orders 
            if order['Store'] == store_name and 
            datetime.strptime(order['CreatedTime'], '%Y-%m-%dT%H:%M:%S.%fZ') >= cutoff_date
        ]
        
        return store_orders
    
    def _generate_demo_orders(self):
        """Generate realistic demo orders that showcase algorithm complexity."""
        
        base_date = datetime.now() - timedelta(days=3)
        
        demo_orders = [
            # Order 1: Direct SKU match - Toyota Camry
            {
                'OrderID': 'DEMO-001-2024-001',
                'Store': 'demo_store_1',
                'BuyerName': 'John Smith',
                'BuyerAddress': {
                    'Name': 'John Smith',
                    'Street1': '123 Main Street',
                    'CityName': 'London',
                    'PostalCode': 'SW1A 1AA',
                    'Country': 'GB'
                },
                'OrderTotal': '45.99',
                'CreatedTime': (base_date + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'Items': [{
                    'ItemID': '123456789',
                    'Title': 'Toyota Camry Car Floor Mats 2020-2025 Tailored Set of 4 Black Carpet',
                    'SKU': 'SAMPLE-TOY-001',
                    'Quantity': 1,
                    'Price': '45.99'
                }]
            },
            
            # Order 2: Complex title matching - BMW 3 Series  
            {
                'OrderID': 'DEMO-002-2024-001',
                'Store': 'demo_store_1', 
                'BuyerName': 'Sarah Johnson',
                'BuyerAddress': {
                    'Name': 'Sarah Johnson',
                    'Street1': '456 Oak Avenue',
                    'CityName': 'Manchester',
                    'PostalCode': 'M1 1AA',
                    'Country': 'GB'
                },
                'OrderTotal': '52.99',
                'CreatedTime': (base_date + timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'Items': [{
                    'ItemID': '234567890',
                    'Title': 'BMW 3 Series E90 E91 E92 E93 2005-2012 Custom Fit Car Mats Black Velour',
                    'SKU': 'BMW-3SER-VELOUR-4PC',
                    'Quantity': 1, 
                    'Price': '52.99'
                }]
            },
            
            # Order 3: Multi-item order - Audi A4
            {
                'OrderID': 'DEMO-003-2024-001',
                'Store': 'demo_store_2',
                'BuyerName': 'Michael Brown',
                'BuyerAddress': {
                    'Name': 'Michael Brown',
                    'Street1': '789 Pine Road',
                    'CityName': 'Birmingham',
                    'PostalCode': 'B1 1AA',
                    'Country': 'GB'
                },
                'OrderTotal': '89.98',
                'CreatedTime': (base_date + timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'Items': [
                    {
                        'ItemID': '345678901',
                        'Title': 'Audi A4 B8 2008-2015 Premium Car Floor Mats Set',
                        'SKU': 'SAMPLE-AUD-001',
                        'Quantity': 1,
                        'Price': '48.99'
                    },
                    {
                        'ItemID': '345678902', 
                        'Title': 'Audi A4 B8 Boot Mat Carpet Liner 2008-2015',
                        'SKU': 'AUD-A4-BOOT-001',
                        'Quantity': 1,
                        'Price': '40.99'
                    }
                ]
            },
            
            # Order 4: Year range challenge - Ford Focus
            {
                'OrderID': 'DEMO-004-2024-001',
                'Store': 'demo_store_2',
                'BuyerName': 'Emma Wilson',
                'BuyerAddress': {
                    'Name': 'Emma Wilson',
                    'Street1': '321 Elm Street',
                    'CityName': 'Liverpool',
                    'PostalCode': 'L1 1AA',
                    'Country': 'GB'
                },
                'OrderTotal': '41.99',
                'CreatedTime': (base_date + timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'Items': [{
                    'ItemID': '456789012',
                    'Title': 'Ford Focus MK4 2018-2024 Hatchback Car Mats Full Set Black',
                    'SKU': 'FORD-FOC-MK4-SET',
                    'Quantity': 1,
                    'Price': '41.99'
                }]
            },
            
            # Order 5: Tricky SKU extraction - Mercedes C-Class
            {
                'OrderID': 'DEMO-005-2024-001', 
                'Store': 'demo_store_3',
                'BuyerName': 'David Taylor',
                'BuyerAddress': {
                    'Name': 'David Taylor',
                    'Street1': '654 Maple Drive',
                    'CityName': 'Leeds',
                    'PostalCode': 'LS1 1AA',
                    'Country': 'GB'
                },
                'OrderTotal': '67.99',
                'CreatedTime': (base_date + timedelta(hours=18)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'Items': [{
                    'ItemID': '567890123',
                    'Title': 'Mercedes C Class W205 2014-2021 AMG Line Premium Carpet Car Mats',
                    'SKU': 'MER-C205-PREMIUM',
                    'Quantity': 1,
                    'Price': '67.99'
                }]
            },
            
            # Order 6: VW Golf - Multiple generations
            {
                'OrderID': 'DEMO-006-2024-001',
                'Store': 'demo_store_3', 
                'BuyerName': 'Lisa Anderson',
                'BuyerAddress': {
                    'Name': 'Lisa Anderson',
                    'Street1': '987 Cedar Lane',
                    'CityName': 'Edinburgh',
                    'PostalCode': 'EH1 1AA',
                    'Country': 'GB'
                },
                'OrderTotal': '38.99',
                'CreatedTime': (base_date + timedelta(hours=22)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'Items': [{
                    'ItemID': '678901234',
                    'Title': 'VW Golf MK7 2012-2020 5 Door Hatchback Tailored Car Floor Mats',
                    'SKU': 'SAMPLE-VW-001',
                    'Quantity': 1,
                    'Price': '38.99'
                }]
            },
            
            # Order 7: Honda Civic - Color specification
            {
                'OrderID': 'DEMO-007-2024-001',
                'Store': 'demo_store_1',
                'BuyerName': 'Robert Garcia',
                'BuyerAddress': {
                    'Name': 'Robert Garcia', 
                    'Street1': '147 Birch Avenue',
                    'CityName': 'Glasgow',
                    'PostalCode': 'G1 1AA',
                    'Country': 'GB'
                },
                'OrderTotal': '43.99',
                'CreatedTime': (base_date + timedelta(days=1, hours=3)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'Items': [{
                    'ItemID': '789012345',
                    'Title': 'Honda Civic 2016-2022 Type R Custom Car Mats Grey Binding',
                    'SKU': 'SAMPLE-HON-001',
                    'Quantity': 1,
                    'Price': '43.99'
                }]
            },
            
            # Order 8: Nissan Altima - US market
            {
                'OrderID': 'DEMO-008-2024-001',
                'Store': 'demo_store_2',
                'BuyerName': 'Jennifer Martinez',
                'BuyerAddress': {
                    'Name': 'Jennifer Martinez',
                    'Street1': '258 Willow Court',
                    'CityName': 'Cardiff',
                    'PostalCode': 'CF1 1AA',
                    'Country': 'GB'
                },
                'OrderTotal': '39.99',
                'CreatedTime': (base_date + timedelta(days=1, hours=8)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'Items': [{
                    'ItemID': '890123456',
                    'Title': 'Nissan Altima 2019-2025 Sedan Premium Floor Mat Set Black',
                    'SKU': 'SAMPLE-NIS-001',
                    'Quantity': 1,
                    'Price': '39.99'
                }]
            }
        ]
        
        return demo_orders
    
    def get_demo_statistics(self):
        """Get statistics about the demo data for display purposes."""
        total_orders = len(self.demo_orders)
        total_items = sum(len(order['Items']) for order in self.demo_orders)
        total_value = sum(float(order['OrderTotal']) for order in self.demo_orders)
        
        stores = list(set(order['Store'] for order in self.demo_orders))
        
        return {
            'total_orders': total_orders,
            'total_items': total_items,
            'total_value': round(total_value, 2),
            'stores': stores,
            'date_range': '7 days',
            'sample_skus': [
                'SAMPLE-TOY-001', 'BMW-3SER-VELOUR-4PC', 'SAMPLE-AUD-001',
                'FORD-FOC-MK4-SET', 'MER-C205-PREMIUM', 'SAMPLE-VW-001'
            ]
        } 