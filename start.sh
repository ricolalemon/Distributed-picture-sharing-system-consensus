#!/bin/bash

echo "Starting Distributed Picture Sharing System..."

# Generate gRPC code
echo "Generating gRPC code..."
cd grpc_nodes
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. picture.proto

# Copy gRPC files to web directory
echo "Copying gRPC files to web directory..."
cp picture_pb2.py picture_pb2_grpc.py ../web/
cd ..

# Build and start all containers
echo "Building and starting Docker containers..."
docker-compose up --build -d

echo ""
echo "System started successfully!"
echo "Web interface: http://localhost:8000"
echo "HTTP nodes: http://localhost:5001, 5002, 5003"
echo "gRPC nodes: localhost:50051, 50052, 50053"
echo ""
echo "Waiting for services to be ready..."
sleep 5
echo ""
echo "Use 'docker-compose logs -f' to view logs"
echo "Use './kill.sh' to stop all services"