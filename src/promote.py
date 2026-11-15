"""Model Registry: register a run's model and point an alias at it, or roll @champion back.

python src/promote.py [run_id] [--alias champion]   # default run id: models/run_id.txt
python src/promote.py rollback                      # @champion -> previous version
"""

import argparse
import sys
from pathlib import Path

import mlflow
from mlflow import MlflowClient

NAME = "banking77"
ROOT = Path(__file__).resolve().parents[1]


def promote(run_id: str, alias: str) -> None:
    client = MlflowClient()
    existing = client.search_model_versions(f"name='{NAME}' and run_id='{run_id}'")
    # re-running a deploy for the same run must not create a duplicate version
    version = existing[0].version if existing else mlflow.register_model(f"runs:/{run_id}/model", NAME).version
    for key, value in client.get_run(run_id).data.metrics.items():
        client.set_model_version_tag(NAME, version, key, f"{value:.4f}")
    client.set_registered_model_alias(NAME, alias, version)
    print(f"{NAME} v{version} (run {run_id}) -> @{alias}")


def rollback() -> None:
    client = MlflowClient()
    current = int(client.get_model_version_by_alias(NAME, "champion").version)
    older = [int(v.version) for v in client.search_model_versions(f"name='{NAME}'") if int(v.version) < current]
    if not older:
        sys.exit(f"v{current} is the oldest version, nothing to roll back to")
    client.set_registered_model_alias(NAME, "champion", max(older))
    print(f"{NAME} @champion: v{current} -> v{max(older)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", nargs="?")
    parser.add_argument("--alias", default="champion")
    args = parser.parse_args()
    if args.run_id == "rollback":
        rollback()
    else:
        promote(args.run_id or (ROOT / "models/run_id.txt").read_text().strip(), args.alias)
