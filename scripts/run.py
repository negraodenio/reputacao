"""
Development server launcher.
Usage: python scripts/run.py
"""
import sys
import os

# Ensure the project root is on the Python path so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
