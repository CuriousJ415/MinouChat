from fastapi import Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Dict, Any
from .flash import get_flashed_messages

# Get the templates directory path
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Create Jinja2Templates instance
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Template mapping for routes
TEMPLATE_MAPPING = {
    # Main pages
    "index": "index.html",
    "landing": "landing.html",
    "dashboard": "dashboard.html",
    "chat/index": "chat/index.html",
    "settings": "settings.html",
    "config": "config.html",
    "first_time_setup": "first_time_setup.html",
    
    # Setup pages
    "setup/wizard": "setup/wizard.html",
    
    # Persona pages
    "persona/list": "persona/list.html",
    "persona/view": "persona/view.html",
    "persona/create": "persona/create.html",
    "persona/edit": "persona/edit.html",
    
    # Auth pages
    "login": "auth/login.html",
    "register": "auth/register.html",
}

def get_template_context(request: Request, **kwargs) -> Dict[str, Any]:
    """Get the base template context with utility functions."""
    context = {
        "request": request,
        "get_flashed_messages": get_flashed_messages,
        "url_for": lambda endpoint, **url_kwargs: f"/{endpoint}",  # Simple URL generator
    }
    context.update(kwargs)
    return context

async def render_template(request: Request, template_name: str, **kwargs):
    """
    Render a template with the given context.
    
    Args:
        request: The FastAPI request object
        template_name: The name of the template to render
        **kwargs: Additional context variables for the template
    """
    if template_name not in TEMPLATE_MAPPING:
        raise ValueError(f"Template {template_name} not found in mapping")
    
    context = get_template_context(request, **kwargs)
    
    return templates.TemplateResponse(
        TEMPLATE_MAPPING[template_name],
        context
    ) 