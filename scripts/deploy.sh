#!/usr/bin/env bash
# Manual deploy for when the self-hosted runner is off: gate -> @champion -> rollout.
set -euo pipefail
K="kubectl --context kind-mlops-team -n mlops-team"

python src/gate.py
python src/promote.py
$K apply -f k8s/api.yaml
$K rollout restart deployment/inference # re-resolve @champion even if the image is unchanged
$K rollout status deployment/inference --timeout=300s
