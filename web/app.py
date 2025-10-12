from flask import Flask, render_template, request, jsonify, send_file
import requests
import grpc
import picture_pb2
import picture_pb2_grpc
import random
import io
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

HTTP_NODES = [
    'http://http-node1:5000',
    'http://http-node2:5000',
    'http://http-node3:5000'
]

GRPC_NODES = [
    'grpc-node1:50051',
    'grpc-node2:50051',
    'grpc-node3:50051'
]

logs = []

def add_log(message):
    """Add a log message with timestamp"""
    logs.append({
        'time': time.strftime('%H:%M:%S'),
        'message': message
    })
    if len(logs) > 100:
        logs.pop(0)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def get_logs():
    """Get recent logs"""
    return jsonify(logs)

@app.route('/upload', methods=['POST'])
def upload():
    """Upload picture to a random node"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    strategy = request.form.get('strategy', 'http')
    
    if strategy == 'http':
        node = random.choice(HTTP_NODES)
        files = {'file': (file.filename, file.stream, file.mimetype)}
        response = requests.post(f'{node}/upload', files=files)
        result = response.json()
        add_log(f"Uploaded {file.filename} to HTTP node {result.get('node')}")
        return jsonify(result)
    
    elif strategy == 'grpc':
        node = random.choice(GRPC_NODES)
        channel = grpc.insecure_channel(node)
        stub = picture_pb2_grpc.PictureServiceStub(channel)
        
        data = file.read()
        response = stub.Upload(picture_pb2.UploadRequest(
            filename=file.filename,
            data=data
        ))
        add_log(f"Uploaded {file.filename} to gRPC node {response.node}")
        return jsonify({'success': response.success, 'node': response.node})

@app.route('/list')
def list_pictures():
    """List all pictures from all nodes"""
    strategy = request.args.get('strategy', 'http')
    all_pictures = {}
    
    if strategy == 'http':
        for node in HTTP_NODES:
            try:
                response = requests.get(f'{node}/list', timeout=2)
                pictures = response.json()
                for filename, meta in pictures.items():
                    all_pictures[filename] = meta
            except:
                pass
    
    elif strategy == 'grpc':
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.List(picture_pb2.ListRequest())
                for filename, meta in response.pictures.items():
                    all_pictures[filename] = {
                        'likes': meta.likes,
                        'node': meta.node
                    }
            except:
                pass
    
    return jsonify(all_pictures)

@app.route('/search/<filename>')
def search(filename):
    """Search for a picture across all nodes"""
    strategy = request.args.get('strategy', 'http')
    
    if strategy == 'http':
        for node in HTTP_NODES:
            try:
                response = requests.get(f'{node}/search/{filename}', timeout=2)
                result = response.json()
                if result.get('found'):
                    add_log(f"Found {filename} on HTTP node {result['node']}")
                    return jsonify(result)
            except:
                pass
    
    elif strategy == 'grpc':
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.Search(picture_pb2.SearchRequest(filename=filename))
                if response.found:
                    add_log(f"Found {filename} on gRPC node {response.node}")
                    return jsonify({
                        'found': True,
                        'node': response.node,
                        'likes': response.likes
                    })
            except:
                pass
    
    add_log(f"Picture {filename} not found")
    return jsonify({'found': False})

@app.route('/download/<filename>')
def download(filename):
    """Download a picture"""
    strategy = request.args.get('strategy', 'http')
    
    if strategy == 'http':
        for node in HTTP_NODES:
            try:
                response = requests.get(f'{node}/download/{filename}', timeout=5)
                if response.status_code == 200:
                    add_log(f"Downloaded {filename} from HTTP node")
                    return send_file(
                        io.BytesIO(response.content),
                        as_attachment=True,
                        download_name=filename
                    )
            except:
                pass
    
    elif strategy == 'grpc':
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.Download(picture_pb2.DownloadRequest(filename=filename))
                if response.found:
                    add_log(f"Downloaded {filename} from gRPC node")
                    return send_file(
                        io.BytesIO(response.data),
                        as_attachment=True,
                        download_name=filename
                    )
            except:
                pass
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/delete/<filename>', methods=['DELETE'])
def delete(filename):
    """Delete a picture"""
    strategy = request.args.get('strategy', 'http')
    
    if strategy == 'http':
        for node in HTTP_NODES:
            try:
                response = requests.delete(f'{node}/delete/{filename}', timeout=2)
                if response.json().get('success'):
                    add_log(f"Deleted {filename} from HTTP node")
                    return jsonify({'success': True})
            except:
                pass
    
    elif strategy == 'grpc':
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.Delete(picture_pb2.DeleteRequest(filename=filename))
                if response.success:
                    add_log(f"Deleted {filename} from gRPC node")
                    return jsonify({'success': True})
            except:
                pass
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/like/<filename>', methods=['POST'])
def like(filename):
    """Like a picture"""
    strategy = request.args.get('strategy', 'http')
    
    if strategy == 'http':
        for node in HTTP_NODES:
            try:
                response = requests.post(f'{node}/like/{filename}', timeout=2)
                result = response.json()
                if result.get('success'):
                    add_log(f"Liked {filename}, total likes: {result['likes']}")
                    return jsonify(result)
            except:
                pass
    
    elif strategy == 'grpc':
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.Like(picture_pb2.LikeRequest(filename=filename))
                if response.success:
                    add_log(f"Liked {filename}, total likes: {response.likes}")
                    return jsonify({'success': True, 'likes': response.likes})
            except:
                pass
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/benchmark', methods=['POST'])
def benchmark():
    """Run benchmark tests"""
    data = request.json
    strategy = data.get('strategy', 'http')
    workload = data.get('workload', 100)
    
    results = {
        'upload': {'latency': [], 'throughput': 0},
        'search': {'latency': [], 'throughput': 0},
        'download': {'latency': [], 'throughput': 0},
        'delete': {'latency': [], 'throughput': 0},
        'like': {'latency': [], 'throughput': 0}
    }
    
    add_log(f"Starting benchmark: {strategy} strategy, {workload} requests")
    
    # Simple benchmark implementation
    # In production, use proper benchmarking tools
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)