#!/usr/bin/env python3
"""Ingesta Bronze

Lee archivos en landing (contratos.csv y riesgos_precios.csv), separa y normaliza
datasets de negocio en Parquet particionado por fecha de procesamiento:
- transacciones: tipa cantidades, precios y fechas, desde contratos.csv
- proveedores: tipa capacidad y fecha de contrato, desde contratos.csv
- clientes: publica tipo_cliente cuando existe en contratos.csv
- riesgos_precios: tipa riesgo_pct cuando corresponde

Entradas:
- s3://<landing>/contratos.csv o contratos/contratos.csv
- s3://<landing>/riesgos_precios.csv o riesgos/riesgos_precios.csv

Salidas:
- s3://<bronze>/{transacciones,proveedores,clientes,riesgos_precios}/year=YYYY/month=MM/day=DD/
"""
import sys, json
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import current_date, year, month, dayofmonth, col, to_date, lit, when

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

landing_root = f"s3://{args['SRC_BUCKET']}/"
bronze_root  = f"s3://{args['DST_BUCKET']}/"

contracts_paths = [landing_root + "contratos.csv", landing_root + "contratos/contratos.csv"]
risks_paths     = [landing_root + "riesgos_precios.csv", landing_root + "riesgos/riesgos_precios.csv"]

contracts_df = None
for p in contracts_paths:
    try:
        contracts_df = spark.read.option("header","true").csv(p)
        break
    except Exception as e:
        print("Contracts not found at", p, e)

risks_df = None
for p in risks_paths:
    try:
        risks_df = spark.read.option("header","true").csv(p)
        break
    except Exception as e:
        print("Risks not found at", p, e)

if contracts_df is not None:
    cols = contracts_df.columns
    tx_cols = ["id_transaccion","fecha_transaccion","tipo_transaccion","cliente_proveedor","cantidad_kwh","precio_kwh","tipo_energia","hora_transaccion","ciudad"]
    if all(c in cols for c in tx_cols):
        tx = contracts_df.select(*tx_cols).where(col("id_transaccion").isNotNull())
        tx = tx.withColumn("cantidad_kwh", col("cantidad_kwh").cast("double")) \
               .withColumn("precio_kwh", col("precio_kwh").cast("double")) \
               .withColumn("fecha_transaccion", to_date(col("fecha_transaccion")))
        tx = tx.withColumn("processed_date", current_date())
        tx = tx.withColumn("year", year(col("processed_date"))) \
               .withColumn("month", month(col("processed_date"))) \
               .withColumn("day", dayofmonth(col("processed_date")))
        tx.write.mode("append").partitionBy("year","month","day").parquet(bronze_root + "transacciones/")
    prov_cols = ["nombre_proveedor","tipo_energia","capacidad_mw","ciudad","fecha_contrato"]
    if all(c in cols for c in prov_cols):
        pv = contracts_df.select(*prov_cols).where(col("nombre_proveedor").isNotNull())
        pv = pv.withColumn("capacidad_mw", col("capacidad_mw").cast("double"))
        pv = pv.withColumn("fecha_contrato", to_date(col("fecha_contrato")))
        pv = pv.withColumn("processed_date", current_date())
        pv = pv.withColumn("year", year(col("processed_date"))) \
               .withColumn("month", month(col("processed_date"))) \
               .withColumn("day", dayofmonth(col("processed_date")))
        pv.write.mode("append").partitionBy("year","month","day").parquet(bronze_root + "proveedores/")
    if "tipo_cliente" in cols and "cliente_proveedor" in cols:
        select_cols = [
            col("cliente_proveedor").alias("cliente_proveedor"),
            when(col("tipo_cliente").isNull(), lit("desconocido")).otherwise(col("tipo_cliente")).alias("tipo_cliente")
        ]
        if "ciudad" in cols:
            select_cols.append(col("ciudad"))
        cl = contracts_df.where(col("cliente_proveedor").isNotNull()).select(*select_cols)
        cl = cl.withColumn("processed_date", current_date())
        cl = cl.withColumn("year", year(col("processed_date"))) \
               .withColumn("month", month(col("processed_date"))) \
               .withColumn("day", dayofmonth(col("processed_date")))
        cl.write.mode("append").partitionBy("year","month","day").parquet(bronze_root + "clientes/")

if risks_df is not None:
    r = risks_df
    if "riesgo_pct" in r.columns:
        r = r.withColumn("riesgo_pct", col("riesgo_pct").cast("double"))
    r = r.withColumn("processed_date", current_date())
    r = r.withColumn("year", year(col("processed_date"))) \
         .withColumn("month", month(col("processed_date"))) \
         .withColumn("day", dayofmonth(col("processed_date")))
    r.write.mode("append").partitionBy("year","month","day").parquet(bronze_root + "riesgos_precios/")

job.commit()
print("Bronze ingestion completed.")
