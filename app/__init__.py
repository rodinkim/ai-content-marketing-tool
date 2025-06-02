from flask import Flask
from app.routes import rag, knowledge_base

def create_app():
    app = Flask(__name__)
    
    app.register_blueprint(rag.bp)
    app.register_blueprint(knowledge_base.bp)

    return app
