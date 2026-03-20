"""
Vercel serverless entry point.
Imports the FastAPI app from the backend directory.
"""
import sys
import os

# Make the backend package importable when running as a Vercel function
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from main import app  # noqa: F401  — Vercel detects the ASGI app automatically
