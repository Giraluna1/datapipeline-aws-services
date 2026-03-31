import os, boto3
import awswrangler as wr

AWS_REGION = os.getenv("AWS_REGION","us-east-1")
ATHENA_OUTPUT = os.getenv("ATHENA_OUTPUT","s3://my-athena-results-bucket/athena-results/")

session = boto3.Session(region_name=AWS_REGION)

def run_athena_query(sql: str, database: str):
    df = wr.athena.read_sql_query(sql=sql, database=database, s3_output=ATHENA_OUTPUT, boto3_session=session)
    return df

if __name__ == "__main__":
    db = "energy_database_prd"
    sql = """
    SELECT tipo_energia, COUNT(*) AS cnt, AVG(avg_precio_kwh) as avg_price
    FROM transacciones
    WHERE year = 2024
    GROUP BY tipo_energia
    ORDER BY cnt DESC
    LIMIT 50
    """
    df = run_athena_query(sql, db)
    print(df)
