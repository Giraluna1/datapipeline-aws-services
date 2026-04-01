terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = { source = "hashicorp/aws" version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags { tags = var.common_tags }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
  environment  = var.environment
  common_tags  = var.common_tags
  storage_tier_defaults = var.storage_tier_defaults
  lifecycle_days = var.lifecycle_days
}

module "iam" {
  source        = "./modules/iam"
  project_name  = var.project_name
  environment   = var.environment
  common_tags   = var.common_tags
  s3_bucket_names = module.s3.bucket_names
  secrets_arns  = [var.secret_names.app_secret]
}

# Glue Data Catalog database
resource "aws_glue_catalog_database" "this" {
  name = "${var.project_name}_db_${var.environment}"
}

# Crawlers for landing/bronze/silver/gold
resource "aws_glue_crawler" "landing" {
  name          = "energy-landing-crawler-${var.environment}"
  role          = module.iam.glue_role_arn
  database_name = aws_glue_catalog_database.this.name
  s3_target {
    path = "s3://${module.s3.bucket_names["landing"]}/"
  }
  tags = var.common_tags
}

resource "aws_glue_crawler" "bronze" {
  name          = "energy-bronze-crawler-${var.environment}"
  role          = module.iam.glue_role_arn
  database_name = aws_glue_catalog_database.this.name
  s3_target {
    path = "s3://${module.s3.bucket_names["bronze"]}/"
  }
  configuration = jsonencode({ Version = 1.0, CrawlerOutput = { Partitions = { AddOrUpdateBehavior = "InheritFromTable" } } })
  tags = var.common_tags
}

resource "aws_glue_crawler" "silver" {
  name          = "energy-silver-crawler-${var.environment}"
  role          = module.iam.glue_role_arn
  database_name = aws_glue_catalog_database.this.name
  s3_target {
    path = "s3://${module.s3.bucket_names["silver"]}/"
  }
  configuration = jsonencode({ Version = 1.0, CrawlerOutput = { Partitions = { AddOrUpdateBehavior = "InheritFromTable" } } })
  tags = var.common_tags
}

resource "aws_glue_crawler" "gold" {
  name          = "energy-gold-crawler-${var.environment}"
  role          = module.iam.glue_role_arn
  database_name = aws_glue_catalog_database.this.name
  s3_target {
    path = "s3://${module.s3.bucket_names["gold"]}/"
  }
  configuration = jsonencode({ Version = 1.0, CrawlerOutput = { Partitions = { AddOrUpdateBehavior = "InheritFromTable" } } })
  tags = var.common_tags
}

# Lake Formation settings and registrations
resource "aws_lakeformation_data_lake_settings" "settings" {
  admins = var.lf_admin_arns
}

resource "aws_lakeformation_resource" "landing" {
  arn = "arn:aws:s3:::${module.s3.bucket_names["landing"]}"
}
resource "aws_lakeformation_resource" "bronze" {
  arn = "arn:aws:s3:::${module.s3.bucket_names["bronze"]}"
}
resource "aws_lakeformation_resource" "silver" {
  arn = "arn:aws:s3:::${module.s3.bucket_names["silver"]}"
}
resource "aws_lakeformation_resource" "gold" {
  arn = "arn:aws:s3:::${module.s3.bucket_names["gold"]}"
}

resource "aws_lakeformation_permissions" "glue_role_landing" {
  principal   = module.iam.glue_role_arn
  permissions = ["DATA_LOCATION_ACCESS"]
  data_location {
    arn = aws_lakeformation_resource.landing.arn
  }
}
resource "aws_lakeformation_permissions" "glue_role_bronze" {
  principal   = module.iam.glue_role_arn
  permissions = ["DATA_LOCATION_ACCESS"]
  data_location {
    arn = aws_lakeformation_resource.bronze.arn
  }
}
resource "aws_lakeformation_permissions" "glue_role_silver" {
  principal   = module.iam.glue_role_arn
  permissions = ["DATA_LOCATION_ACCESS"]
  data_location {
    arn = aws_lakeformation_resource.silver.arn
  }
}
resource "aws_lakeformation_permissions" "glue_role_gold" {
  principal   = module.iam.glue_role_arn
  permissions = ["DATA_LOCATION_ACCESS"]
  data_location {
    arn = aws_lakeformation_resource.gold.arn
  }
}

# LF: permisos sobre la database del catálogo (governance real)
resource "aws_lakeformation_permissions" "glue_role_database" {
  principal   = module.iam.glue_role_arn
  permissions = ["CREATE_TABLE", "DESCRIBE", "ALTER"]

  database {
    name = aws_glue_catalog_database.this.name
  }
}

