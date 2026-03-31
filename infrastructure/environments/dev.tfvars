project_name = "energy"
environment  = "dev"

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
