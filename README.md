
Autors:
Jian Xu
Yinhao Wu

## Quick Start:

1. Quick Start:
curl -fsSL https://raw.githubusercontent.com/J1anXu/Distributed-picture-sharing-system/main/one_click.sh | bash

2. Access web interface: http://localhost:8000

3. Stop all running containers: docker stop $(docker ps -q)


## Deploy by yourself

DEPENDENCY INSTALLATION
   conda create -n imgshare python=3.11 -y
   conda activate imgshare
   pip install -r requirements.txt

1. chmod +x start.sh kill.sh
   
2. ./start.sh
   
3. Access web interface: http://localhost:8000

4. Stop the system: ./stop.sh

NOTES:
- Docker and Docker Compose must be installed
- Ports 5001-5003, 50051-50053, and 8000 must be available
- For Windows, use Git Bash or WSL to run .sh scripts
- Web interface auto-refreshes every 5 seconds
- Logs update every 2 seconds
- Pictures are randomly distributed across nodes on upload

---

## Project 3 (Group10) — 2PC + Raft Additions

We added a dedicated consensus cluster (5 gRPC nodes) to satisfy Project 3 requirements. New artifacts live under `consensus_node/` (our submission repo: https://github.com/ricolalemon/Distributed-picture-sharing-system-consensus).
- 2PC proto/service: `consensus_node/two_phase.proto`
- Raft proto/service: `consensus_node/raft.proto`
- Combined node implementation: `consensus_node/node.py`
- Compose to launch 5 nodes: `docker-compose-consensus.yml` (ports 6001–6005 mapped to container port 6000)
 - Our submission repo: https://github.com/ricolalemon/Distributed-picture-sharing-system-consensus
 - Contributors: Muhan Zhang (2PC/Raft core, Docker), Danhua Zhao (testing, logs/screenshots, report)

### Run the consensus cluster
```bash
docker compose -f docker-compose-consensus.yml up --build -d
# Stop
docker compose -f docker-compose-consensus.yml down
```

### 2PC quick check (Phase vote + decision messaging)
```bash
# Start a transaction on node1 (coordinator). All client/server prints follow the required formats.
grpcurl -plaintext -d '{"key":"demo","value":"v1"}' localhost:6001 twopc.TwoPhaseService/StartTransaction
```

### Raft quick check (election + log replication)
```bash
# Send a client command to any node; follower will forward to leader.
grpcurl -plaintext -d '{"command":"set a 1","client_id":"cli"}' localhost:6003 raft.RaftService/ClientCommand
# Optionally inspect the committed KV file inside a node: /data/consensus_store.json

# Convenience helper:
python consensus_node/demo_raft.py           # uses localhost:6003 by default
```

Behavior details:
- Heartbeat timeout is 1s; election timeout is randomized in [1.5s, 3s].
- Followers copy the full log on each AppendEntries and advance commit index `c` after majority ACKs.
- Any node can receive client commands and will forward to the current leader. 2PC phases use gRPC for both intra-node (self) and inter-node calls.

### Handy demo scripts
- 2PC: `python consensus_node/demo_2pc.py <key> <value>` (defaults target localhost:6001)
- Raft: `python consensus_node/demo_raft.py "set k v"` (defaults target localhost:6003)

---

## Submission metadata (Group10)
- Group: 10
- Members: Muhan Zhang, Danhua Zhao
- Repo link: https://github.com/J1anXu/Distributed-picture-sharing-system (project base) with consensus additions in this folder.
