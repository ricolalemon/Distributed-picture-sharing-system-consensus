"""Small helper to exercise the 2PC coordinator call for demos/tests."""

import os
import sys

import grpc

from consensus_node import two_phase_pb2 as tp
from consensus_node import two_phase_pb2_grpc as tpg


def main():
    target = os.environ.get("TARGET", "localhost:6001")
    key = sys.argv[1] if len(sys.argv) > 1 else "demo-key"
    value = sys.argv[2] if len(sys.argv) > 2 else "demo-value"

    channel = grpc.insecure_channel(target)
    stub = tpg.TwoPhaseServiceStub(channel)
    resp = stub.StartTransaction(tp.TxnRequest(key=key, value=value), timeout=5)
    print(f"Decision={resp.decision}, success={resp.success}, txn_id={resp.txn_id}, coordinator={resp.coordinator_id}")


if __name__ == "__main__":
    main()
