import os
from flask import Blueprint, request, jsonify, current_app
from app.services.knowledge_service import save_document, list_documents

bp = Blueprint('knowledge_base', __name__, url_prefix='/knowledge-base')

@bp.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filepath = save_document(file)
    return jsonify({'message': 'File uploaded successfully', 'path': filepath})

@bp.route('/list', methods=['GET'])
def list_files():
    docs = list_documents()
    return jsonify({'documents': docs})
