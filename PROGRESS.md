# PROGRESS.md

Plan for `databricks-sagemaker-fraud-pipeline` (Project 2). Legend: `[x]` done, `[ ]` pending.
The notebooks are drafts and have not run yet.

Time budget: the Databricks trial (Project 1 workspace) expires about 2026-10-21 (8 days left on 2026-10-13). The last 3-4 days are reserved for prod and `destroy` in Project 1, so Phase 1 and Phase 2 must fit before about 2026-10-17. Phase 3 is the first thing to cut.

## Phase 0 - Setup
- [x] Repository created, cloned next to Project 1
- [x] Scaffold: `databricks.yml`, `resources/fraud_pipeline.yml`, notebooks 01-05, docs
- [ ] AWS Budgets alert (Project 1, before the first cluster runs)
- [ ] OAuth secret for `databricks-homol-pipeline` and GitHub `homol` Environment secrets in this repo
- [ ] Install the Databricks CLI; `databricks bundle validate -t homol` passes

## Phase 1 - Databricks pipeline (batch)
- [ ] 01 bronze: CSV -> `homol_catalog.bronze.creditcard_raw` (284,807 rows, 492 frauds)
- [ ] 02 silver: types, quality rules, deduplication -> `silver.creditcard_clean`
- [ ] 03 gold: rolling features and time split -> `gold.creditcard_features`
- [ ] 04 train: GBT with class weights, MLflow run with AUPRC / precision / recall
- [ ] 05 export: Parquet to `export/gold/creditcard/{train,test}/`
- [ ] Whole Workflow runs end to end with `bundle run` (NAT on, then off)
- [ ] Optional: register the model in Unity Catalog (needs `CREATE_MODEL` grant in Project 1)

## Phase 2 - SageMaker
- [ ] IAM role for SageMaker (read `export/gold/creditcard/`, training, endpoint) and a CI role trusting this repo (in Project 1 `infra/ci-oidc`)
- [ ] XGBoost training job with `scale_pos_weight`, same metrics as Phase 1
- [ ] Serverless Inference endpoint, test with a simulated transaction
- [ ] Delete the endpoint (`sagemaker-teardown`)

## Phase 3 - Streaming (optional, first thing to cut)
- [ ] Auto Loader + Structured Streaming into Delta, with a checkpoint

## CI/CD
- [ ] `databricks-pipeline-homol.yml`: validate on PR, deploy on push to `main`
- [ ] `databricks-pipeline-prod.yml`: `environment: prod` with a required reviewer (after prod exists in Project 1)
- [ ] `sagemaker-train-deploy.yml` (manual) and `sagemaker-teardown.yml` (always available)
- [ ] Ruleset on `main` requiring the validation check
