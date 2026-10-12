# Databricks notebook source
# Export gold to Parquet in S3 for SageMaker. SageMaker reads this prefix, never the Delta table:
# reading Delta directly would bypass Unity Catalog permissions.

# COMMAND ----------

from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "homol_catalog")
dbutils.widgets.text("data_bucket", "")
catalog = dbutils.widgets.get("catalog")
data_bucket = dbutils.widgets.get("data_bucket")
base = f"s3://{data_bucket}/export/gold/creditcard"

gold = spark.table(f"{catalog}.gold.creditcard_features")
# Label first (SageMaker XGBoost convention); Time and the split flag are not model inputs
feature_cols = [c for c in gold.columns if c not in ("Time", "Class", "is_test")]
cols = ["Class", *feature_cols]

# COMMAND ----------

for name, flag in (("train", False), ("test", True)):
    part = gold.filter(F.col("is_test") == F.lit(flag)).select(*cols)
    part.write.mode("overwrite").parquet(f"{base}/{name}/")
    print(f"{base}/{name}/: {part.count()} rows")
