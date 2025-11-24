# Project 3 Report - Group10 (Muhan Zhang, Danhua Zhao)

## Team and Repo
- Group: 10
- Members: Muhan Zhang, Danhua Zhao
- Base repo: https://github.com/J1anXu/Distributed-picture-sharing-system
- Additions: `consensus_node/` code, new protos, helper scripts, `docker-compose-consensus.yml`

## Overview
We extended the picture-sharing system with a 5-node consensus cluster implementing:
- Two Phase Commit (2PC) vote + decision phases over gRPC
- Raft leader election and log replication (heartbeat 1s, election timeout 1.5–3s)
- Client forwarding from followers to leader, majority commit, and consistent state on disk
- Required logging formats for all RPCs

## Architecture
- Each consensus node runs both 2PC and Raft services (see `consensus_node/node.py`).
- State is persisted per node in `/data/consensus_store.json` (volume backed).
- Full-log replication on every AppendEntries simplifies recovery after crashes.
- Protos: `consensus_node/two_phase.proto`, `consensus_node/raft.proto`.
- Docker: 5 homogeneous containers; host ports 6001–6005 map to container port 6000.

## How to Run
```bash
docker compose -f docker-compose-consensus.yml up --build -d
# 2PC demo
grpcurl -plaintext -d '{"key":"k1","value":"v1"}' localhost:6001 twopc.TwoPhaseService/StartTransaction
# Raft demo (works on follower, will forward)
grpcurl -plaintext -d '{"command":"set a 1","client_id":"cli"}' localhost:6003 raft.RaftService/ClientCommand
# Shut down
docker compose -f docker-compose-consensus.yml down
```
Host Python (with deps): `PYTHONPATH=. .venv-local/bin/python consensus_node/demo_raft.py "set a 1"`  
Inside a container: `docker exec <container> /bin/sh -c "cd /app && PYTHONPATH=/app TARGET=consensus-nodeX:6000 python consensus_node/demo_raft.py 'set k v'"`.

## Implementation Highlights
- 2PC: coordinator gathers votes, then issues global commit/abort; pending txns tracked per node.
- Raft: randomized election timeout to avoid split vote; leader sends heartbeats; follower forwarding; majority commit.
- Logging: follows required strings for both 2PC phases and Raft RPCs.
- Test helpers: `demo_2pc.py`, `demo_raft.py`.

## Validation (Q5 Test Cases)
Screenshots are in `screenshots/` (use *_short.png for logs, store_after_*.png for state):
1) Initial leader election: `logs_initial_short.png` (RequestVote + AppendEntries).
2) Heartbeat stability: same log shows steady AppendEntries with no new elections.
3) Log replication and commit: command `set a 1`; see `store_after_a.png` and AppendEntries in `logs_initial_short.png`.
4) Client forwarding: follower receives ClientCommand, forwards to leader; see `logs_forwarding_short.png`; state in `store_after_b.png`.
5) Leader failure and re-election: stop old leader, new leader elected; see `logs_failover_short.png`; restart old leader (`logs_restart_short.png`); post-failover command `set c 3` confirmed in `store_after_c.png`.

Commands used in validation:
- `docker compose -f docker-compose-consensus.yml up --build -d`
- `PYTHONPATH=. .venv-local/bin/python consensus_node/demo_2pc.py`
- `PYTHONPATH=. .venv-local/bin/python consensus_node/demo_raft.py "set a 1"`
- `TARGET=localhost:6004 PYTHONPATH=. .venv-local/bin/python consensus_node/demo_raft.py "set b 2"`
- `docker compose -f docker-compose-consensus.yml stop consensus-node3` (failover) then `start consensus-node3`
- `TARGET=localhost:6005 PYTHONPATH=. .venv-local/bin/python consensus_node/demo_raft.py "set c 3"`
- `docker exec distributed-picture-sharing-system-consensus-node2-1 cat /data/consensus_store.json`
- `docker compose -f docker-compose-consensus.yml down`

## Notes
- Compose omits `version` to silence warnings.
- Use `.venv-local/bin/python` on host to avoid missing grpc; inside containers set `PYTHONPATH=/app`.
- State file per node: `/data/consensus_store.json`.
