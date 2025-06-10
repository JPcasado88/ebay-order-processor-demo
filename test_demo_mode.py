#!/usr/bin/env python3
"""
Demo Mode Test Script
====================

Quick script to test demo mode functionality locally.
This script sets up the environment and tests the demo features.

Usage:
    python test_demo_mode.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def setup_demo_environment():
    """Set up the demo environment for testing."""
    print("🔧 Setting up demo environment...")
    
    # Copy demo environment file to .env
    env_demo_path = Path('env.demo')
    env_path = Path('.env')
    
    if env_demo_path.exists():
        shutil.copy(env_demo_path, env_path)
        print(f"  ✅ Copied {env_demo_path} to {env_path}")
    else:
        print(f"  ❌ {env_demo_path} not found!")
        return False
    
    # Ensure required directories exist
    directories = ['output', 'flask_session', 'logs', 'data/processes', 'data/sessions']
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Created directory: {dir_path}")
    
    # Check if demo data files exist
    demo_files = [
        'data/ebay_tokens_demo.json',
        'data/sample_product_data.csv'
    ]
    
    all_demo_files_exist = True
    for file_path in demo_files:
        if Path(file_path).exists():
            print(f"  ✅ Demo file exists: {file_path}")
        else:
            print(f"  ❌ Demo file missing: {file_path}")
            all_demo_files_exist = False
    
    return all_demo_files_exist

def test_demo_data():
    """Test that demo data is working correctly."""
    print("\n📊 Testing demo data...")
    
    try:
        # Test demo data service
        from ebay_processor.services.demo_data import DemoDataService
        
        demo_service = DemoDataService()
        stats = demo_service.get_demo_statistics()
        
        print(f"  ✅ Demo orders: {stats['total_orders']}")
        print(f"  ✅ Demo items: {stats['total_items']}")
        print(f"  ✅ Demo stores: {len(stats['stores'])}")
        print(f"  ✅ Total value: £{stats['total_value']}")
        
        # Test demo orders for each store
        for store in stats['stores']:
            orders = demo_service.get_sample_orders(store, 7)
            print(f"  ✅ {store}: {len(orders)} orders")
        
        return True
    except Exception as e:
        print(f"  ❌ Error testing demo data: {e}")
        return False

def test_config():
    """Test that the configuration is loaded correctly."""
    print("\n⚙️  Testing configuration...")
    
    try:
        from ebay_processor.config import Config
        
        config = Config()
        
        print(f"  ✅ DEMO_MODE: {config.DEMO_MODE}")
        print(f"  ✅ Using demo tokens: {config.EBAY_CONFIG_JSON_PATH}")
        print(f"  ✅ Using demo product data: {config.MATLIST_CSV_PATH}")
        print(f"  ✅ Demo stores: {len(config.EBAY_STORE_ACCOUNTS)}")
        
        return config.DEMO_MODE
    except Exception as e:
        print(f"  ❌ Error testing configuration: {e}")
        return False

def run_demo_mode_tests():
    """Run comprehensive demo mode tests."""
    print("🎪 eBay Order Processor - Demo Mode Test")
    print("=" * 50)
    
    # Step 1: Setup environment
    if not setup_demo_environment():
        print("\n❌ Failed to set up demo environment!")
        return False
    
    # Step 2: Test configuration
    if not test_config():
        print("\n❌ Demo mode not properly configured!")
        return False
    
    # Step 3: Test demo data
    if not test_demo_data():
        print("\n❌ Demo data not working correctly!")
        return False
    
    # All tests passed
    print("\n" + "=" * 50)
    print("✅ All demo mode tests passed!")
    print("\n🚀 You can now run the application in demo mode:")
    print("   python run.py")
    print("\n💡 Login credentials for demo:")
    print("   Username: demo")
    print("   Password: demo123")
    print("\n🎯 Demo features:")
    print("   • Sample orders from 3 demo stores")
    print("   • Full SKU matching algorithm demonstration")
    print("   • Real Excel file generation with demo data")
    print("   • All processing features work without real eBay API")
    
    return True

if __name__ == '__main__':
    success = run_demo_mode_tests()
    sys.exit(0 if success else 1) 