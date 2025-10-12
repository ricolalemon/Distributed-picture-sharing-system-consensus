from flask import Flask, request, jsonify, send_file
import os
import json
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = '/data/pictures'
METADATA_FILE = '/data/metadata.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_metadata():
    """Load picture metadata from disk"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Save picture metadata to disk"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

metadata = load_metadata()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'node': os.environ.get('NODE_NAME', 'unknown')})

@app.route('/upload', methods=['POST'])
def upload():
    """Upload a picture to this node"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Save metadata
    metadata[filename] = {
        'likes': 0,
        'upload_time': time.time(),
        'node': os.environ.get('NODE_NAME', 'unknown')
    }
    save_metadata(metadata)
    
    return jsonify({
        'success': True,
        'filename': filename,
        'node': os.environ.get('NODE_NAME', 'unknown')
    })

@app.route('/list', methods=['GET'])
def list_pictures():
    """List all pictures on this node"""
    return jsonify(metadata)

@app.route('/search/<filename>', methods=['GET'])
def search(filename):
    """Search for a picture by filename"""
    if filename in metadata:
        return jsonify({
            'found': True,
            'filename': filename,
            'node': os.environ.get('NODE_NAME', 'unknown'),
            'likes': metadata[filename]['likes']
        })
    return jsonify({'found': False})

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    """Download a picture from this node"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/delete/<filename>', methods=['DELETE'])
def delete(filename):
    """Delete a picture from this node"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        if filename in metadata:
            del metadata[filename]
            save_metadata(metadata)
        return jsonify({'success': True})
    return jsonify({'error': 'File not found'}), 404

@app.route('/like/<filename>', methods=['POST'])
def like(filename):
    """Increment like count for a picture"""
    if filename in metadata:
        metadata[filename]['likes'] += 1
        save_metadata(metadata)
        return jsonify({
            'success': True,
            'likes': metadata[filename]['likes']
        })
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)