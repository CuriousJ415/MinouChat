from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Get the static directory path - create it if it doesn't exist
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Create subdirectories
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)
(STATIC_DIR / "images").mkdir(exist_ok=True)

def mount_static_files(app):
    """
    Mount static file directories to the FastAPI app.
    
    Args:
        app: The FastAPI application instance
    """
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static") 