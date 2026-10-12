# Databricks notebook source
# Silver: explicit types, validation, deduplication.

# COMMAND ----------

from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "homol_catalog")
catalog = dbutils.widgets.get("catalog")
source = f"{catalog}.bronze.creditcard_raw"
target = f"{catalog}.silver.creditcard_clean"

# COMMAND ----------

v_cols = [f"V{i}" for i in range(1, 29)]
expected = ["Time", *v_cols, "Amount", "Class"]

bronze = spark.table(source)
missing = [c for c in expected if c not in bronze.columns]
assert not missing, f"bronze is missing columns: {missing}"

typed = bronze.select(
    F.col("Time").cast("double").alias("Time"),
    *[F.col(c).cast("double").alias(c) for c in v_cols],
    F.col("Amount").cast("double").alias("Amount"),
    F.col("Class").cast("int").alias("Class"),
)

# COMMAND ----------

# Data quality rules: fail the job instead of silently training on bad data
bad = typed.filter(
    F.col("Class").isNull() | ~F.col("Class").isin(0, 1) | F.col("Amount").isNull() | (F.col("Amount") < 0) | F.col("Time").isNull()
).count()
assert bad == 0, f"{bad} rows violate the quality rules (null/invalid Class, Amount or Time)"

# COMMAND ----------

# The public dataset contains exact duplicate rows; drop them
silver = typed.dropDuplicates()
silver.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(target)

# COMMAND ----------

before = typed.count()
after = spark.table(target).count()
frauds = spark.table(target).filter("Class = 1").count()
print(f"{target}: {after} rows ({before - after} duplicates removed), {frauds} frauds")
