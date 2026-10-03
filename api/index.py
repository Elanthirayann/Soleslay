import sys
from pathlib import Path

# Ensure project root is on sys.path so 'app' can be imported anywhere
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import the FastAPI application
from app.main import app

# Vercel Serverless ASGI entrypoint
# The 'app' variable is detected automatically by @vercel/python
