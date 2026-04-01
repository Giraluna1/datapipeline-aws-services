#!/usr/bin/env python3
"""Carga Gold → Redshift (DWH)

Crea esquemas/tablas si no existen y carga datos curados y agregados desde la
zona gold en S3 hacia Redshift usando COPY Parquet con Redshift Data API.
Refleja el esquema de negocio del sample para consultas y reporting.

Entradas:
- s3://<gold>/transacciones_curated/, transacciones_agg/, proveedores/

Objetivo:
- Schemas: gold, analytics
- Tablas: gold.transacciones, gold.proveedores, analytics.transacciones_agg
"""
import sys, time
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, [
    "JOB_NAME","SRC_BUCKET","ENVIRONMENT",
    "REDSHIFT_SECRET_ARN","REDSHIFT_IAM_ROLE_ARN",
    "REDSHIFT_DATABASE","REDSHIFT_DB_USER","REDSHIFT_CLUSTER_ID"
])

sc = SparkContext()
glueContext = GlueContext(sc)
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

src_path = f"s3://{args['SRC_BUCKET']}/transacciones_agg/"
iam_role = args.get("REDSHIFT_IAM_ROLE_ARN")

if iam_role:
    redshift = boto3.client("redshift-data")
    db = args.get("REDSHIFT_DATABASE")
    user = args.get("REDSHIFT_DB_USER")
    create_sql = """
    CREATE SCHEMA IF NOT EXISTS gold;
    CREATE SCHEMA IF NOT EXISTS analytics;
    CREATE TABLE IF NOT EXISTS gold.transacciones (
      id_transaccion VARCHAR(64),
      fecha_transaccion DATE,
      tipo_transaccion VARCHAR(32),
      cliente_proveedor VARCHAR(256),
      cantidad_kwh DOUBLE PRECISION,
      precio_kwh DOUBLE PRECISION,
      tipo_energia VARCHAR(64),
      hora_transaccion VARCHAR(16),
      ciudad VARCHAR(128)
    );
    CREATE TABLE IF NOT EXISTS analytics.transacciones_agg (
      tipo_energia VARCHAR(64),
      ciudad VARCHAR(128),
      fecha_transaccion DATE,
      total_kwh DOUBLE PRECISION,
      avg_precio_kwh DOUBLE PRECISION
    );
    CREATE TABLE IF NOT EXISTS gold.proveedores (
      nombre_proveedor VARCHAR(256),
      tipo_energia VARCHAR(64),
      capacidad_mw DOUBLE PRECISION,
      ciudad VARCHAR(128),
      fecha_contrato DATE
    );
    """
    exec_create = {"Sql": create_sql, "Database": db, "DbUser": user}
    if args.get("REDSHIFT_CLUSTER_ID"): exec_create["ClusterIdentifier"] = args.get("REDSHIFT_CLUSTER_ID")
    if args.get("REDSHIFT_SECRET_ARN"): exec_create["SecretArn"] = args.get("REDSHIFT_SECRET_ARN")
    resp = redshift.execute_statement(**exec_create)
    stmt_id = resp["Id"]
    while True:
        desc = redshift.describe_statement(Id=stmt_id)
        if desc["Status"] in ("FINISHED","FAILED","ABORTED"): break
        time.sleep(1)
    copy_sql = f"""
    COPY gold.transacciones
    FROM 's3://{args['SRC_BUCKET']}/transacciones_curated/'
    IAM_ROLE '{iam_role}'
    FORMAT AS PARQUET;
    COPY analytics.transacciones_agg
    FROM 's3://{args['SRC_BUCKET']}/transacciones_agg/'
    IAM_ROLE '{iam_role}'
    FORMAT AS PARQUET;
    COPY gold.proveedores
    FROM 's3://{args['SRC_BUCKET']}/proveedores/'
    IAM_ROLE '{iam_role}'
    FORMAT AS PARQUET;
    CREATE OR REPLACE VIEW gold.v_ventas AS
      SELECT * FROM gold.transacciones WHERE lower(tipo_transaccion)='venta';
    CREATE OR REPLACE VIEW gold.v_compras AS
      SELECT * FROM gold.transacciones WHERE lower(tipo_transaccion)='compra';
    CREATE OR REPLACE VIEW gold.v_clientes AS
      SELECT cliente_proveedor AS cliente, max(ciudad) AS ciudad
      FROM gold.transacciones
      WHERE lower(tipo_transaccion)='venta' AND cliente_proveedor IS NOT NULL
      GROUP BY cliente_proveedor;
    """
    exec_copy = {"Sql": copy_sql, "Database": db, "DbUser": user}
    if args.get("REDSHIFT_CLUSTER_ID"): exec_copy["ClusterIdentifier"] = args.get("REDSHIFT_CLUSTER_ID")
    if args.get("REDSHIFT_SECRET_ARN"): exec_copy["SecretArn"] = args.get("REDSHIFT_SECRET_ARN")
    resp2 = redshift.execute_statement(**exec_copy)
    print("COPY to Redshift triggered:", resp2.get("Id"))
else:
    print("REDSHIFT_IAM_ROLE_ARN not provided; skipping Redshift load.")

job.commit()
print("Gold -> Redshift load completed.")
