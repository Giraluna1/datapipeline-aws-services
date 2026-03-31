project_name = "energy"
environment  = "prd"

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
