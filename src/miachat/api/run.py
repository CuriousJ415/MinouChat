import uvicorn
from miachat.api.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5050,
        reload=True
    ) 