"""
Automated capture of real command + output screenshots for the report.

Steps performed:
1. docker compose down (to start clean), then up -d
2. Capture initial election logs
3. set a 1 (leader will handle); capture logs + state
4. set b 2 via follower port 6004; capture logs + state
5. Stop consensus-node5 (likely leader) to force failover; capture logs
6. Start consensus-node5; set c 3 via port 6005; capture logs + state

Outputs PNGs into screenshots/: logs_*_short.png, store_after_*.png
Requirements: pillow (`pip install pillow`), .venv-local with deps, docker running.
"""

import subprocess
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
SCREEN_DIR = ROOT / "screenshots"
SCREEN_DIR.mkdir(exist_ok=True)

FONT = ImageFont.load_default()
LINE_H = FONT.getbbox("Ag")[3] + 4
WIDTH = 1400


def run_cmd(cmd: str) -> str:
    res = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    return (res.stdout + res.stderr).strip()


def render_png(stem: str, lines):
    height = LINE_H * (len(lines) + 2)
    img = Image.new("RGB", (WIDTH, height), "white")
    d = ImageDraw.Draw(img)
    y = 4
    for line in lines:
        d.text((6, y), line, font=FONT, fill="black")
        y += LINE_H
    out = SCREEN_DIR / f"{stem}.png"
    img.save(out)
    print(f"wrote {out}")


def capture_logs(stem: str, cmd: str, tail: int = 120):
    out = run_cmd(cmd)
    lines = [f"$ {cmd}"] + out.splitlines()[:tail]
    render_png(stem, lines)


def capture_state(stem: str, desc: str):
    state = run_cmd("docker exec distributed-picture-sharing-system-consensus-node2-1 cat /data/consensus_store.json")
    render_png(stem, [desc, state])


def main():
    # Clean start
    run_cmd("docker compose -f docker-compose-consensus.yml down")
    run_cmd("docker compose -f docker-compose-consensus.yml up --build -d")
    time.sleep(5)

    # Initial election logs
    capture_logs("logs_initial_short", "docker compose -f docker-compose-consensus.yml logs --tail 120")

    # set a 1
    run_cmd('PYTHONPATH=. .venv-local/bin/python consensus_node/demo_raft.py "set a 1"')
    capture_logs("logs_after_a", "docker compose -f docker-compose-consensus.yml logs --tail 60")
    capture_state("store_after_a", "$ state after set a 1")

    # set b 2 via follower port
    run_cmd('TARGET=localhost:6004 PYTHONPATH=. .venv-local/bin/python consensus_node/demo_raft.py "set b 2"')
    capture_logs("logs_forwarding_short", "docker compose -f docker-compose-consensus.yml logs --tail 60")
    capture_state("store_after_b", "$ state after set b 2")

    # Failover: stop node5
    run_cmd("docker compose -f docker-compose-consensus.yml stop consensus-node5")
    time.sleep(5)
    capture_logs("logs_failover_short", "docker compose -f docker-compose-consensus.yml logs --tail 120")

    # Restart node5 and set c 3
    run_cmd("docker compose -f docker-compose-consensus.yml start consensus-node5")
    time.sleep(3)
    run_cmd('TARGET=localhost:6005 PYTHONPATH=. .venv-local/bin/python consensus_node/demo_raft.py "set c 3"')
    capture_logs("logs_restart_short", "docker compose -f docker-compose-consensus.yml logs --tail 80")
    capture_state("store_after_c", "$ state after set c 3")

    print("Capture complete.")


if __name__ == "__main__":
    main()
