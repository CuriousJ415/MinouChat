from fastapi import Request
from starlette.middleware.sessions import SessionMiddleware
from typing import List, Optional
import json

class FlashMessage:
    def __init__(self, message: str, category: str = "info"):
        self.message = message
        self.category = category

def get_flashed_messages(request: Request) -> List[FlashMessage]:
    """Get flash messages from the session."""
    if "flash_messages" not in request.session:
        return []
    
    messages = request.session.pop("flash_messages")
    return [FlashMessage(**msg) for msg in json.loads(messages)]

def flash(request: Request, message: str, category: str = "info") -> None:
    """Add a flash message to the session."""
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = json.dumps([])
    
    messages = json.loads(request.session["flash_messages"])
    messages.append({"message": message, "category": category})
    request.session["flash_messages"] = json.dumps(messages) 