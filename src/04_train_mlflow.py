# Databricks notebook source
# Train a Spark ML gradient-boosted trees model and log it to MLflow.
# Metrics follow the class imbalance (0.17% fraud): AUPRC, precision and recall, never accuracy.

# COMMAND ----------

import mlflow
import mlflow.spark
from pyspark.ml import Pipeline
from pyspark.ml.classification import GBTClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.feature import VectorAssembler
from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "homol_catalog")
dbutils.widgets.text("experiment_path", "/Shared/homol/fraud-detection")
catalog = dbutils.widgets.get("catalog")
experiment_path = dbutils.widgets.get("experiment_path")

gold = spark.table(f"{catalog}.gold.creditcard_features")
feature_cols = [c for c in gold.columns if c not in ("Time", "Class", "is_test")]

train = gold.filter(~F.col("is_test"))
test = gold.filter(F.col("is_test"))

# COMMAND ----------

# Class weights instead of resampling: a fraud row weighs (negatives / positives)
n_pos = train.filter("Class = 1").count()
n_neg = train.filter("Class = 0").count()
pos_weight = n_neg / n_pos
train = train.withColumn("weight", F.when(F.col("Class") == 1, F.lit(pos_weight)).otherwise(F.lit(1.0)))

params = {"maxIter": 50, "maxDepth": 5, "stepSize": 0.1, "seed": 42}
assembler = VectorAssembler(inputCols=feature_cols, outputCol="features", handleInvalid="skip")
gbt = GBTClassifier(labelCol="Class", featuresCol="features", weightCol="weight", **params)
pipeline = Pipeline(stages=[assembler, gbt])

# COMMAND ----------

mlflow.set_experiment(experiment_path)

with mlflow.start_run(run_name="gbt-weighted") as run:
    mlflow.log_params({**params, "pos_weight": round(pos_weight, 2), "n_features": len(feature_cols)})

    model = pipeline.fit(train)
    pred = model.transform(test)

    auprc = BinaryClassificationEvaluator(labelCol="Class", rawPredictionCol="rawPrediction", metricName="areaUnderPR").evaluate(pred)
    auroc = BinaryClassificationEvaluator(labelCol="Class", rawPredictionCol="rawPrediction", metricName="areaUnderROC").evaluate(pred)

    counts = pred.groupBy("Class", "prediction").count().collect()
    cell = {(int(r["Class"]), int(r["prediction"])): r["count"] for r in counts}
    tp, fp, fn = cell.get((1, 1), 0), cell.get((0, 1), 0), cell.get((1, 0), 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    mlflow.log_metrics({"test_auprc": auprc, "test_auroc": auroc, "test_precision": precision, "test_recall": recall})
    mlflow.spark.log_model(model, "model")

    print(f"run {run.info.run_id}: AUPRC={auprc:.4f} precision={precision:.4f} recall={recall:.4f} (tp={tp} fp={fp} fn={fn})")
