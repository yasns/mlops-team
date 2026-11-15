# Banko klientų užklausų klasifikavimas

## Reikalavimai
Docker, kind, kubectl, Python 3.14, git.

## Paleidimas nuo nulio

### 1. Repo ir Python aplinka
```bash
git clone https://github.com/yasns/mlops-team && cd mlops-team
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Duomenys
Jei DVC remote (`~/dvcstore`) yra šiame kompiuteryje:
```bash
dvc pull
```
Jei ne (pvz., kitas kompiuteris) – atsisiųsti tą pačią rinkinio reviziją iš Hugging Face:
```bash
python src/fetch_data.py
```

### 3. Klasteris ir MLflow
```bash
kind create cluster --config k8s/kind-config.yaml
kubectl --context kind-mlops-team apply -f k8s/namespace.yaml -f k8s/mlflow.yaml
kubectl --context kind-mlops-team rollout status deployment/mlflow -n mlops-team
```
Pirmą kartą užtrunka kelias minutes, kol atsisiunčiamas MLflow vaizdas.

### 4. Prieiga prie MLflow
Atskirame terminale (palikti veikti):
```bash
kubectl --context kind-mlops-team port-forward -n mlops-team svc/mlflow 5005:5000
```
MLflow UI: http://127.0.0.1:5005

### 5. Pipeline'as
`MLFLOW_TRACKING_URI` nustatomas `.envrc` faile. 

a) Jei naudojate direnv: 
```bash
direnv allow
```
b) Be direnv: 
```bash 
source .envrc
```
Tada:
```bash
dvc repro
```
Jei niekas nepasikeitė, `dvc repro` praleidžia visus etapus. Naujam run'ui su tais pačiais parametrais – `dvc repro -f`.

### 6. Istorinio run'o atkūrimas
Run ID nukopijuoti iš MLflow UI (run'o puslapio antraštė). Darbinis medis turi būti švarus (`git status`).
```bash
time python reproduce.py <run_id>
```
Atkuria to run'o kodą (git), duomenis (DVC) ir parametrus, perleidžia pipeline'ą ir palygina metrikas. UI atsiranda naujas run'as su žyma `reproduces=<run_id>`.

### 7. Modelio registras
```bash
python src/promote.py           # registruoja run'ą iš models/run_id.txt ir suteikia @champion alias'ą
python src/promote.py <run_id>  # konkrečiam run'ui
```
Modelis `banking77` matomas MLflow UI skiltyje Models.

### 8. Prognozių API
Secret'as sukuriamas vieną kartą per CLI (Git'e jo nėra):
```bash
kubectl --context kind-mlops-team create secret generic mlflow-credentials -n mlops-team \
  --from-literal=MLFLOW_TRACKING_URI=http://mlflow.mlops-team.svc.cluster.local:5000
```
API modelį `models:/banking77@champion` nuskaito iš registro Pod'o paleidimo metu.

```bash
kubectl --context kind-mlops-team apply -f k8s/api.yaml
kubectl --context kind-mlops-team rollout status deployment/inference -n mlops-team
kubectl --context kind-mlops-team port-forward -n mlops-team svc/inference 8005:80   # atskirame terminale
```
```bash
curl -s localhost:8005/health
curl -s -X POST localhost:8005/predict -H 'Content-Type: application/json' -d '{"text": "my card was declined"}'
```

### 9. Rollback
```bash
python src/promote.py rollback   # @champion -> ankstesnė versija
kubectl --context kind-mlops-team rollout restart deployment/inference -n mlops-team
kubectl --context kind-mlops-team rollout status deployment/inference -n mlops-team
curl -s localhost:8005/health    # "version" turi sumažėti
```

### 10. CI/CD
`.github/workflows/ci-cd.yaml`: testai -> `dvc repro` -> kokybės vartas (`src/gate.py`, slenkstis `params.yaml` `gate`) -> vaizdo build/push į GHCR -> `k8s/api.yaml` atnaujinimas -> `@champion` ir rollout. Vartui nepraėjus, deploy neįvyksta.

`train` ir `deploy` žingsniai vykdomi self-hosted runner'yje kompiuteryje, kuriame veikia klasteris (reikia `python3.14`, `kubectl`). Runner'is registruojamas repo nustatymuose: Settings -> Actions -> Runners.

Jei runner'is išjungtas, tą patį galima atlikti ranka (vaizdas nekeičiamas):
```bash
dvc repro && scripts/deploy.sh
```

### 11. Testai
```bash
pip install ruff pytest httpx
ruff check src tests scripts && pytest -q
```

## Rezultatai
| Kas | Kur |
|-----|-----|
| MLflow UI (run'ai, parametrai, metrikos, modeliai) | http://127.0.0.1:5005, eksperimentas `banking77`, be prisijungimo |
| Modelio registras | MLflow UI, skiltis Models: `banking77@champion` |
| Pipeline'o metrikos | `metrics.json`, `dvc metrics show` |
| Vėlinimas, pralaidumas | `docs/load-test.json` (`python scripts/loadtest.py http://127.0.0.1:8005 200 10`) |
| CI/CD paleidimai | [GitHub Actions](https://github.com/yasns/mlops-team/actions) |
| Docker vaizdas | `ghcr.io/yasns/mlops-team` |
| Reikalavimai (FR, NFR, KPI) | `docs/requirements.md` |

## Išjungimas
Dėmesio: ištrina ir visus MLflow run'us (PVC).
```bash
kind delete cluster --name mlops-team
```
