# CLAUDE.md

Context for future sessions. Track status in `PROGRESS.md`; run instructions are in `README.md`.

## What this repo is

**Project 2** of two linked projects. Project 1 is `../databricks-aws-terraform-lab` (platform: Databricks workspace on AWS, Unity Catalog, cluster policies, Terraform + GitHub Actions). This repo holds the data and model code that runs on that platform: Spark -> Delta Lake -> MLflow -> Parquet export to S3 -> SageMaker.

Original briefs (Portuguese) are in the parent directory: `../projeto-1-databricks-terraform-cicd.md`, `../projeto-2-databricks-sagemaker.md`. No need to re-read them.

Purpose: job-interview/portfolio practice (Spark and Delta Lake pipelines, MLflow, feature engineering, CI/CD for ML, Databricks -> SageMaker integration).

## Contract with Project 1 (do not change it from here)

- Workspace `databricks-homol`: https://dbc-405a719f-a0d8.cloud.databricks.com. Catalog `homol_catalog`, schemas `bronze` (`creditcard_raw`), `silver` (`creditcard_clean`), `gold` (`creditcard_features`).
- Jobs run as the service principal `databricks-homol-pipeline` (least privilege: `USE_SCHEMA`, `SELECT`, `MODIFY`, `CREATE_TABLE`; read/write on the data external location). Needs `CREATE_MODEL` on a schema before registering models in Unity Catalog: that grant belongs to Project 1 (`infra/modules/unity-catalog/grants.tf`).
- Cluster policy `databricks-homol-job-policy` (id `0001AA326BA37BEC`): fixed Spark LTS, node type `m5d.large`, `SINGLE_USER`, at most 2 workers. Job clusters only.
- S3 data bucket `databricks-homol-data-<databricks-account-id>`: input `raw/creditcard/creditcard.csv`, output `export/gold/creditcard/{train,test}/`. SageMaker reads the export prefix, never Delta (it would bypass Unity Catalog).
- **The NAT Gateway is OFF by default** (cost ~US$0.05/h). Clusters cannot start without it. Turn it on in Project 1 only while the job runs: Actions > terraform-apply-homol > Run workflow with `enable_nat` ticked; turn it off afterwards (run again unticked). Verify with `aws ec2 describe-nat-gateways` / `describe-addresses`.
- The Databricks trial expires about **2026-10-21**. The last 3-4 days are reserved for prod and `destroy` in Project 1.
- AWS auth from GitHub Actions needs a role trusting THIS repo. The Project 1 roles (`github-actions-terraform-*`) trust only the Project 1 repo, so SageMaker workflows need a new role added to `infra/ci-oidc` in Project 1 (applied by hand with an IAM admin profile). The `sub` claim has the form `repo:gil-son@<ownerId>/<repo>@<repoId>:environment:<env>`; owner id is 72712095, repo id comes from `https://api.github.com/repos/gil-son/databricks-sagemaker-fraud-pipeline`.

## Conventions

- Dataset: Credit Card Fraud Detection (ULB/Worldline), 284,807 rows, 492 frauds (0.17%). Metrics: AUPRC, precision, recall. Never accuracy.
- Notebooks are Databricks `.py` source files (`# Databricks notebook source`, `# COMMAND ----------`), parameterized with widgets, deployed by the bundle in `databricks.yml`. No hardcoded catalog or bucket names.
- Silver drops exact duplicate rows (the public dataset has some), so silver counts differ from bronze's 284,807 / 492.
- Gold features only look at PAST transactions (window upper bound -1). Train/test split is by time (`is_test`, last 20%), computed once in gold and reused by training and export.
- SageMaker: Serverless Inference, small instances, and always delete the endpoint after testing. Endpoints bill while they exist.
- User writes in Portuguese; code, docs, commits and these files are in English. Conventional commits (`feat(pipeline): ...`), one branch per feature, branch from updated `origin/main`, one PR per branch. Never commit secrets, tfvars or `.databricks/`.
- Document each finished piece in `README.md` and tick it in `PROGRESS.md`.
- The user runs deploys and anything that costs money; give them the commands, and tell them what to check and where (Databricks UI, S3, AWS console).

## PAUSED (2026-10-20): the platform was destroyed

The Databricks trial was about to expire, so the user paused the project and tore down the whole homol environment in Project 1 (see its `CLAUDE.md`, "Paused" section). **Everything in "Contract with Project 1" above describes the platform as it WAS; it does not exist now.** No pipeline run ever happened: the notebooks are still unexecuted drafts and no code was changed by the teardown. Nothing in this repo costs money.

Gone and must be recreated (the values below will be different next time):
- Workspace URL (`databricks.yml` line ~24 has the old `dbc-405a719f-a0d8` host), cluster policy id (`databricks.yml` line ~30 has `0001AA326BA37BEC`), service principal `databricks-homol-pipeline` and its application id (`BUNDLE_VAR_pipeline_sp_application_id`), data bucket name (it contains the Databricks account id, which may change), catalog/schemas, `creditcard.csv` in S3.

## Next session: where to start

1. Rebuild the platform first, in Project 1 (see its "Resume" steps): new Databricks account/trial, `terraform apply -var enable_nat=true`, upload `creditcard.csv` to `raw/creditcard/`.
2. Update `databricks.yml` with the new `host` and `job_policy_id` (both are hardcoded) and the new bucket / SP application id (`BUNDLE_VAR_*`).
3. Pipeline SP OAuth secret (account console > Service principals > `databricks-homol-pipeline` > Secrets), stored as `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET` / `DATABRICKS_HOST` secrets of the `homol` GitHub Environment of this repo.
4. Install the Databricks CLI, `databricks bundle validate -t homol`, fix what it reports (policy defaults, `run_as`, variables).
5. Turn the NAT on, `bundle deploy` + `bundle run fraud_pipeline`, fix notebook errors, turn the NAT off.
6. Then workflow `databricks-pipeline-homol.yml` (validate on PR, deploy on push to `main`), then SageMaker (Phase 2).

The 2026-10-21 trial deadline in this file and in `PROGRESS.md` no longer applies; plan against whatever account or trial is used next.
