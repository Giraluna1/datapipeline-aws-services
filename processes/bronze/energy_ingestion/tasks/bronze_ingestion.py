#!/usr/bin/env python3
import sys, json
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import current_date, year, month, dayofmonth

args = getResolvedOptions(sys.argv, ['JOB_NAME','SRC_BUCKET','DST_BUCKET','ENVIRONMENT','SECRET_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def get_secret(secret_name):
    sm = boto3.client('secretsmanager')
    try:
        r = sm.get_secret_value(SecretId=secret_name)
        s = r.get('SecretString')
        return json.loads(s) if s else {}
    except Exception as e:
        print("Error reading secret:", e)
        return {}

secrets = {}
if args.get('SECRET_NAME'):
    secrets = get_secret(args['SECRET_NAME'])

src_path = f"s3://{args['SRC_BUCKET']}/"
dst_path = f"s3://{args['DST_BUCKET']}/"

# Read CSVs (assume header)
df = spark.read.option("header", "true").csv(src_path)

# Basic transformations
df_clean = df.withColumnRenamed("nombre_proveedor", "provider_name") \
             .withColumn("processed_date", current_date())

df_final = df_clean.withColumn("year", year(df_clean.processed_date)) \
                   .withColumn("month", month(df_clean.processed_date)) \
                   .withColumn("day", dayofmonth(df_clean.processed_date))

(df_final.write.mode("append").partitionBy("year","month","day").parquet(dst_path))

job.commit()
print("Bronze ingestion completed.")
