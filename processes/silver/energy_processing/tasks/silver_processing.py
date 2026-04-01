#!/usr/bin/env python3
"""Procesamiento Silver → Gold

Lee datasets estandarizados en bronze y publica dos vistas en gold:
- transacciones_curated: esquema de negocio curado (equivalente al sample)
- transacciones_agg: agregados por tipo_energia, ciudad y fecha_transaccion
Además, si existen proveedores/clientes en bronze, los copia/tipea a gold.
Escribe siempre en Parquet particionado por fecha de procesamiento.

Entradas:
- s3://<bronze>/transacciones/, proveedores/ y clientes/ (si existen)

Salidas:
- s3://<gold>/transacciones_curated/, transacciones_agg/, proveedores/, clientes/
"""
import sys, json, os
import boto3, awswrangler as wr
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, current_date, year, month, dayofmonth, to_date

args = getResolvedOptions(sys.argv, [
    "JOB_NAME","SRC_BUCKET","DST_BUCKET","ENVIRONMENT","SECRET_NAME",
    "ATHENA_OUTPUT","GLUE_DATABASE"
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

s3_silver_tx   = f"s3://{args['SRC_BUCKET']}/transacciones/"
s3_silver_prov = f"s3://{args['SRC_BUCKET']}/proveedores/"
s3_silver_cli  = f"s3://{args['SRC_BUCKET']}/clientes/"
s3_gold_agg   = f"s3://{args['DST_BUCKET']}/transacciones_agg/"
s3_gold_cur   = f"s3://{args['DST_BUCKET']}/transacciones_curated/"
s3_gold_prov  = f"s3://{args['DST_BUCKET']}/proveedores/"
s3_gold_cli   = f"s3://{args['DST_BUCKET']}/clientes/"

df = spark.read.parquet(s3_silver_tx)

# Curated (mantener esquema de negocio)
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
df_cur.write.mode("append").partitionBy("year","month","day").parquet(s3_gold_cur)

# Agregado para analítica y DWH
df_agg = df.groupBy("tipo_energia","ciudad","fecha_transaccion").agg(
    {"cantidad_kwh":"sum","precio_kwh":"avg"}
).withColumnRenamed("sum(cantidad_kwh)","total_kwh") \
 .withColumnRenamed("avg(precio_kwh)","avg_precio_kwh") \
 .withColumn("processed_date", current_date())

df_final = df_agg.withColumn("year", year(col("processed_date"))) \
                 .withColumn("month", month(col("processed_date"))) \
                 .withColumn("day", dayofmonth(col("processed_date")))

df_final.write.mode("append").partitionBy("year","month","day").parquet(s3_gold_agg)

try:
    df_prov = spark.read.parquet(s3_silver_prov)
    df_prov = df_prov.withColumn("capacidad_mw", col("capacidad_mw").cast("double"))
    if "fecha_contrato" in df_prov.columns:
        df_prov = df_prov.withColumn("fecha_contrato", to_date(col("fecha_contrato")))
    df_prov = df_prov.withColumn("processed_date", current_date())
    df_prov = df_prov.withColumn("year", year(col("processed_date"))) \
                     .withColumn("month", month(col("processed_date"))) \
                     .withColumn("day", dayofmonth(col("processed_date")))
    df_prov.write.mode("append").partitionBy("year","month","day").parquet(s3_gold_prov)
    print("Proveedores curated written")
except Exception as e:
    print("Skipping proveedores:", e)

try:
    df_cli = spark.read.parquet(s3_silver_cli)
    df_cli = df_cli.withColumn("processed_date", current_date())
    df_cli = df_cli.withColumn("year", year(col("processed_date"))) \
                   .withColumn("month", month(col("processed_date"))) \
                   .withColumn("day", dayofmonth(col("processed_date")))
    df_cli.write.mode("append").partitionBy("year","month","day").parquet(s3_gold_cli)
    print("Clientes curated written")
except Exception as e:
    print("Skipping clientes:", e)

try:
    session = boto3.Session()
    glue_db = args.get("GLUE_DATABASE") or os.environ.get("GLUE_DATABASE")
    output_loc = args.get("ATHENA_OUTPUT")
    if glue_db and output_loc:
        ath = boto3.client("athena")
        def run_ddl(sql):
            q = ath.start_query_execution(
                QueryString=sql,
                QueryExecutionContext={"Database": glue_db},
                ResultConfiguration={"OutputLocation": output_loc}
            )
            qid = q["QueryExecutionId"]
            while True:
                d = ath.get_query_execution(QueryExecutionId=qid)
                s = d["QueryExecution"]["Status"]["State"]
                if s in ("SUCCEEDED","FAILED","CANCELLED"): break
        run_ddl("CREATE OR REPLACE VIEW v_servicio AS SELECT DISTINCT tipo_energia FROM transacciones")
        run_ddl("CREATE OR REPLACE VIEW v_ventas AS SELECT * FROM transacciones WHERE lower(tipo_transaccion)='venta'")
        run_ddl("CREATE OR REPLACE VIEW v_compras AS SELECT * FROM transacciones WHERE lower(tipo_transaccion)='compra'")
        run_ddl("""
        CREATE OR REPLACE VIEW v_clientes AS
        SELECT t.cliente_proveedor AS cliente,
               coalesce(max(c.tipo_cliente), 'desconocido') AS tipo_cliente,
               max(t.ciudad) AS ciudad
        FROM transacciones t
        LEFT JOIN clientes c
          ON t.cliente_proveedor = c.cliente_proveedor
        WHERE t.cliente_proveedor IS NOT NULL
        GROUP BY t.cliente_proveedor
        """)
        print("Athena logical model created: v_servicio, v_ventas, v_compras, v_clientes")
    else:
        print("ATHENA_OUTPUT or GLUE_DATABASE not provided; skipping Athena views.")
except Exception as e:
    print("Athena validation failed/skipped:", e)

job.commit()
print("Silver -> Gold completed.")
