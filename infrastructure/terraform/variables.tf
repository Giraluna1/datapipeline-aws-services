variable "aws_region" {
  type        = string
  description = "AWS Region (e.g., us-east-1 para South Carolina)"
}

variable "project_name" {
  type        = string
  description = "Nombre del proyecto"
}

variable "environment" {
  type        = string
  description = "Entorno (dev|lab|prd)"
}

variable "common_tags" {
  type        = map(string)
  description = "Tags comunes"
  default     = {}
}

variable "storage_tier_defaults" {
  type        = map(string)
  description = "Clases de almacenamiento por capa"
}

variable "lifecycle_days" {
  description = "Días para transiciones/expiración de objetos por capa"
  type = object({
    to_ia      = number
    to_glacier = number
    expire     = number
  })
}

variable "secret_names" {
  description = "Secrets usados por los Jobs de Glue"
  type = object({
    app_secret = string
  })
}

variable "redshift" {
  description = "Parámetros para la carga a Redshift"
  type = object({
    secret_arn   = string
    iam_role_arn = string
    database     = string
    db_user      = string
    cluster_id   = string
  })
}

variable "athena_output_s3" {
  type        = string
  description = "Ruta S3 para resultados de Athena (s3://bucket/prefix/)"
}

variable "glue_cron_expression" {
  type        = string
  description = "Expresión CRON para el trigger programado de Glue"
  default     = "cron(0 3 * * ? *)"
}

variable "lf_admin_arns" {
  type        = list(string)
  description = "ARNs de administradores de Lake Formation"
  default     = []
}

variable "deployer_service_account_name" {
  type        = string
  description = "Nombre de la service account/IAM principal que despliega (p.ej., sa-<proyecto>-<ambiente>-<recurso>-<zona>-<temp>)"
  default     = ""
}
