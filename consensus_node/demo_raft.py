"""Send a client command to any node; follower will forward to leader if needed."""

import os
import sys

import grpc

from consensus_node import raft_pb2 as rp
from consensus_node import raft_pb2_grpc as rpg


def main():
    target = os.environ.get("TARGET", "localhost:6003")
    command = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "set demo 1"
    client_id = os.environ.get("CLIENT_ID", "demo-client")
    channel = grpc.insecure_channel(target)
    stub = rpg.RaftServiceStub(channel)
    resp = stub.ClientCommand(rp.ClientRequest(command=command, client_id=client_id), timeout=5)
    print(f"accepted={resp.accepted}, leader={resp.leader_id}, msg={resp.message}, index={resp.index}")


if __name__ == "__main__":
    main()
