"""
Generate a clean PDF report (ASCII-only) with sections and screenshots.
Requires: fpdf2 (install locally, e.g. `.venv-local/bin/pip install fpdf2`).
"""

from pathlib import Path
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "REPORT.pdf"

# Caption, image path pairs
IMAGES = [
    ("Initial Election (logs)", "screenshots/logs_initial_short.png"),
    ("Forwarding (logs)", "screenshots/logs_forwarding_short.png"),
    ("Failover (logs)", "screenshots/logs_failover_short.png"),
    ("Restart (logs)", "screenshots/logs_restart_short.png"),
    ("State after set a 1", "screenshots/store_after_a.png"),
    ("State after set b 2", "screenshots/store_after_b.png"),
    ("State after set c 3", "screenshots/store_after_c.png"),
]


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Project 3 - 2PC & Raft (Group10)", ln=1, align="C")
        self.ln(2)

    def section(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, title, ln=1)
        self.ln(1)

    def bullet(self, text: str):
        self.set_font("Helvetica", size=11)
        safe = text.replace("–", "-").replace("—", "-")
        self.multi_cell(190, 6, f"- {safe}")

    def para(self, text: str):
        self.set_font("Helvetica", size=11)
        safe = text.replace("–", "-").replace("—", "-")
        self.multi_cell(190, 6, safe)
        self.ln(1)


def build_pdf():
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Team & Repo
    pdf.section("Team & Repo")
    pdf.bullet("Group: 10")
    pdf.bullet("Members: Muhan Zhang, Danhua Zhao")
    pdf.bullet("Base repo: https://github.com/J1anXu/Distributed-picture-sharing-system")
    pdf.bullet("Consensus additions: consensus_node/, docker-compose-consensus.yml")
    pdf.ln(2)

    # Overview
    pdf.section("Overview")
    pdf.para(
        "Added a 5-node consensus cluster with Two-Phase Commit (vote+decision) and Raft "
        "(leader election, heartbeats, log replication). Followers forward client commands "
        "to the leader; majority commit drives state to disk."
    )

    # Architecture
    pdf.section("Architecture")
    pdf.bullet("Heartbeat 1s; election timeout randomized 1.5–3s.")
    pdf.bullet("Full-log replication on AppendEntries; majority ACK -> commit.")
    pdf.bullet("State per node: /data/consensus_store.json (volume-backed).")
    pdf.bullet("Protos: consensus_node/two_phase.proto, consensus_node/raft.proto.")
    pdf.bullet("Docker: 5 homogeneous nodes; host ports 6001–6005 map to 6000.")
    pdf.ln(2)

    # How to Run
    pdf.section("How to Run")
    pdf.bullet("Start: docker compose -f docker-compose-consensus.yml up --build -d")
    pdf.bullet("2PC demo: grpcurl -plaintext -d '{\"key\":\"k1\",\"value\":\"v1\"}' localhost:6001 twopc.TwoPhaseService/StartTransaction")
    pdf.bullet("Raft demo (works on follower): grpcurl -plaintext -d '{\"command\":\"set a 1\",\"client_id\":\"cli\"}' localhost:6003 raft.RaftService/ClientCommand")
    pdf.bullet("Stop: docker compose -f docker-compose-consensus.yml down")
    pdf.bullet("Host helper: PYTHONPATH=. .venv-local/bin/python consensus_node/demo_raft.py \"set a 1\"")
    pdf.bullet("In container: PYTHONPATH=/app TARGET=consensus-nodeX:6000 python consensus_node/demo_raft.py \"set k v\"")
    pdf.ln(2)

    # Test Cases
    pdf.section("Validation (Q5)")
    pdf.bullet("Initial election: logs_initial_short.png (RequestVote + AppendEntries).")
    pdf.bullet("Heartbeat stability: steady AppendEntries, no elections.")
    pdf.bullet("Log replication: set a 1 -> store_after_a.png.")
    pdf.bullet("Client forwarding: follower forwards, leader commits -> logs_forwarding_short.png, store_after_b.png.")
    pdf.bullet("Leader failover/restart: logs_failover_short.png, logs_restart_short.png; set c 3 -> store_after_c.png.")
    pdf.ln(2)

    # Notes
    pdf.section("Notes")
    pdf.bullet("Compose omits version to silence warnings.")
    pdf.bullet("Use .venv-local/bin/python on host; set PYTHONPATH=/app inside containers.")
    pdf.bullet("Logs follow required formats for 2PC and Raft RPCs.")

    # Images
    for caption, img in IMAGES:
        path = ROOT / img
        if not path.exists():
            continue
        pdf.add_page()
        pdf.section(caption)
        pdf.image(str(path), x=10, y=None, w=190)

    pdf.output(str(OUTPUT))
    print(f"PDF written to {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
