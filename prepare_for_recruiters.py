#!/usr/bin/env python3
"""
Recruiter Preparation Script
============================

This script helps prepare the eBay Order Processor for recruiter presentation
by ensuring all sensitive data is properly sanitized or removed.

Usage:
    python prepare_for_recruiters.py

What this script does:
- Verifies sensitive files are not present
- Creates/updates demo data files
- Cleans temporary directories
- Provides checklist for manual review
"""

import os
import shutil
import json
from pathlib import Path

class RecruiterPrepTool:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.sensitive_files = [
            'data/ebay_tokens.json',
            'data/ktypemaster3.csv',
            '.env',
            '.env.local',
            '.env.production'
        ]
        self.directories_to_clean = [
            'logs',
            'output',
            'flask_session',
            'data/processes',
            'data/sessions'
        ]
    
    def check_sensitive_files(self):
        """Check if any sensitive files exist and warn about them."""
        print("🔍 Checking for sensitive files...")
        found_sensitive = []
        
        for file_path in self.sensitive_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                found_sensitive.append(file_path)
                print(f"  ⚠️  FOUND: {file_path}")
        
        if found_sensitive:
            print(f"\n❌ Found {len(found_sensitive)} sensitive files!")
            print("   These files contain real client/API data and should not be shared.")
            print("   Consider moving them to a backup location or renaming them.")
            return False
        else:
            print("  ✅ No sensitive files found")
            return True
    
    def clean_directories(self):
        """Clean temporary and output directories."""
        print("\n🧹 Cleaning temporary directories...")
        
        for dir_name in self.directories_to_clean:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                try:
                    # Remove all contents but keep the directory
                    for item in dir_path.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    print(f"  ✅ Cleaned: {dir_name}/")
                except Exception as e:
                    print(f"  ⚠️  Could not clean {dir_name}/: {e}")
            else:
                print(f"  ℹ️  Directory not found: {dir_name}/")
    
    def ensure_demo_files(self):
        """Ensure demo/sample files exist."""
        print("\n📝 Checking demo files...")
        
        # Check demo tokens file
        demo_tokens_path = self.project_root / 'data/ebay_tokens_demo.json'
        if not demo_tokens_path.exists():
            print("  ⚠️  Creating demo tokens file...")
            demo_tokens = {
                "demo_store_1": {
                    "access_token": "v^1.1#i^1#r^0#f^0#I^3#[DEMO_TOKEN_PLACEHOLDER_FOR_STORE_1]",
                    "expiry_time": "2025-12-31T23:59:59.000000+00:00"
                },
                "demo_store_2": {
                    "access_token": "v^1.1#i^1#f^0#p^3#r^0#I^3#[DEMO_TOKEN_PLACEHOLDER_FOR_STORE_2]",
                    "expiry_time": "2025-12-31T23:59:59.000000+00:00"
                }
            }
            with open(demo_tokens_path, 'w') as f:
                json.dump(demo_tokens, f, indent=4)
            print("  ✅ Created demo tokens file")
        else:
            print("  ✅ Demo tokens file exists")
        
        # Check sample data file
        sample_data_path = self.project_root / 'data/sample_product_data.csv'
        if sample_data_path.exists():
            print("  ✅ Sample product data exists")
        else:
            print("  ⚠️  Sample product data file missing")
    
    def check_gitignore(self):
        """Verify .gitignore is properly configured."""
        print("\n🚫 Checking .gitignore configuration...")
        
        gitignore_path = self.project_root / '.gitignore'
        if not gitignore_path.exists():
            print("  ❌ .gitignore file missing!")
            return False
        
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
        
        required_patterns = [
            '.env',
            'data/ebay_tokens.json',
            'data/ktypemaster3.csv',
            'logs/',
            'output/'
        ]
        
        missing_patterns = []
        for pattern in required_patterns:
            if pattern not in gitignore_content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print(f"  ⚠️  Missing gitignore patterns: {missing_patterns}")
            return False
        else:
            print("  ✅ .gitignore properly configured")
            return True
    
    def final_checklist(self):
        """Display final manual checklist."""
        print("\n" + "="*50)
        print("📋 FINAL RECRUITER PREPARATION CHECKLIST")
        print("="*50)
        
        checklist_items = [
            "✅ All sensitive files removed or renamed",
            "✅ Demo data files are in place",
            "✅ Temporary directories cleaned",
            "✅ .gitignore properly configured",
            "📖 README_RECRUITERS.md explains the demo nature",
            "🔍 Code review: no hardcoded secrets in source files",
            "🌐 Consider creating GitHub repository for easy sharing",
            "📧 Prepare elevator pitch about the project's complexity",
            "💼 Highlight: Production-ready architecture patterns",
            "🚀 Mention: Handles real business with thousands of orders"
        ]
        
        for item in checklist_items:
            print(f"  {item}")
        
        print("\n" + "="*50)
        print("🎯 KEY SELLING POINTS FOR RECRUITERS:")
        print("="*50)
        print("• Complex API integration with OAuth2 token management")
        print("• Advanced algorithms (19-case SKU matching system)")
        print("• Production-ready architecture (Flask factory pattern)")
        print("• Asynchronous background processing")
        print("• Real business impact (processes actual e-commerce orders)")
        print("• Cloud deployment ready (Railway/Heroku/AWS)")
        print("• Comprehensive testing suite")
        print("• Security best practices implemented")
    
    def run(self):
        """Run the complete preparation process."""
        print("🚀 eBay Order Processor - Recruiter Preparation Tool")
        print("="*52)
        
        sensitive_check = self.check_sensitive_files()
        self.clean_directories()
        self.ensure_demo_files()
        gitignore_check = self.check_gitignore()
        
        print("\n" + "="*52)
        if sensitive_check and gitignore_check:
            print("✅ PROJECT IS RECRUITER-READY!")
            print("   All sensitive data has been properly handled.")
        else:
            print("⚠️  PROJECT NEEDS ATTENTION!")
            print("   Please address the issues mentioned above.")
        
        self.final_checklist()

if __name__ == '__main__':
    tool = RecruiterPrepTool()
    tool.run() 