import requests
import grpc
import picture_pb2
import picture_pb2_grpc
import time
import statistics
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

HTTP_NODES = ['http://localhost:5001', 'http://localhost:5002', 'http://localhost:5003']
GRPC_NODES = ['localhost:50051', 'localhost:50052', 'localhost:50053']

def generate_test_image(size_kb=10):
    """Generate a test image of specified size"""
    return b'0' * (size_kb * 1024)

def random_filename():
    """Generate random filename"""
    return ''.join(random.choices(string.ascii_lowercase, k=8)) + '.jpg'

class HTTPBenchmark:
    """Benchmark HTTP implementation"""
    
    def upload(self, filename, data):
        node = random.choice(HTTP_NODES)
        start = time.time()
        files = {'file': (filename, io.BytesIO(data), 'image/jpeg')}
        response = requests.post(f'{node}/upload', files=files)
        latency = (time.time() - start) * 1000
        return latency, response.status_code == 200
    
    def search(self, filename):
        start = time.time()
        for node in HTTP_NODES:
            try:
                response = requests.get(f'{node}/search/{filename}', timeout=2)
                if response.json().get('found'):
                    latency = (time.time() - start) * 1000
                    return latency, True
            except:
                pass
        latency = (time.time() - start) * 1000
        return latency, False
    
    def download(self, filename):
        start = time.time()
        for node in HTTP_NODES:
            try:
                response = requests.get(f'{node}/download/{filename}', timeout=5)
                if response.status_code == 200:
                    latency = (time.time() - start) * 1000
                    return latency, True
            except:
                pass
        latency = (time.time() - start) * 1000
        return latency, False
    
    def delete(self, filename):
        start = time.time()
        for node in HTTP_NODES:
            try:
                response = requests.delete(f'{node}/delete/{filename}', timeout=2)
                if response.json().get('success'):
                    latency = (time.time() - start) * 1000
                    return latency, True
            except:
                pass
        latency = (time.time() - start) * 1000
        return latency, False
    
    def like(self, filename):
        start = time.time()
        for node in HTTP_NODES:
            try:
                response = requests.post(f'{node}/like/{filename}', timeout=2)
                if response.json().get('success'):
                    latency = (time.time() - start) * 1000
                    return latency, True
            except:
                pass
        latency = (time.time() - start) * 1000
        return latency, False

class GRPCBenchmark:
    """Benchmark gRPC implementation"""
    
    def upload(self, filename, data):
        node = random.choice(GRPC_NODES)
        channel = grpc.insecure_channel(node)
        stub = picture_pb2_grpc.PictureServiceStub(channel)
        
        start = time.time()
        response = stub.Upload(picture_pb2.UploadRequest(filename=filename, data=data))
        latency = (time.time() - start) * 1000
        return latency, response.success
    
    def search(self, filename):
        start = time.time()
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.Search(picture_pb2.SearchRequest(filename=filename))
                if response.found:
                    latency = (time.time() - start) * 1000
                    return latency, True
            except:
                pass
        latency = (time.time() - start) * 1000
        return latency, False
    
    def download(self, filename):
        start = time.time()
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.Download(picture_pb2.DownloadRequest(filename=filename))
                if response.found:
                    latency = (time.time() - start) * 1000
                    return latency, True
            except:
                pass
        latency = (time.time() - start) * 1000
        return latency, False
    
    def delete(self, filename):
        start = time.time()
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.Delete(picture_pb2.DeleteRequest(filename=filename))
                if response.success:
                    latency = (time.time() - start) * 1000
                    return latency, True
            except:
                pass
        latency = (time.time() - start) * 1000
        return latency, False
    
    def like(self, filename):
        start = time.time()
        for node in GRPC_NODES:
            try:
                channel = grpc.insecure_channel(node)
                stub = picture_pb2_grpc.PictureServiceStub(channel)
                response = stub.Like(picture_pb2.LikeRequest(filename=filename))
                if response.success:
                    latency = (time.time() - start) * 1000
                    return latency, True
            except:
                pass
        latency = (time.time() - start) * 1000
        return latency, False

def run_benchmark(benchmark_class, num_requests=100):
    """Run benchmark for a specific implementation"""
    bench = benchmark_class()
    results = {
        'upload': [],
        'search': [],
        'download': [],
        'delete': [],
        'like': []
    }
    
    print(f"\nRunning {benchmark_class.__name__} with {num_requests} requests...")
    
    # Upload test
    print("Testing upload...")
    test_files = []
    for i in range(num_requests):
        filename = random_filename()
        data = generate_test_image()
        latency, success = bench.upload(filename, data)
        if success:
            results['upload'].append(latency)
            test_files.append(filename)
    
    # Search test
    print("Testing search...")
    for filename in test_files[:min(50, len(test_files))]:
        latency, success = bench.search(filename)
        if success:
            results['search'].append(latency)
    
    # Download test
    print("Testing download...")
    for filename in test_files[:min(50, len(test_files))]:
        latency, success = bench.download(filename)
        if success:
            results['download'].append(latency)
    
    # Like test
    print("Testing like...")
    for filename in test_files[:min(50, len(test_files))]:
        latency, success = bench.like(filename)
        if success:
            results['like'].append(latency)
    
    # Delete test
    print("Testing delete...")
    for filename in test_files:
        latency, success = bench.delete(filename)
        if success:
            results['delete'].append(latency)
    
    return results

def print_results(name, results):
    """Print benchmark results"""
    print(f"\n{'='*60}")
    print(f"{name} Results")
    print(f"{'='*60}")
    
    for operation, latencies in results.items():
        if latencies:
            avg = statistics.mean(latencies)
            median = statistics.median(latencies)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            throughput = len(latencies) / (sum(latencies) / 1000)
            
            print(f"\n{operation.upper()}:")
            print(f"  Requests: {len(latencies)}")
            print(f"  Avg Latency: {avg:.2f} ms")
            print(f"  Median Latency: {median:.2f} ms")
            print(f"  P95 Latency: {p95:.2f} ms")
            print(f"  Throughput: {throughput:.2f} ops/sec")
        else:
            print(f"\n{operation.upper()}: No successful requests")

if __name__ == '__main__':
    print("Distributed Picture Sharing System - Benchmark Tool")
    print("="*60)
    
    # HTTP Benchmark
    http_results = run_benchmark(HTTPBenchmark, num_requests=50)
    print_results("HTTP (Layered Architecture)", http_results)
    
    # gRPC Benchmark
    grpc_results = run_benchmark(GRPCBenchmark, num_requests=50)
    print_results("gRPC (Microservices)", grpc_results)
    
    print(f"\n{'='*60}")
    print("Benchmark completed!")
    print(f"{'='*60}\n")