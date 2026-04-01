project_name = "energy"
environment  = "dev"

aws_region   = "us-east-1"

common_tags = {
  Owner = "Giraluna"
  Project = "EnergyDataLake"
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
  to_ia      = 90
  to_glacier = 3650
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

athena_output_s3     = "s3://energy-s3-glue-assets-dev-standard/athena-results/"
glue_cron_expression = "cron(0 3 * * ? *)"
lf_admin_arns        = []
