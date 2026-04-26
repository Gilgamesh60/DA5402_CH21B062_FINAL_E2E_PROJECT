"""Local rollback CLI.

Mirrors the GitHub Actions rollback workflow so developers can run it
from their laptop without pushing to GH. Restarts the model-server
automatically via `docker compose restart` when run with `--restart`.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from mlflow.tracking import MlflowClient

from ssa_model.registry import rollback


def _list_versions(client: MlflowClient, name: str) -> None:
    mvs = client.search_model_versions(f"name='{name}'")
    print(f"Current versions of {name}:")
    for v in sorted(mvs, key=lambda x: int(x.version), reverse=True):
        print(f"  v{v.version:<4} {v.current_stage}")


def main() -> None:
    p = argparse.ArgumentParser(description="Roll the registered model back.")
    p.add_argument("target_version", help="Version to promote to Production")
    p.add_argument("--name", default="stock-sentiment")
    p.add_argument("--tracking-uri", default=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--restart", action="store_true", help="docker compose restart model-server after rollback")
    args = p.parse_args()

    client = MlflowClient(tracking_uri=args.tracking_uri)
    _list_versions(client, args.name)

    if args.dry_run:
        print(f"\n[dry-run] would promote v{args.target_version} to Production")
        return

    import mlflow
    mlflow.set_tracking_uri(args.tracking_uri)
    prev, new = rollback(args.name, args.target_version)
    print(
        f"\nrolled back: previous=v{prev.version or '-'} ({prev.stage or '-'}) "
        f"-> new=v{new.version} ({new.stage})"
    )

    if args.restart:
        try:
            subprocess.run(
                ["docker", "compose", "restart", "model-server"], check=True
            )
            print("model-server restarted")
        except subprocess.CalledProcessError as e:
            print(f"failed to restart model-server: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
