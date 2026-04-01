#!/usr/bin/env python3
"""Silver Task: athena_views

Crea/actualiza vistas lógicas en Athena (Glue Data Catalog) sobre las tablas
catalogadas (transacciones, clientes, proveedores). Espera a que existan en el
Catálogo antes de ejecutar los DDL.
"""
import sys, os, time
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, [
    "JOB_NAME","ENVIRONMENT","GLUE_DATABASE","ATHENA_OUTPUT"
])

sc = SparkContext()
glueContext = GlueContext(sc)
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

glue = boto3.client("glue")
ath = boto3.client("athena")
db = args["GLUE_DATABASE"]
out = args["ATHENA_OUTPUT"]

def wait_table(name, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            glue.get_table(DatabaseName=db, Name=name)
            return
        except glue.exceptions.EntityNotFoundException:
            time.sleep(2)
    print(f"Table {name} not found in Glue within timeout; continuing")

for t in ["transacciones","clientes","proveedores"]:
    wait_table(t)

def run_ddl(sql):
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

job.commit()
print("Silver task athena_views completed.")
