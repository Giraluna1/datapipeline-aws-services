import os, csv, time
import boto3

REGION = os.getenv("AWS_REGION","us-east-1")
CLUSTER_ID = os.getenv("REDSHIFT_CLUSTER_ID")
DATABASE = os.getenv("REDSHIFT_DATABASE")
DB_USER = os.getenv("REDSHIFT_DB_USER")
SECRET_ARN = os.getenv("REDSHIFT_SECRET_ARN")
OUTPUT_DIR = os.getenv("EXPORT_OUTPUT_DIR","exports")

client = boto3.client('redshift-data', region_name=REGION)

def run_query(sql: str):
    params = {
        "Sql": sql,
        "Database": DATABASE,
        "DbUser": DB_USER
    }
    if CLUSTER_ID: params["ClusterIdentifier"] = CLUSTER_ID
    if SECRET_ARN: params["SecretArn"] = SECRET_ARN
    resp = client.execute_statement(**params)
    qid = resp["Id"]
    while True:
        d = client.describe_statement(Id=qid)
        if d["Status"] in ("FINISHED","FAILED","ABORTED"): break
        time.sleep(0.5)
    if d["Status"] != "FINISHED":
        raise RuntimeError(f"Query failed: {d}")
    return client.get_statement_result(Id=qid)

def result_to_csv(result, path):
    cols = [c["name"] for c in result["ColumnMetadata"]]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in result["Records"]:
            row = []
            for cell in r:
                if "stringValue" in cell: row.append(cell["stringValue"])
                elif "longValue" in cell: row.append(cell["longValue"])
                elif "doubleValue" in cell: row.append(cell["doubleValue"])
                elif "booleanValue" in cell: row.append(cell["booleanValue"])
                else: row.append("")
            w.writerow(row)

if __name__ == "__main__":
    r1 = run_query("SELECT * FROM gold.transacciones ORDER BY fecha_transaccion, id_transaccion LIMIT 1000")
    result_to_csv(r1, os.path.join(OUTPUT_DIR, "transacciones.csv"))
    try:
        r2 = run_query("SELECT * FROM gold.proveedores ORDER BY nombre_proveedor LIMIT 1000")
        result_to_csv(r2, os.path.join(OUTPUT_DIR, "proveedores.csv"))
    except Exception:
        pass
    print("Export completed to", OUTPUT_DIR)
