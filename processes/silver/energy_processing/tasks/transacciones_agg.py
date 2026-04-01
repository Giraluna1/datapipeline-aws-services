#!/usr/bin/env python3
"""Silver Task: transacciones_agg

Lee bronze/transacciones y genera agregados por tipo_energia, ciudad y fecha_transaccion
en gold/transacciones_agg (Parquet particionado).
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

src = f"s3://{args['SRC_BUCKET']}/transacciones/"
dst = f"s3://{args['DST_BUCKET']}/transacciones_agg/"

df = spark.read.parquet(src)
df_agg = df.groupBy("tipo_energia","ciudad","fecha_transaccion").agg(
    {"cantidad_kwh":"sum","precio_kwh":"avg"}
).withColumnRenamed("sum(cantidad_kwh)","total_kwh") \
 .withColumnRenamed("avg(precio_kwh)","avg_precio_kwh") \
 .withColumn("processed_date", current_date())

df_final = df_agg.withColumn("year", year(col("processed_date"))) \
                 .withColumn("month", month(col("processed_date"))) \
                 .withColumn("day", dayofmonth(col("processed_date")))
df_final.write.mode("append").partitionBy("year","month","day").parquet(dst)

job.commit()
print("Silver task transacciones_agg completed.")
