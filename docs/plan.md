# Team project plan — what is left for `team-final`

Source: `komandine.md`. Submission **2026-12-09** (tag `team-final` + report), defence **2026-12-16**.
Status as of 2026-11-15.

## Status quo

Working end to end on main:

- DVC pipeline `prepare → train → evaluate` logging to the team MLflow (3.18.0) in the kind cluster `mlops-team`, namespace `mlops-team`.
- Model registry: `banking77@champion`, set by `src/promote.py` (also `--alias` and `rollback`).
- Inference service in the cluster: Deployment `inference` (2 replicas, non-root), Service port 80 → 8000, `POST /predict` with `{"text": "..."}` → intent, confidence, model version; `GET /health`.
- CI/CD (`.github/workflows/ci-cd.yaml`): lint + tests → `dvc repro` on the self-hosted runner → quality gate (accuracy ≥ 0.85) → multi-arch image to `ghcr.io/yasns/mlops-team:sha-<commit>` → manifest bump → `@champion` → rollout → smoke test.
- Secret not in Git: `mlflow-credentials`, created with `kubectl`.
- Python 3.14 everywhere the team's code runs.

## What is left

| # | Work | Depends on | Target |
|---|---|---|---|
| 1 | Requirements v1.0 and traceability matrix | — | Nov 18 (consultation) |
| 2 | CI/CD evidence: red run, rollback, load test | — | Nov 18 |
| 3 | `/metrics` and request logging in the service | — | Nov 20 |
| 4 | Prometheus + Grafana, dashboard, 2 alerts | 3 | Nov 29 |
| 5 | Evidently drift report | 3 | Nov 29 |
| 6 | Tests in CI: data contract, E2E | — | Nov 29 |
| 7 | HPA + load test | 3 | Dec 5 |
| 8 | Security: Trivy in CI, one policy | — | Dec 5 |
| 9 | GPU training of a challenger model (extended part) | — | Dec 5 |
| 10 | Runbook, architecture, model card, EU AI Act note | 4, 5, 7, 8 | Dec 7 |
| 11 | Report ≤ 4 pages, final README, matrix filled, tag | all | Dec 9 |
| 12 | Demo rehearsal, cross-reading each other's files | 11 | Dec 14 |

## 1 — Requirements

`docs/requirements.md` is still v0.0 with an empty FR table and one NFR.

- At least 3 FR and 5 NFR with measurable KPI. Most of FR-01–07 and the NFRs in both individual `requirements.md` files transfer; re-measure the numbers.
- NFRs to cover: p95 latency, throughput, error rate, rollback time, scale-out under load, 0 CRITICAL CVEs, reproducibility.
- Add the traceability matrix `NFR → test → evidence`, with a "measured" column; rows get filled as the items below finish.
- Bump the version and fill the change history on every edit.

## 2 — CI/CD evidence

The pipeline works; the defence needs proof saved in `docs/`.

- Red run: push a bad parameter (e.g. `C: 0.0001`), save the failed gate log, revert.
- Rollback: `python src/promote.py rollback` + rollout restart; save `/health` before and after and the time it took.
- Load test: `python scripts/loadtest.py http://127.0.0.1:8005 200 10` → `docs/load-test.json` (p95, throughput).

## 3 — Service contract leftovers

Monitoring and the drift report both wait on these.

- `GET /metrics` in Prometheus format: request count by status, latency histogram.
- Log every request's text and predicted intent (stdout as JSON or a file on a volume).

## 4 — Monitoring

- Install `kube-prometheus-stack` with Helm; add a ServiceMonitor selecting `app: inference`.
- Grafana dashboard saved as JSON in the repo: latency p50/p95, error rate, throughput.
- Two alerts as a PrometheusRule: high p95 latency, and high error rate or no ready pods.
- Memory: the course estimates about 6 GB for the cluster with this stack.

## 5 — Drift report

- Evidently report: training texts vs. logged requests (text length, predicted class distribution).
- Simulate drift by sending off-topic requests; save the report under `docs/`.

## 6 — Tests in CI

Gate and API unit tests exist. Still missing:

- Data contract: columns, no nulls, 77 labels, expected row counts.
- E2E: after deploy, call `/predict` through the cluster and check the response shape (the smoke test only calls `/health`).

## 7 — Scale

- metrics-server + HPA on CPU for `inference` (resource requests are already set).
- Load test while watching replicas scale out; save the numbers and a screenshot.

## 8 — Security

- Trivy as a CI job with a 0-CRITICAL gate, report saved under `docs/`. Local scan on 2026-11-15: 0 CRITICAL, 52 HIGH, 5 of them fixable (`msgpack`, `urllib3`, `setuptools`).
- One policy. Pod Security `restricted` on the namespace needs two changes first: the MLflow server image runs as root, and `inference` needs `allowPrivilegeEscalation: false`, dropped capabilities and a seccomp profile. A NetworkPolicy is the alternative.

## 9 — GPU training (extended part)

The TF-IDF + LogisticRegression model gains nothing from a GPU, so this adds a second model.

- `src/train_gpu.py`: fine-tune a small transformer (e.g. `distilbert-base-uncased`) on the same `data/processed` CSVs. `torch` and `transformers` have Python 3.14 builds.
- Pick the device automatically: `cuda`, else `mps` (Apple Silicon), else `cpu`. The run happens outside the cluster and logs to the team MLflow through the port-forward.
- On HPC the laptop MLflow is unreachable: log locally there and copy the run over.
- Register the result with `python src/promote.py <run_id> --alias challenger`; log device and training time.
- Hyperparameters under a new `train_gpu` key in `params.yaml`; separate `docker/requirements-gpu.txt` so torch stays out of the existing images.
- Evidence: MLflow comparison of `champion` vs `challenger` (accuracy, training time, GPU vs CPU time for one epoch).
- Serving keeps the TF-IDF `champion`.

## 10 — Docs and governance

- `docs/runbook.md`: what to do on drift, accuracy drop, pod crash, each of the two alerts.
- `docs/architecture.md`: one Mermaid diagram that matches what the demo shows.
- `docs/model_card.md`: at least 8 sections, plus a short risk / EU AI Act classification.

## 11 — Submission

- README: start from zero, ports, who demos what.
- Report ≤ 4 pages: methodology, architecture diagram, results, conclusions.
- Traceability matrix complete, every NFR pointing at a test and a piece of evidence.
- CI green on main, then `git tag team-final && git push --tags`.

## 12 — Defence prep

- Rehearse the 15-minute flow on one laptop from a fresh cluster: problem and NFR → architecture → data / MLflow / `/predict` / dashboard → one governance artefact.
- Each person must explain their own part **and** live-edit one file the other person wrote. For example, whoever built the quality gate walks through an alert rule, and the other way round.
- The demo laptop needs the self-hosted runner running. Keep a pre-built cluster as backup in case the fresh start fails.

## Open questions and housekeeping

- Saulė's machine: Python 3.14, `python src/fetch_data.py` for the data (the DVC remote `~/dvcstore` exists only on Matas's laptop), and a cluster created from the current manifests (namespace `mlops-team`, MLflow 3.18.0).

## Not planned

- Ray / Prefect / HITL — DVC + CI already meets the orchestration minimum.
- Rest of the extended part (self-healing agent, edge/FL, GCP cost analysis) — only if everything above is done before Dec 5. GCP cost analysis is the cheapest one to add.
