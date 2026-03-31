variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
}

variable "environment" {
  description = "Environment (dev|lab|prd)"
  type        = string
}

variable "common_tags" {
  description = "Tags comunes"
  type        = map(string)
  default     = {}
}

variable "storage_tier_defaults" {
  description = "Storage class defaults per layer"
  type = map(string)
  default = {
    landing     = "STANDARD"
    bronze      = "INTELLIGENT_TIERING"
    silver      = "INTELLIGENT_TIERING"
    gold        = "STANDARD_IA"
    glue-assets = "STANDARD"
    archive     = "GLACIER"
  }
}

variable "lifecycle_days" {
  description = "Días para transiciones/expiraciones"
  type = object({
    to_ia      = number
    to_glacier = number
    expire     = number
  })
  default = {
    to_ia      = 30
    to_glacier = 730
    expire     = 3650
  }
}
