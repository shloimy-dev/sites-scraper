#!/usr/bin/env python3
"""Run all site scrapers in parallel batches."""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts" / "sites"
LOG_DIR = ROOT / "data"

PARALLEL = 3


def main():
    scrapers = sorted(SCRIPTS_DIR.glob("scrape_*.py"))
    print(f"Found {len(scrapers)} scrapers:")
    for s in scrapers:
        print(f"  {s.name}")

    running = {}
    queue = list(scrapers)
    done = []
    failed = []

    while queue or running:
        while queue and len(running) < PARALLEL:
            script = queue.pop(0)
            site = script.stem.replace("scrape_", "")
            log_path = LOG_DIR / f"run_{site}.log"
            print(f"\nStarting {site}...")
            log_f = open(log_path, "w")
            proc = subprocess.Popen(
                [sys.executable, "-u", str(script)],
                stdout=log_f, stderr=subprocess.STDOUT,
                cwd=str(ROOT),
            )
            running[site] = {"proc": proc, "log": log_f, "log_path": log_path}

        finished = []
        for site, info in running.items():
            ret = info["proc"].poll()
            if ret is not None:
                info["log"].close()
                if ret == 0:
                    done.append(site)
                    print(f"  DONE: {site} (exit 0)")
                else:
                    failed.append(site)
                    print(f"  FAIL: {site} (exit {ret})")
                finished.append(site)

        for s in finished:
            del running[s]

        if running:
            time.sleep(5)

    print(f"\n{'='*50}")
    print(f"RESULTS: {len(done)} done, {len(failed)} failed")
    if done:
        print(f"  Done: {', '.join(done)}")
    if failed:
        print(f"  Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
