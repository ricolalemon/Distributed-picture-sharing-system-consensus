# ============= Project Structure =============
# distributed-picture-system/
# ├── http_nodes/
# │   ├── node.py
# │   └── Dockerfile
# ├── grpc_nodes/
# │   ├── node.py
# │   ├── picture.proto
# │   ├── picture_pb2.py
# │   └── Dockerfile
# ├── web/
# │   ├── app.py
# │   └── templates/
# │       └── index.html
# ├── docker-compose.yml
# ├── start.sh
# ├── kill.sh
# ├── benchmark.py
# └── requirements.txt


DEPENDENCY INSTALLATION
   conda create -n imgshare python=3.11 -y
   conda activate imgshare
   pip install -r requirements.txt




SETUP INSTRUCTIONS:

1. Make scripts executable:
   chmod +x start.sh kill.sh

2. Start the system:
   ./start.sh

3. Access web interface:
   http://localhost:8000

4. Run benchmark (optional):
   python benchmark.py

5. Stop the system:
   ./kill.sh

NOTES:
- Docker and Docker Compose must be installed
- Ports 5001-5003, 50051-50053, and 8000 must be available
- For Windows, use Git Bash or WSL to run .sh scripts
- Web interface auto-refreshes every 5 seconds
- Logs update every 2 seconds
- Pictures are randomly distributed across nodes on upload