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
kubectl --context kind-mlops-team rollout status deployment/mlflow -n mlops
```
Pirmą kartą užtrunka kelias minutes, kol atsisiunčiamas MLflow vaizdas.

### 4. Prieiga prie MLflow
Atskirame terminale (palikti veikti):
```bash
kubectl --context kind-mlops-team port-forward -n mlops svc/mlflow 5001:5000
```
MLflow UI: http://127.0.0.1:5001

### 5. Pipeline'as
```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5001
dvc repro
```
Jei niekas nepasikeitė, `dvc repro` praleidžia visus etapus. Naujam run'ui su tais pačiais parametrais – `dvc repro -f`.

### 6. Istorinio run'o atkūrimas
Run ID nukopijuoti iš MLflow UI (run'o puslapio antraštė). Darbinis medis turi būti švarus (`git status`).
```bash
time python reproduce.py <run_id>
```
Atkuria to run'o kodą (git), duomenis (DVC) ir parametrus, perleidžia pipeline'ą ir palygina metrikas. UI atsiranda naujas run'as su žyma `reproduces=<run_id>`.

## Rezultatai
| Kas | Kur |
|-----|-----|
| MLflow UI (run'ai, parametrai, metrikos, modeliai) | http://127.0.0.1:5001, eksperimentas `banking77`, be prisijungimo |
| Pipeline'o metrikos | `metrics.json`, `dvc metrics show` |
| Reikalavimai (FR, NFR, KPI) | `docs/requirements.md` |

## Išjungimas
Dėmesio: ištrina ir visus MLflow run'us (PVC).
```bash
kind delete cluster --name mlops-team
```
