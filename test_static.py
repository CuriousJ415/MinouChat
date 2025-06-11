from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return '<img src="/static/images/ai_face_glow.jpg">'

if __name__ == '__main__':
    app.run(port=5001) 