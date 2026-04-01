project_name = "energy"
environment  = "lab"

aws_region   = "us-east-1"

common_tags = {
  Owner   = "Giraluna"
  Project = "EnergyDataLake"
  Stage   = "QA"
}

storage_tier_defaults = {
  landing     = "STANDARD"
  bronze      = "STANDARD"
  silver      = "STANDARD"
  gold        = "STANDARD"
  glue-assets = "STANDARD"
  archive     = "GLACIER"
}

lifecycle_days = {
  to_ia      = 60
  to_glacier = 1825
  expire     = 3650
}

# Nombre del principal que despliega (ejemplo de patrón solicitado)
deployer_service_account_name = "sa-energy-lab-deployer-us-east-1-temp"

# Rutas/nombres de secretos con patrón solicitado
secret_names = {
  app_secret = "app-energy-lab-glue-us-east-1-temp"
}

redshift = {
  secret_arn   = "arn:aws:secretsmanager:us-east-1:123456789012:secret:db_user-energy-lab-redshift-us-east-1-temp"
  iam_role_arn = "arn:aws:iam::123456789012:role/sa-energy-lab-redshift-us-east-1-temp"
  database     = "energy_lab"
  db_user      = "db_user-energy-lab-redshift-us-east-1-temp"
  cluster_id   = "energy-lab-cluster"
}

athena_output_s3     = "s3://energy-s3-glue-assets-lab-standard/athena-results/"
glue_cron_expression = "cron(0 4 * * ? *)"
lf_admin_arns        = ["arn:aws:iam::123456789012:role/sa-energy-lab-admin-us-east-1-temp"]
