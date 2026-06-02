#!/usr/bin/env python3
"""
Possum Patrol Inbox Triage
Usage:
  python main.py triage   — process inbox.json through Claude, save to DB
  python main.py serve    — launch the web dashboard at http://localhost:8000
  python main.py digest   — print the morning digest to the terminal
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import argparse


def main():
    parser = argparse.ArgumentParser(
        description="🦝 Possum Patrol Inbox Triage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["triage", "serve", "digest"],
        nargs="?",
        default="triage",
        help="triage | serve | digest",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Less verbose output")
    args = parser.parse_args()

    if args.command == "triage":
        from triage import run_triage
        run_triage(verbose=not args.quiet)

    elif args.command == "serve":
        import uvicorn
        from dashboard import app
        print("🦝 Possum Patrol Dashboard → http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

    elif args.command == "digest":
        from database import init_db
        from digest import generate_digest
        init_db()
        print(generate_digest())


if __name__ == "__main__":
    main()
