
## Quick Start:

1. Quick Start:
curl -fsSL https://raw.githubusercontent.com/J1anXu/Distributed-book-sharing-system/main/one_click.sh | bash

2. Access web interface: http://localhost:8000

3. Stop the system: ./kill.sh

## Deploy by yourself

DEPENDENCY INSTALLATION
   conda create -n imgshare python=3.11 -y
   conda activate imgshare
   pip install -r requirements.txt

1. chmod +x start.sh kill.sh
   
2. ./start.sh
   
3. Access web interface: http://localhost:8000

5. Stop the system: ./kill.sh

NOTES:
- Docker and Docker Compose must be installed
- Ports 5001-5003, 50051-50053, and 8000 must be available
- For Windows, use Git Bash or WSL to run .sh scripts
- Web interface auto-refreshes every 5 seconds
- Logs update every 2 seconds
- Pictures are randomly distributed across nodes on upload