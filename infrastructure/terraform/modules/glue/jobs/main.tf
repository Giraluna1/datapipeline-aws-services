variable "job_name" { type = string }
variable "job_config" { type = map(any) }
variable "s3_buckets" { type = map(string) }
variable "glue_role_arn" { type = string }
variable "glue_version" { type = string default = "4.0" }
variable "environment" { type = string }
variable "common_tags" { type = map(string) default = {} }

resource "aws_s3_object" "job_script" {
  bucket = var.s3_buckets["glue-assets"]
  key    = "scripts/${var.environment}/${replace(var.job_config["script_path"], "${path.module}/../../../../", "")}"
  source = var.job_config["script_path"]
  etag   = filemd5(var.job_config["script_path"])
  tags   = var.common_tags
}

resource "aws_glue_job" "job" {
  name         = var.job_name
  role_arn     = var.glue_role_arn
  glue_version = var.glue_version

  command {
    script_location = "s3://${var.s3_buckets["glue-assets"]}/${aws_s3_object.job_script.key}"
    python_version  = "3"
  }

  default_arguments = merge(
    {
      "--job-bookmark-option"    = "job-bookmark-enable"
      "--ENVIRONMENT"            = var.environment
      "--SRC_BUCKET"             = lookup(var.job_config, "src_bucket", var.s3_buckets["landing"])
      "--DST_BUCKET"             = lookup(var.job_config, "dst_bucket", var.s3_buckets["bronze"])
      "--SECRET_NAME"            = lookup(var.job_config, "secret_name", "")
      "--REDSHIFT_SECRET_ARN"    = lookup(var.job_config, "redshift_secret_arn", "")
      "--ATHENA_OUTPUT"          = lookup(var.job_config, "athena_output", "")
      "--REDSHIFT_IAM_ROLE_ARN"  = lookup(var.job_config, "redshift_iam_role_arn", "")
    },
    lookup(var.job_config, "additional_arguments", {})
  )

  worker_type       = lookup(var.job_config, "worker_type", "G.1X")
  number_of_workers = lookup(var.job_config, "workers", 2)
  timeout           = lookup(var.job_config, "timeout", 60)
  max_retries       = lookup(var.job_config, "max_retries", 1)

  tags = var.common_tags

  depends_on = [aws_s3_object.job_script]
}
