# Projekto reikalavimai

Versija: 1.0
Data: 2026-11-16
Autoriai: Saule Gylyte (@lumiflarez), Matas Jasiūnas (@yasns) 

## 1. Problemos aprašymas

Sistema priskiria banko klientų užklausas vienam iš 77 ketinimų (intents). Duomenys: [PolyAI/banking77](https://huggingface.co/datasets/PolyAI/banking77), oficialus train/test skaidymas. Modelis: TF-IDF + LogisticRegression. Iš dalies remtasi straipsniu: [Efficient Intent Detection with Dual Sentence Encoders](https://arxiv.org/pdf/2003.04807).

## 2. Stakeholder'iai

| Kas | Ko reikia |
|---|---|
| Klientų aptarnavimo komanda | Teisingas nukreipimas, žemas klaidingų nukreipimų skaičius |
| ML / MLOps inžinieriai | Atkartojami run'ai, saugus deploy, greitas rollback |

## 3. Funkciniai reikalavimai (FR)

| ID | Reikalavimas | Prioritetas |
|-------|-------------------------------------|-------------|
| FR-01 | POST /predict priima {"text": "..."} ir grąžina intent, confidence, model_version | Must |
| FR-02 | GET /health grąžina modelio versiją; 503, jei modelis nepakrautas | Must |
| FR-03 | Mokymas per DVC pipeline, kiekvienas run'as registruojamas MLflow | Must |
| FR-04 | Servisas krauna modelį iš registro per alias @champion; rollback perkelia alias į ankstesnę versiją | Must |
| FR-05 | GET /metrics Prometheus formatu | Must |

## 4. Nefunkciniai reikalavimai (NFR)

| ID | Kategorija | Reikalavimas | Metrika/KPI |
|--------|---------------|---------------------------|--------------------|
| NFR-01 | Kokybė | Modelio tikslumas | accuracy ≥ 0.85 |
| NFR-02 | Kokybės vartas | Modelis, nepasiekęs NFR-01, nepatenka į registrą ir klasterį | 100 % raudonų run'ų sustabdo deploy |
| NFR-03 | Našumas | /predict vėlinimas | p95 ≤ 200 ms (200 užklausų, 10 lygiagrečių) |
| NFR-04 | Našumas | Pralaidumas | ≥ 50 req/s (200 užklausų, 10 lygiagrečių) |
| NFR-05 | Patikimumas | Klaidos apkrovos teste | 0 klaidų iš 200 užklausų |
| NFR-06 | Operacijos | Rollback laikas | ≤ 2 min iki /health su senesne versija |
| NFR-07 | Mastelis | HPA scale-out po apkrova | 2 → 4 replikos per ≤ 3 min |
| NFR-08 | Atkartojamumas | Istorinis run'as atkuriamas su reproduce.py <run_id> | Δaccuracy ≤ 0.005 |
| NFR-09 | Atsekamumas | Kiekvienas run'as turi git commit, duomenų md5, params| 100 % run'ų |
| NFR-10 | Saugumas | Vaizdas be CRITICAL pažeidžiamumų | 0 CRITICAL (Trivy) |
| NFR-11 | Saugumas | Servisas veikia ne root | UID ≠ 0 |
| NFR-12 | Saugumas | Secret'ai ne Git'e | 0 secret'ų repo; Secret kuriamas per kubectl |
| NFR-13 | Stebėsena | Vėlinimas, klaidos, pralaidumas matomi Grafana dashboard'e; ≥ 2 alert'ai | alert firing ≤ 2 min nuo sąlygos |
| NFR-14 | Dreifas | Įvesties / prognozių dreifas aptinkamas Evidently ataskaita | simuliuotas dreifas aptiktas |

## 5. Atsekamumo matrica

| NFR | Testas / matavimas | Įrodymas | Išmatuota |
|---|---|---|---|
| NFR-01 | src/evaluate.py → metrics.json | metrics.json, MLflow run | 0.8928 (commit 973b953) |
| NFR-02 | src/gate.py CI; red run su C: 0.0001 | docs/gate-red.log, Actions screenshot | TBD |
| NFR-03 | scripts/loadtest.py … 200 10 | docs/load-test.json (p95_ms) | 51.8 |
| NFR-04 | scripts/loadtest.py … 200 10 | docs/load-test.json (throughput_rps) | 232.9 |
| NFR-05 | scripts/loadtest.py baigiasi be klaidos | docs/load-test.json | 0 klaidų |
| NFR-06 | time (promote.py rollback + rollout restart + rollout status) | docs/rollback.md (/health prieš / po) | 27s |
| NFR-07 | loadtest.py + kubectl get hpa -w | docs/hpa.md + screenshot | TBD |
| NFR-08 | python reproduce.py <run_id> | MLflow run su tag reproduces=<run_id> | TBD |
| NFR-09 | MLflow run Tags skiltis | MLflow UI | 100 % |
| NFR-10 | Trivy CI job, --severity CRITICAL --exit-code 1 | docs/trivy.json | TBD |
| NFR-11 | kubectl exec deploy/inference -- id | k8s/api.yaml, docker/Dockerfile | uid=1000 |
| NFR-12 | git log -p \| grep -i secret; README §8 | kubectl get secret -n mlops-team | 0 |
| NFR-13 | PrometheusRule; alert'o suveikimas simuliuojant | docs/grafana-dashboard.json, k8s/alerts.yaml, screenshot | TBD |
| NFR-14 | Evidently po off-topic užklausų | docs/drift-report.html | TBD |

## 6. Keitimo istorija

| Versija | Data | Autorius | Pakeitimai |
|---|---|---|---|
| 0.0 | 2026-10-30 | Matas | Pradinė struktūra, problema |
| 1.0 | 2026-11-16 | Saule | Stakeholder'iai, FR-01–05, NFR-01–14, atsekamumo matrica |