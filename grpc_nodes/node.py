import grpc
from concurrent import futures
import os
import json
import picture_pb2
import picture_pb2_grpc

UPLOAD_FOLDER = '/data/pictures'
METADATA_FILE = '/data/metadata.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

class PictureServicer(picture_pb2_grpc.PictureServiceServicer):
    def __init__(self):
        self.metadata = load_metadata()
        self.node_name = os.environ.get('NODE_NAME', 'unknown')

    def Health(self, request, context):
        return picture_pb2.HealthResponse(status='healthy', node=self.node_name)

    def Upload(self, request, context):
        filename = request.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(request.data)
        
        self.metadata[filename] = {'likes': 0, 'node': self.node_name}
        save_metadata(self.metadata)
        
        return picture_pb2.UploadResponse(success=True, node=self.node_name)

    def Search(self, request, context):
        filename = request.filename
        if filename in self.metadata:
            return picture_pb2.SearchResponse(
                found=True,
                node=self.node_name,
                likes=self.metadata[filename]['likes']
            )
        return picture_pb2.SearchResponse(found=False)

    def Download(self, request, context):
        filename = request.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                return picture_pb2.DownloadResponse(data=f.read(), found=True)
        return picture_pb2.DownloadResponse(data=b'', found=False)

    def Delete(self, request, context):
        filename = request.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            if filename in self.metadata:
                del self.metadata[filename]
                save_metadata(self.metadata)
            return picture_pb2.DeleteResponse(success=True)
        return picture_pb2.DeleteResponse(success=False)

    def Like(self, request, context):
        filename = request.filename
        if filename in self.metadata:
            self.metadata[filename]['likes'] += 1
            save_metadata(self.metadata)
            return picture_pb2.LikeResponse(
                success=True,
                likes=self.metadata[filename]['likes']
            )
        return picture_pb2.LikeResponse(success=False, likes=0)

    def List(self, request, context):
        pictures = {}
        for filename, meta in self.metadata.items():
            pictures[filename] = picture_pb2.PictureMetadata(
                likes=meta['likes'],
                node=self.node_name
            )
        return picture_pb2.ListResponse(pictures=pictures)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    picture_pb2_grpc.add_PictureServiceServicer_to_server(
        PictureServicer(), server
    )
    server.add_insecure_port('[::]:50051')
    server.start()
    print(f"gRPC node started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()