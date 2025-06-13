import uuid
import os
from datetime import datetime
from werkzeug.utils import secure_filename

def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())

def get_file_extension(filename):
    """Get the file extension from a filename."""
    return os.path.splitext(filename)[1].lower()

def is_allowed_file(filename, allowed_extensions=None):
    """Check if a file has an allowed extension."""
    if allowed_extensions is None:
        allowed_extensions = {'.txt', '.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif'}
    return get_file_extension(filename) in allowed_extensions

def save_file(file, upload_folder):
    """Save an uploaded file and return its filename."""
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    return filename

def get_file_metadata(file_path):
    """Get metadata for a file."""
    return {
        'name': os.path.basename(file_path),
        'type': get_mime_type(file_path),
        'size': os.path.getsize(file_path),
        'url': f"/static/files/{os.path.basename(file_path)}"
    }

def get_mime_type(file_path):
    """Get the MIME type of a file."""
    ext = get_file_extension(file_path)
    mime_types = {
        '.txt': 'text/plain',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif'
    }
    return mime_types.get(ext, 'application/octet-stream') 