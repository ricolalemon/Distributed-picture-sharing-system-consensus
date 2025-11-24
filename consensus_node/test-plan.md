# Raft Test Plan (Group10)

Five manual tests to document with screenshots in the report.

1) **Initial leader election**
- Command: `docker compose -f docker-compose-consensus.yml up --build`
- Expected: nodes print randomized election timeout expirations; one node receives majority `RequestVote` grants and becomes leader; others print `AppendEntries` receipts from that leader.

2) **Heartbeat stability**
- Command: after cluster is steady, keep services running.
- Expected: followers print `AppendEntries` heartbeats every second and never transition to candidate while heartbeats arrive.

3) **Log replication + commit**
- Command: `grpcurl -plaintext -d '{"command":"set x 1","client_id":"c1"}' localhost:6002 raft.RaftService/ClientCommand`
- Expected: follower forwards to leader (if the target was a follower), leader appends entry, majority ACKs seen, commit index advances and `consensus_store.json` contains `"x": "1"` on all nodes.

4) **Client forwarding correctness**
- Command: send multiple commands to a known follower (e.g., node3) while leader is node1.
- Expected: node3 prints `ClientCommand` forwarding to node1; node1 accepts and replicates; node3 state machine reflects the committed values.

5) **Leader failure and re-election**
- Command: `docker compose -f docker-compose-consensus.yml stop consensus-node1` (current leader), then wait.
- Expected: remaining followers time out (1.5–3s), start election, elect a new leader, and heartbeats resume. Restart node1 and observe it copying the full log via `AppendEntries`.
