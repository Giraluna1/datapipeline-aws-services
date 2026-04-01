#!/usr/bin/env python3
"""Silver Task: clientes_curated

Lee bronze/clientes y publica gold/clientes en Parquet particionado.
"""
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, current_date, year, month, dayofmonth

args = getResolvedOptions(sys.argv, [
    "JOB_NAME","SRC_BUCKET","DST_BUCKET","ENVIRONMENT"
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

src = f"s3://{args['SRC_BUCKET']}/clientes/"
dst = f"s3://{args['DST_BUCKET']}/clientes/"

df = spark.read.parquet(src)
if "cliente_proveedor" in df.columns:
    df = df.dropDuplicates(["cliente_proveedor"])
df = df.withColumn("processed_date", current_date())
df = df.withColumn("year", year(col("processed_date"))) \
       .withColumn("month", month(col("processed_date"))) \
       .withColumn("day", dayofmonth(col("processed_date")))
df.write.mode("append").partitionBy("year","month","day").parquet(dst)

job.commit()
print("Silver task clientes_curated completed.")
