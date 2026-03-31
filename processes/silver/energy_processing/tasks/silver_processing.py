#!/usr/bin/env python3
import sys, time, json, os
import boto3, awswrangler as wr
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, current_date, year, month, dayofmonth

args = getResolvedOptions(sys.argv, [
    "JOB_NAME","SRC_BUCKET","DST_BUCKET","ENVIRONMENT","SECRET_NAME",
    "ATHENA_OUTPUT","REDSHIFT_SECRET_ARN","REDSHIFT_IAM_ROLE_ARN",
    "REDSHIFT_DATABASE","REDSHIFT_DB_USER","REDSHIFT_CLUSTER_ID"
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

def get_secret(secret_name):
    sm = boto3.client("secretsmanager")
    try:
        r = sm.get_secret_value(SecretId=secret_name)
        s = r.get("SecretString")
        return json.loads(s) if s else {}
    except Exception as e:
        print("Error reading secret:", e)
        return {}

secrets = get_secret(args.get("SECRET_NAME","")) if args.get("SECRET_NAME") else {}

s3_silver = f"s3://{args['SRC_BUCKET']}/transacciones/"
s3_gold   = f"s3://{args['DST_BUCKET']}/transacciones/"

df = spark.read.parquet(s3_silver)

df_agg = df.groupBy("tipo_energia","ciudad","fecha_transaccion").agg(
    {"cantidad_kwh":"sum","precio_kwh":"avg"}
).withColumnRenamed("sum(cantidad_kwh)","total_kwh") \
 .withColumnRenamed("avg(precio_kwh)","avg_precio_kwh") \
 .withColumn("processed_date", current_date())

df_final = df_agg.withColumn("year", year(col("processed_date"))) \
                 .withColumn("month", month(col("processed_date"))) \
                 .withColumn("day", dayofmonth(col("processed_date")))

(df_final.write.mode("append").partitionBy("year","month","day").parquet(s3_gold))

# Athena validation
try:
    session = boto3.Session()
    sql = "SELECT COUNT(*) AS total FROM transacciones WHERE year = year(current_date) LIMIT 1"
    df_check = wr.athena.read_sql_query(sql=sql, database=os.environ.get("GLUE_DATABASE","energy_db"),
                                        s3_output=args.get("ATHENA_OUTPUT"), boto3_session=session)
    print("Athena check:", df_check.head())
except Exception as e:
    print("Athena validation failed/skipped:", e)

# Redshift load using Data API + COPY (requires IAM role attached to cluster)
iam_role = args.get("REDSHIFT_IAM_ROLE_ARN")
if iam_role:
    redshift = boto3.client("redshift-data")
    table = "analytics.transacciones_agg"
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table} (
      tipo_energia VARCHAR(64),
      ciudad VARCHAR(128),
      fecha_transaccion DATE,
      total_kwh DOUBLE PRECISION,
      avg_precio_kwh DOUBLE PRECISION,
      processed_date DATE
    );
    """
    try:
        exec_create = {"Sql": create_sql, "Database": args.get("REDSHIFT_DATABASE"), "DbUser": args.get("REDSHIFT_DB_USER")}
        if args.get("REDSHIFT_CLUSTER_ID"): exec_create["ClusterIdentifier"] = args.get("REDSHIFT_CLUSTER_ID")
        if args.get("REDSHIFT_SECRET_ARN"): exec_create["SecretArn"] = args.get("REDSHIFT_SECRET_ARN")
        resp = redshift.execute_statement(**exec_create)
        stmt_id = resp["Id"]
        while True:
            desc = redshift.describe_statement(Id=stmt_id)
            if desc["Status"] in ("FINISHED","FAILED","ABORTED"): break
            time.sleep(1)
        copy_sql = f"COPY {table} FROM '{s3_gold}' IAM_ROLE '{iam_role}' FORMAT AS PARQUET;"
        exec_copy = {"Sql": copy_sql, "Database": args.get("REDSHIFT_DATABASE"), "DbUser": args.get("REDSHIFT_DB_USER")}
        if args.get("REDSHIFT_CLUSTER_ID"): exec_copy["ClusterIdentifier"] = args.get("REDSHIFT_CLUSTER_ID")
        if args.get("REDSHIFT_SECRET_ARN"): exec_copy["SecretArn"] = args.get("REDSHIFT_SECRET_ARN")
        resp2 = redshift.execute_statement(**exec_copy)
        print("Triggered COPY to Redshift, id:", resp2.get("Id"))
    except Exception as e:
        print("Redshift load failed/skipped:", e)
else:
    print("REDSHIFT_IAM_ROLE_ARN not provided; skipping Redshift load.")

job.commit()
print("Silver -> Gold completed.")
