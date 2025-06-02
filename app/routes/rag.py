from flask import Blueprint, request, jsonify
from app.services.rag_service import perform_rag_search

bp = Blueprint('rag', __name__, url_prefix='/rag-search')

@bp.route('', methods=['POST'])
def rag_search():
    data = request.get_json()
    query = data.get('query')
    industry = data.get('industry')

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    results = perform_rag_search(query, industry)
    return jsonify(results)
