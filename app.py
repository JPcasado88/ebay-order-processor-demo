#!/usr/bin/env python3
"""
Railway deployment entry point for eBay Order Processor Demo.

This file creates the Flask application instance for production deployment
on Railway platform. It uses the same application factory pattern as run.py
but is optimized for production hosting.
"""

import os
import logging
from ebay_processor import create_app

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask application instance
app = create_app()

if __name__ == '__main__':
    # This won't be used in Railway (gunicorn handles it)
    # but useful for local testing with: python app.py
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 