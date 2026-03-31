import os, boto3, time

REGION = os.getenv("AWS_REGION","us-east-1")
CLUSTER_ID = os.getenv("REDSHIFT_CLUSTER_ID")
DATABASE = os.getenv("REDSHIFT_DATABASE")
DB_USER = os.getenv("REDSHIFT_DB_USER")
SECRET_ARN = os.getenv("REDSHIFT_SECRET_ARN")

client = boto3.client('redshift-data', region_name=REGION)

def run_redshift_sql(sql: str):
    resp = client.execute_statement(
        ClusterIdentifier=CLUSTER_ID,
        Database=DATABASE,
        DbUser=DB_USER,
        Sql=sql,
        SecretArn=SECRET_ARN
    )
    id = resp['Id']
    while True:
        r = client.describe_statement(Id=id)
        if r['Status'] in ('FINISHED','ABORTED','FAILED'):
            break
        time.sleep(1)
    if r['Status'] != 'FINISHED':
        raise Exception(f"Query failed: {r}")
    return client.get_statement_result(Id=id)

if __name__ == "__main__":
    print(run_redshift_sql("SELECT 1;"))
