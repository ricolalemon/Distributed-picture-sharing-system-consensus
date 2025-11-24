import json
import os
import random
import threading
import time
import uuid
from concurrent import futures
from typing import Dict, List, Tuple

import grpc

import consensus_node.two_phase_pb2 as tp
import consensus_node.two_phase_pb2_grpc as tpg
import consensus_node.raft_pb2 as rp
import consensus_node.raft_pb2_grpc as rpg

# Timing constants for Raft
HEARTBEAT_SECS = 1.0
ELECTION_MIN = 1.5
ELECTION_MAX = 3.0


def parse_peers(raw: str) -> Dict[str, str]:
    """Parse comma-separated host:port pairs into id->addr map."""
    peers = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" in entry:
            node_id, addr = entry.split("=", 1)
        else:
            addr = entry
            node_id = addr.split(":")[0]
        peers[node_id] = addr
    return peers


class ConsensusNode(tpg.TwoPhaseServiceServicer, rpg.RaftServiceServicer):
    def __init__(self) -> None:
        self.node_id = os.getenv("NODE_ID", "node-unknown")
        self.bind_addr = os.getenv("BIND_ADDR", "0.0.0.0:6000")
        self.peer_map = parse_peers(os.getenv("PEERS", ""))
        self.peer_map.setdefault(self.node_id, os.getenv("SELF_ADDR", self.bind_addr.replace("0.0.0.0", self.node_id)))

        self.kv_file = os.getenv("KV_STORE_FILE", "/data/consensus_store.json")
        self.kv_store = self._load_store()
        self.pending_txns: Dict[str, Tuple[str, str]] = {}
        self.kv_lock = threading.Lock()

        # Raft state
        self.state = "follower"
        self.current_term = 0
        self.voted_for = None
        self.leader_id = None
        self.log: List[rp.LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0
        self.match_index: Dict[str, int] = {}
        self.election_deadline = time.time() + self._rand_election_timeout()
        self.stop_evt = threading.Event()
        self.channel_cache: Dict[str, grpc.Channel] = {}

        # Background loops
        threading.Thread(target=self._election_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    # ======================
    # Two-phase commit logic
    # ======================
    def StartTransaction(self, request: tp.TxnRequest, context) -> tp.TxnResult:
        txn_id = str(uuid.uuid4())
        participants = list(self.peer_map.items())
        votes: List[bool] = []

        # Phase 1: voting
        for peer_id, addr in participants:
            resp = self._send_vote(peer_id, addr, txn_id, request.key, request.value)
            votes.append(resp is not None and resp.vote_commit)

        commit = all(votes) and len(votes) == len(participants)

        # Phase 2: decision
        for peer_id, addr in participants:
            self._send_decision(peer_id, addr, txn_id, request.key, request.value, commit)

        decision = "commit" if commit else "abort"
        return tp.TxnResult(success=commit, decision=decision, coordinator_id=self.node_id, txn_id=txn_id)

    def Vote(self, request: tp.VoteRequest, context) -> tp.VoteResponse:
        self._print_server("vote", "Vote", request.coordinator_id)
        with self.kv_lock:
            # Simple rule: always vote commit unless the key starts with "deny"
            allow = not request.key.lower().startswith("deny")
            if allow:
                self.pending_txns[request.txn_id] = (request.key, request.value)
            return tp.VoteResponse(vote_commit=allow, node_id=self.node_id, reason="" if allow else "Key rejected by policy")

    def Decision(self, request: tp.DecisionRequest, context) -> tp.DecisionAck:
        self._print_server("decision", "Decision", request.coordinator_id)
        with self.kv_lock:
            if request.txn_id in self.pending_txns:
                del self.pending_txns[request.txn_id]
            if request.global_commit:
                self.kv_store[request.key] = request.value
                self._save_store()
        return tp.DecisionAck(node_id=self.node_id, applied=True)

    def _send_vote(self, peer_id: str, addr: str, txn_id: str, key: str, value: str) -> tp.VoteResponse:
        self._print_client("vote", "Vote", peer_id)
        try:
            stub = tpg.TwoPhaseServiceStub(self._channel(addr))
            return stub.Vote(tp.VoteRequest(txn_id=txn_id, key=key, value=value, coordinator_id=self.node_id), timeout=2)
        except Exception as exc:  # pragma: no cover - network failure simulation
            print(f"[{self.node_id}] vote RPC to {peer_id} failed: {exc}")
            return None

    def _send_decision(self, peer_id: str, addr: str, txn_id: str, key: str, value: str, commit: bool) -> None:
        self._print_client("decision", "Decision", peer_id)
        try:
            stub = tpg.TwoPhaseServiceStub(self._channel(addr))
            stub.Decision(
                tp.DecisionRequest(
                    txn_id=txn_id,
                    global_commit=commit,
                    key=key,
                    value=value,
                    coordinator_id=self.node_id,
                ),
                timeout=2,
            )
        except Exception as exc:  # pragma: no cover
            print(f"[{self.node_id}] decision RPC to {peer_id} failed: {exc}")

    # ===============
    # Raft RPCs
    # ===============
    def RequestVote(self, request: rp.RequestVoteRequest, context) -> rp.RequestVoteResponse:
        self._print_server_generic("RequestVote", request.candidate_id)
        with self.kv_lock:
            if request.term > self.current_term:
                self._become_follower(request.term)
            grant = False
            up_to_date = (len(self.log) == 0) or (request.last_log_term > self.log[-1].term) or (
                request.last_log_term == self.log[-1].term and request.last_log_index >= self.log[-1].index
            )
            if request.term == self.current_term and up_to_date and (self.voted_for in (None, request.candidate_id)):
                grant = True
                self.voted_for = request.candidate_id
                self.election_deadline = time.time() + self._rand_election_timeout()
        return rp.RequestVoteResponse(vote_granted=grant, term=self.current_term, voter_id=self.node_id)

    def AppendEntries(self, request: rp.AppendEntriesRequest, context) -> rp.AppendEntriesResponse:
        self._print_server_generic("AppendEntries", request.leader_id)
        with self.kv_lock:
            if request.term >= self.current_term:
                if request.term > self.current_term or self.state != "follower":
                    self._become_follower(request.term)
                self.leader_id = request.leader_id
                self.election_deadline = time.time() + self._rand_election_timeout()
                # Copy entire log as required
                self.log = [
                    rp.LogEntry(command=e.command, term=e.term, index=e.index, client_id=e.client_id) for e in request.entries
                ]
                self.commit_index = min(request.commit_index, len(self.log))
                self._apply_committed()
                return rp.AppendEntriesResponse(success=True, term=self.current_term, node_id=self.node_id, match_index=len(self.log))
            return rp.AppendEntriesResponse(success=False, term=self.current_term, node_id=self.node_id, match_index=len(self.log))

    def ClientCommand(self, request: rp.ClientRequest, context) -> rp.ClientResponse:
        caller = getattr(context, "peer", lambda: "")()
        self._print_server_generic("ClientCommand", request.client_id or caller)
        with self.kv_lock:
            if self.state != "leader":
                if self.leader_id and self.leader_id in self.peer_map and self.leader_id != self.node_id:
                    leader_addr = self.peer_map[self.leader_id]
                    self._print_client_generic("ClientCommand", self.leader_id)
                    try:
                        stub = rpg.RaftServiceStub(self._channel(leader_addr))
                        return stub.ClientCommand(request, timeout=2)
                    except Exception as exc:  # pragma: no cover
                        return rp.ClientResponse(accepted=False, leader_id=self.leader_id, message=str(exc), index=0)
                return rp.ClientResponse(accepted=False, leader_id=self.leader_id or "", message="No leader yet", index=0)

            entry = rp.LogEntry(
                command=request.command,
                term=self.current_term,
                index=len(self.log) + 1,
                client_id=request.client_id or "anonymous",
            )
            self.log.append(entry)
            return rp.ClientResponse(
                accepted=True,
                leader_id=self.node_id,
                message="Appended to leader log; will commit after majority ACK",
                index=entry.index,
            )

    # ======================
    # Raft background loops
    # ======================
    def _election_loop(self) -> None:
        while not self.stop_evt.is_set():
            time.sleep(0.1)
            if self.state == "leader":
                continue
            if time.time() > self.election_deadline:
                self._start_election()

    def _start_election(self) -> None:
        with self.kv_lock:
            self.state = "candidate"
            self.current_term += 1
            self.voted_for = self.node_id
            self.election_deadline = time.time() + self._rand_election_timeout()
            term_snapshot = self.current_term
            votes = 1
            last_index = self.log[-1].index if self.log else 0
            last_term = self.log[-1].term if self.log else 0

        for peer_id, addr in self.peer_map.items():
            if peer_id == self.node_id:
                continue
            self._print_client_generic("RequestVote", peer_id)
            try:
                stub = rpg.RaftServiceStub(self._channel(addr))
                resp = stub.RequestVote(
                    rp.RequestVoteRequest(
                        candidate_id=self.node_id,
                        term=term_snapshot,
                        last_log_index=last_index,
                        last_log_term=last_term,
                    ),
                    timeout=1,
                )
                with self.kv_lock:
                    if resp.vote_granted:
                        votes += 1
                    if resp.term > self.current_term:
                        self._become_follower(resp.term)
                        return
            except Exception:  # pragma: no cover
                continue

        if votes > len(self.peer_map) // 2:
            with self.kv_lock:
                self.state = "leader"
                self.leader_id = self.node_id
                self.match_index = {pid: 0 for pid in self.peer_map}
                self.election_deadline = time.time() + self._rand_election_timeout()
            self._broadcast_appendentries(force=True)
        else:
            with self.kv_lock:
                self.state = "follower"

    def _heartbeat_loop(self) -> None:
        while not self.stop_evt.is_set():
            time.sleep(HEARTBEAT_SECS)
            if self.state == "leader":
                self._broadcast_appendentries()

    def _broadcast_appendentries(self, force: bool = False) -> None:
        entries = list(self.log)
        commit_val = self.commit_index
        successes = 1  # leader counts as success
        for peer_id, addr in self.peer_map.items():
            if peer_id == self.node_id:
                continue
            self._print_client_generic("AppendEntries", peer_id)
            try:
                stub = rpg.RaftServiceStub(self._channel(addr))
                resp = stub.AppendEntries(
                    rp.AppendEntriesRequest(
                        leader_id=self.node_id,
                        term=self.current_term,
                        entries=entries,
                        commit_index=commit_val,
                    ),
                    timeout=1,
                )
                if resp.success:
                    successes += 1
                    self.match_index[peer_id] = resp.match_index
            except Exception:  # pragma: no cover
                continue

        if successes > len(self.peer_map) // 2:
            with self.kv_lock:
                self.commit_index = len(self.log)
                self._apply_committed()

    # ================
    # State transitions
    # ================
    def _become_follower(self, term: int) -> None:
        self.state = "follower"
        self.current_term = term
        self.voted_for = None
        self.leader_id = None
        self.election_deadline = time.time() + self._rand_election_timeout()

    def _apply_committed(self) -> None:
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            self._apply_command(entry.command)
        self._save_store()

    def _apply_command(self, command: str) -> None:
        parts = command.strip().split()
        if len(parts) >= 2 and parts[0].lower() in ("set", "put"):
            key = parts[1]
            value = " ".join(parts[2:]) if len(parts) > 2 else ""
            self.kv_store[key] = value
        elif parts and parts[0].lower() == "del" and len(parts) >= 2:
            self.kv_store.pop(parts[1], None)

    def _rand_election_timeout(self) -> float:
        return random.uniform(ELECTION_MIN, ELECTION_MAX)

    # =================
    # Utility functions
    # =================
    def _channel(self, addr: str) -> grpc.Channel:
        if addr not in self.channel_cache:
            self.channel_cache[addr] = grpc.insecure_channel(addr)
        return self.channel_cache[addr]

    def _print_client(self, phase: str, rpc_name: str, peer_id: str) -> None:
        print(f"Phase {phase} of Node {self.node_id} sends RPC {rpc_name} to Phase {phase} of Node {peer_id}")

    def _print_server(self, phase: str, rpc_name: str, caller: str) -> None:
        print(f"Phase {phase} of Node {self.node_id} runs RPC {rpc_name} called by Phase {phase} of Node {caller}")

    def _print_client_generic(self, rpc_name: str, peer_id: str) -> None:
        print(f"Node {self.node_id} sends RPC {rpc_name} to Node {peer_id}")

    def _print_server_generic(self, rpc_name: str, caller: str) -> None:
        print(f"Node {self.node_id} runs RPC {rpc_name} called by Node {caller}")

    def _save_store(self) -> None:
        os.makedirs(os.path.dirname(self.kv_file), exist_ok=True)
        with open(self.kv_file, "w") as f:
            json.dump(self.kv_store, f)

    def _load_store(self) -> Dict[str, str]:
        try:
            with open(self.kv_file) as f:
                return json.load(f)
        except FileNotFoundError:
            return {}


def serve() -> None:
    node = ConsensusNode()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=32))
    tpg.add_TwoPhaseServiceServicer_to_server(node, server)
    rpg.add_RaftServiceServicer_to_server(node, server)
    server.add_insecure_port(node.bind_addr)
    print(f"[{node.node_id}] consensus node listening on {node.bind_addr} with peers: {list(node.peer_map.keys())}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
