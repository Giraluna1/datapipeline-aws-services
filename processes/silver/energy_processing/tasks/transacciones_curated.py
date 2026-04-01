#!/usr/bin/env python3
"""Silver Task: transacciones_curated

Lee bronze/transacciones y publica gold/transacciones_curated en Parquet particionado
con el esquema de negocio curado (equivalente al sample).
"""
import sys, json
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, current_date, year, month, dayofmonth, to_date

args = getResolvedOptions(sys.argv, [
    "JOB_NAME","SRC_BUCKET","DST_BUCKET","ENVIRONMENT","SECRET_NAME"
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

src = f"s3://{args['SRC_BUCKET']}/transacciones/"
dst = f"s3://{args['DST_BUCKET']}/transacciones_curated/"

df = spark.read.parquet(src)
df_cur = df.select(
    col("id_transaccion").cast("string"),
    to_date(col("fecha_transaccion")).alias("fecha_transaccion"),
    col("tipo_transaccion").cast("string"),
    col("cliente_proveedor").cast("string"),
    col("cantidad_kwh").cast("double"),
    col("precio_kwh").cast("double"),
    col("tipo_energia").cast("string"),
    col("hora_transaccion").cast("string"),
    col("ciudad").cast("string"),
)
df_cur = df_cur.withColumn("processed_date", current_date())
df_cur = df_cur.withColumn("year", year(col("processed_date"))) \
               .withColumn("month", month(col("processed_date"))) \
               .withColumn("day", dayofmonth(col("processed_date")))
df_cur.write.mode("append").partitionBy("year","month","day").parquet(dst)

job.commit()
print("Silver task transacciones_curated completed.")
