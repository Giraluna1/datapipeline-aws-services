#!/usr/bin/env python3
"""Silver Task: athena_export

Ejecuta UNLOAD desde Athena para exportar vistas lógicas a CSV en S3 (zona gold/exports):
- v_clientes → s3://<gold>/exports/v_clientes/
- v_ventas   → s3://<gold>/exports/v_ventas/
- v_compras  → s3://<gold>/exports/v_compras/
"""
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
import boto3

args = getResolvedOptions(sys.argv, [
    "JOB_NAME","DST_BUCKET","GLUE_DATABASE","ATHENA_OUTPUT"
])

sc = SparkContext()
glueContext = GlueContext(sc)
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

db = args["GLUE_DATABASE"]
out = args["ATHENA_OUTPUT"]
gold_bucket = args["DST_BUCKET"]

ath = boto3.client("athena")

def run(sql):
    q = ath.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": db},
        ResultConfiguration={"OutputLocation": out}
    )
    qid = q["QueryExecutionId"]
    while True:
        d = ath.get_query_execution(QueryExecutionId=qid)
        s = d["QueryExecution"]["Status"]["State"]
        if s in ("SUCCEEDED","FAILED","CANCELLED"):
            break

run(f"UNLOAD (SELECT * FROM v_clientes) TO 's3://{gold_bucket}/exports/v_clientes/' WITH (format='TEXTFILE', field_delimiter=',')")
run(f"UNLOAD (SELECT * FROM v_ventas)   TO 's3://{gold_bucket}/exports/v_ventas/'   WITH (format='TEXTFILE', field_delimiter=',')")
run(f"UNLOAD (SELECT * FROM v_compras)  TO 's3://{gold_bucket}/exports/v_compras/'  WITH (format='TEXTFILE', field_delimiter=',')")

job.commit()
print("Silver task athena_export completed.")