resource "aws_lakeformation_permissions" "athena_consumer_database" {
  principal   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/athena-consumer-role-${var.environment}"
  permissions = ["DESCRIBE"]

  database {
    name = aws_glue_catalog_database.this.name
  }
}

resource "aws_lakeformation_permissions" "athena_consumer_tables" {
  principal   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/athena-consumer-role-${var.environment}"
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = aws_glue_catalog_database.this.name
    wildcard      = true
  }
}

# example instantiation of glue job modules for each process
module "bronze_ingestion" {
  source = "./modules/glue/jobs"
  job_name = "energy-bronze-ingestion-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/bronze/energy_ingestion/tasks/bronze_ingestion.py"
    src_bucket  = module.s3.bucket_names["landing"]
    dst_bucket  = module.s3.bucket_names["bronze"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 60
    secret_name = var.secret_names.app_secret
    athena_output = var.athena_output_s3
    additional_python_modules = "awswrangler==3.10.1"
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

module "silver_tx_curated" {
  source = "./modules/glue/jobs"
  job_name = "energy-silver-tx-curated-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/silver/energy_processing/tasks/transacciones_curated.py"
    src_bucket  = module.s3.bucket_names["bronze"]
    dst_bucket  = module.s3.bucket_names["gold"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 60
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

module "silver_tx_agg" {
  source = "./modules/glue/jobs"
  job_name = "energy-silver-tx-agg-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/silver/energy_processing/tasks/transacciones_agg.py"
    src_bucket  = module.s3.bucket_names["bronze"]
    dst_bucket  = module.s3.bucket_names["gold"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 60
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

module "silver_prov_curated" {
  source = "./modules/glue/jobs"
  job_name = "energy-silver-prov-curated-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/silver/energy_processing/tasks/proveedores_curated.py"
    src_bucket  = module.s3.bucket_names["bronze"]
    dst_bucket  = module.s3.bucket_names["gold"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 60
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

module "silver_cli_curated" {
  source = "./modules/glue/jobs"
  job_name = "energy-silver-cli-curated-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/silver/energy_processing/tasks/clientes_curated.py"
    src_bucket  = module.s3.bucket_names["bronze"]
    dst_bucket  = module.s3.bucket_names["gold"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 60
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

module "silver_athena_views" {
  source = "./modules/glue/jobs"
  job_name = "energy-silver-athena-views-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/silver/energy_processing/tasks/athena_views.py"
    worker_type = "G.1X"
    workers     = 2
    timeout     = 30
    athena_output = var.athena_output_s3
    additional_python_modules = "awswrangler==3.10.1"
    additional_arguments = {
      "--GLUE_DATABASE" = aws_glue_catalog_database.this.name
    }
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

module "silver_athena_export" {
  source = "./modules/glue/jobs"
  job_name = "energy-silver-athena-export-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/silver/energy_processing/tasks/athena_export.py"
    dst_bucket  = module.s3.bucket_names["gold"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 30
    athena_output = var.athena_output_s3
    additional_arguments = {
      "--GLUE_DATABASE" = aws_glue_catalog_database.this.name
    }
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

module "gold_analytics" {
  source = "./modules/glue/jobs"
  job_name = "energy-gold-analytics-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/gold/energy_analytics/tasks/gold_analytics.py"
    src_bucket  = module.s3.bucket_names["gold"]
    dst_bucket  = module.s3.bucket_names["gold"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 120
    secret_name = var.secret_names.app_secret
    athena_output = var.athena_output_s3
    additional_python_modules = "awswrangler==3.10.1"
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

# Redshift load from Gold
module "redshift_load" {
  source = "./modules/glue/jobs"
  job_name = "energy-dwh-redshift-load-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/dwh/redshift_load/tasks/redshift_load.py"
    src_bucket  = module.s3.bucket_names["gold"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 60
    redshift_secret_arn   = var.redshift.secret_arn
    redshift_iam_role_arn = var.redshift.iam_role_arn
    additional_python_modules = "awswrangler==3.10.1"
    additional_arguments = {
      "--REDSHIFT_DATABASE"   = var.redshift.database
      "--REDSHIFT_DB_USER"    = var.redshift.db_user
      "--REDSHIFT_CLUSTER_ID" = var.redshift.cluster_id
    }
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

# Glue Workflow and Triggers (native orchestrator)
resource "aws_glue_workflow" "main" {
  name = "energy-workflow-${var.environment}"
  tags = var.common_tags
}

resource "aws_glue_trigger" "t_bronze_schedule" {
  name          = "t-bronze-schedule-${var.environment}"
  type          = "SCHEDULED"
  description   = "Start bronze on schedule"
  schedule      = var.glue_cron_expression
  workflow_name = aws_glue_workflow.main.name
  actions {
    job_name = module.bronze_ingestion.job_name
  }
}

resource "aws_glue_trigger" "t_silver_tx_cur_after_bronze" {
  name          = "t-silver-tx-cur-after-bronze-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions { job_name = module.silver_tx_curated.job_name }
  predicate {
    conditions { job_name = module.bronze_ingestion.job_name state = "SUCCEEDED" }
    logical = "AND"
  }
}

resource "aws_glue_trigger" "t_silver_tx_agg_after_bronze" {
  name          = "t-silver-tx-agg-after-bronze-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions { job_name = module.silver_tx_agg.job_name }
  predicate {
    conditions { job_name = module.bronze_ingestion.job_name state = "SUCCEEDED" }
    logical = "AND"
  }
}

resource "aws_glue_trigger" "t_silver_prov_after_bronze" {
  name          = "t-silver-prov-after-bronze-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions { job_name = module.silver_prov_curated.job_name }
  predicate {
    conditions { job_name = module.bronze_ingestion.job_name state = "SUCCEEDED" }
    logical = "AND"
  }
}

resource "aws_glue_trigger" "t_silver_cli_after_bronze" {
  name          = "t-silver-cli-after-bronze-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions { job_name = module.silver_cli_curated.job_name }
  predicate {
    conditions { job_name = module.bronze_ingestion.job_name state = "SUCCEEDED" }
    logical = "AND"
  }
}

resource "aws_glue_trigger" "t_athena_views_after_bronze" {
  name          = "t-athena-views-after-bronze-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions { job_name = module.silver_athena_views.job_name }
  predicate {
    conditions { job_name = module.bronze_ingestion.job_name state = "SUCCEEDED" }
    logical = "AND"
  }
}

resource "aws_glue_trigger" "t_athena_export_after_views" {
  name          = "t-athena-export-after-views-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions { job_name = module.silver_athena_export.job_name }
  predicate {
    conditions { job_name = module.silver_athena_views.job_name state = "SUCCEEDED" }
    logical = "AND"
  }
}

resource "aws_glue_trigger" "t_gold_after_silver" {
  name          = "t-gold-after-silver-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions {
    job_name = module.gold_analytics.job_name
  }
  predicate {
    conditions { job_name = module.silver_tx_curated.job_name   state = "SUCCEEDED" }
    conditions { job_name = module.silver_tx_agg.job_name       state = "SUCCEEDED" }
    conditions { job_name = module.silver_prov_curated.job_name state = "SUCCEEDED" }
    conditions { job_name = module.silver_cli_curated.job_name  state = "SUCCEEDED" }
    logical = "AND"
  }
}

resource "aws_glue_trigger" "t_redshift_after_gold" {
  name          = "t-redshift-after-gold-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions {
    job_name = module.redshift_load.job_name
  }
  predicate {
    conditions {
      job_name = module.gold_analytics.job_name
      state    = "SUCCEEDED"
    }
    logical = "AND"
  }
}

# Run crawlers after each stage
resource "aws_glue_trigger" "t_crawler_bronze" {
  name          = "t-crawler-bronze-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions {
    crawler_name = aws_glue_crawler.bronze.name
  }
  predicate {
    conditions {
      job_name = module.bronze_ingestion.job_name
      state    = "SUCCEEDED"
    }
    logical = "AND"
  }
}

# ✅ CORREGIDO: espera a todos los jobs silver antes de crawlear silver
resource "aws_glue_trigger" "t_crawler_silver" {
  name          = "t-crawler-silver-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions {
    crawler_name = aws_glue_crawler.silver.name
  }
  predicate {
    conditions { job_name = module.silver_tx_curated.job_name   state = "SUCCEEDED" }
    conditions { job_name = module.silver_tx_agg.job_name       state = "SUCCEEDED" }
    conditions { job_name = module.silver_prov_curated.job_name state = "SUCCEEDED" }
    conditions { job_name = module.silver_cli_curated.job_name  state = "SUCCEEDED" }
    logical = "AND"
  }
}

resource "aws_glue_trigger" "t_crawler_gold" {
  name          = "t-crawler-gold-${var.environment}"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.main.name
  actions {
    crawler_name = aws_glue_crawler.gold.name
  }
  predicate {
    conditions {
      job_name = module.gold_analytics.job_name
      state    = "SUCCEEDED"
    }
    logical = "AND"
  }
}