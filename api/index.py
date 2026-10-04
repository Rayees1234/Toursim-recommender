"""
Vercel Serverless Function entry point for Tourism Data Warehouse & Mining System.
Exports the WSGI Flask `app` object for serverless invocation.
"""

import os
import sys

# Ensure project root is available in module search path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Signal Vercel environment
os.environ["VERCEL"] = "1"

# Import Flask application instance
from app.app import app

# Export for Vercel WSGI
app = app
