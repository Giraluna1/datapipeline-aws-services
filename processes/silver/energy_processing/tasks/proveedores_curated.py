#!/usr/bin/env python3
"""Silver Task: proveedores_curated

Lee bronze/proveedores y publica gold/proveedores en Parquet particionado.
"""
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, current_date, year, month, dayofmonth, to_date

args = getResolvedOptions(sys.argv, [
    "JOB_NAME","SRC_BUCKET","DST_BUCKET","ENVIRONMENT"
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

src = f"s3://{args['SRC_BUCKET']}/proveedores/"
dst = f"s3://{args['DST_BUCKET']}/proveedores/"

df = spark.read.parquet(src)
df = df.withColumn("capacidad_mw", col("capacidad_mw").cast("double"))
if "fecha_contrato" in df.columns:
    df = df.withColumn("fecha_contrato", to_date(col("fecha_contrato")))
df = df.withColumn("processed_date", current_date())
df = df.withColumn("year", year(col("processed_date"))) \
       .withColumn("month", month(col("processed_date"))) \
       .withColumn("day", dayofmonth(col("processed_date")))
df.write.mode("append").partitionBy("year","month","day").parquet(dst)

job.commit()
print("Silver task proveedores_curated completed.")
