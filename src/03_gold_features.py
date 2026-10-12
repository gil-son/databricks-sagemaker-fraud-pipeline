# Databricks notebook source
# Gold: model features. The dataset has no card id, so the rolling features are computed over
# the whole transaction stream ordered by Time (seconds since the first transaction).
# Windows only look at PAST transactions (upper bound -1) to avoid leaking the current row.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

dbutils.widgets.text("catalog", "homol_catalog")
catalog = dbutils.widgets.get("catalog")
source = f"{catalog}.silver.creditcard_clean"
target = f"{catalog}.gold.creditcard_features"

# COMMAND ----------

df = spark.table(source)

# No partitionBy: one global ordering, so Spark moves the data to a single partition.
# Fine for 284k rows; it would need a partition key (card id) at real scale.
w_1h = Window.orderBy("Time").rangeBetween(-3600, -1)
w_5m = Window.orderBy("Time").rangeBetween(-300, -1)

features = (
    df
    .withColumn("amount_log", F.log1p("Amount"))
    .withColumn("hour_of_day", (F.floor(F.col("Time") / 3600) % 24).cast("int"))
    .withColumn("tx_count_1h", F.count(F.lit(1)).over(w_1h))
    .withColumn("tx_count_5m", F.count(F.lit(1)).over(w_5m))
    .withColumn("amount_mean_1h", F.coalesce(F.avg("Amount").over(w_1h), F.col("Amount")))
    .withColumn("amount_std_1h", F.coalesce(F.stddev("Amount").over(w_1h), F.lit(0.0)))
    .withColumn(
        "amount_zscore_1h",
        F.when(F.col("amount_std_1h") > 0, (F.col("Amount") - F.col("amount_mean_1h")) / F.col("amount_std_1h")).otherwise(F.lit(0.0)),
    )
    .withColumn("amount_ratio_to_mean_1h", F.col("Amount") / (F.col("amount_mean_1h") + F.lit(1e-6)))
)

# Time-based split (last 20% of the timeline is the test set), stored once so that training
# and the SageMaker export use exactly the same split.
split_time = features.approxQuantile("Time", [0.8], 0.001)[0]
features = features.withColumn("is_test", F.col("Time") > F.lit(split_time))

features.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(target)

# COMMAND ----------

out = spark.table(target)
summary = out.groupBy("is_test").agg(F.count("*").alias("rows"), F.sum("Class").alias("frauds")).orderBy("is_test")
display(summary)
print(f"{target}: split at Time > {split_time:.0f}")
