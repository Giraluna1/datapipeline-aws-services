#!/usr/bin/env python3
import sys, json
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, ['JOB_NAME','SRC_BUCKET','DST_BUCKET','ENVIRONMENT','SECRET_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

s3_src = f"s3://{args['SRC_BUCKET']}/transacciones/"
s3_dst = f"s3://{args['DST_BUCKET']}/analytics/"

df = spark.read.parquet(s3_src)

# Example: top 10 providers by total_kwh
df_top = df.groupBy("tipo_energia").sum("total_kwh").withColumnRenamed("sum(total_kwh)","total_kwh")

(df_top.write.mode("overwrite").parquet(s3_dst + "tipo_energia/"))

job.commit()
print("Gold analytics job finished.")
