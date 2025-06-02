import os
from datetime import datetime
from app.utils.chunking import simple_chunk_text

UPLOAD_FOLDER = 'uploads'
CHUNKED_FOLDER = 'uploads/chunked'

def save_document(file):
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(CHUNKED_FOLDER):
        os.makedirs(CHUNKED_FOLDER)

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # 문서 청킹 및 저장
    process_document(filepath)

    return filepath

def list_documents():
    if not os.path.exists(UPLOAD_FOLDER):
        return []
    return os.listdir(UPLOAD_FOLDER)

def process_document(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = simple_chunk_text(text, max_chunk_size=1000)

    base_filename = os.path.basename(filepath)
    name, _ = os.path.splitext(base_filename)
    chunk_dir = os.path.join(CHUNKED_FOLDER, name)

    if not os.path.exists(chunk_dir):
        os.makedirs(chunk_dir)

    for i, chunk in enumerate(chunks):
        chunk_filename = f"{name}_chunk{i+1}.txt"
        metadata = {
            "source_file": base_filename,
            "chunk_index": i+1,
            "created_at": datetime.now().isoformat()
        }

        chunk_path = os.path.join(chunk_dir, chunk_filename)
        with open(chunk_path, "w", encoding="utf-8") as cf:
            cf.write(chunk)

        # 나중에 메타데이터도 JSON 형태로 저장 가능
        meta_path = chunk_path.replace(".txt", ".meta.json")
        with open(meta_path, "w", encoding="utf-8") as mf:
            import json
            json.dump(metadata, mf, indent=2, ensure_ascii=False)
