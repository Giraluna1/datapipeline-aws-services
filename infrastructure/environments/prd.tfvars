project_name = "energy"
environment  = "prd"

aws_region   = "us-east-1"

common_tags = {
  Owner = "Giraluna"
  Project = "EnergyDataLake"
  CostCenter = "DataEngineering"
}

storage_tier_defaults = {
  landing     = "STANDARD"
  bronze      = "INTELLIGENT_TIERING"
  silver      = "INTELLIGENT_TIERING"
  gold        = "STANDARD_IA"
  glue-assets = "STANDARD"
  archive     = "GLACIER"
}

lifecycle_days = {
  to_ia      = 30
  to_glacier = 730
  expire     = 3650
}

secret_names = {
  app_secret = ""
}

redshift = {
  secret_arn   = ""
  iam_role_arn = ""
  database     = ""
  db_user      = ""
  cluster_id   = ""
}

athena_output_s3     = "s3://energy-s3-glue-assets-prd-standard/athena-results/"
glue_cron_expression = "cron(0 2 * * ? *)"
lf_admin_arns        = []
