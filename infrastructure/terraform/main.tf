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
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}

module "silver_processing" {
  source = "./modules/glue/jobs"
  job_name = "energy-silver-processing-${var.environment}"
  job_config = {
    script_path = "${path.module}/../../processes/silver/energy_processing/tasks/silver_processing.py"
    src_bucket  = module.s3.bucket_names["bronze"]
    dst_bucket  = module.s3.bucket_names["silver"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 90
    secret_name = var.secret_names.app_secret
    athena_output = var.athena_output_s3
    redshift_secret_arn = var.redshift.secret_arn
    redshift_iam_role_arn = var.redshift.iam_role_arn
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
    src_bucket  = module.s3.bucket_names["silver"]
    dst_bucket  = module.s3.bucket_names["gold"]
    worker_type = "G.1X"
    workers     = 2
    timeout     = 120
    secret_name = var.secret_names.app_secret
    athena_output = var.athena_output_s3
  }
  s3_buckets    = module.s3.bucket_names
  glue_role_arn = module.iam.glue_role_arn
  environment   = var.environment
  common_tags   = var.common_tags
}
