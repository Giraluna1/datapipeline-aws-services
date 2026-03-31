locals {
  layers = ["landing", "bronze", "silver", "gold", "glue-assets", "archive"]
}

resource "aws_s3_bucket" "layer" {
  for_each = toset(local.layers)

  bucket = "${var.project_name}-s3-${each.key}-${var.environment}-${lower(replace(var.storage_tier_defaults[each.key], "_", ""))}"
  acl    = "private"

  versioning { enabled = true }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = merge(var.common_tags, { "Layer" = each.key, "Environment" = var.environment })
}

resource "aws_s3_bucket_lifecycle_configuration" "layer_lifecycle" {
  for_each = aws_s3_bucket.layer

  bucket = each.value.id

  rule {
    id     = "default-transition-${each.key}"
    status = "Enabled"

    filter { prefix = "" }

    transition {
      days          = var.lifecycle_days.to_ia
      storage_class = lookup(var.storage_tier_defaults, each.key, "STANDARD_IA")
    }

    transition {
      days          = var.lifecycle_days.to_glacier
      storage_class = "GLACIER"
    }

    expiration { days = var.lifecycle_days.expire }

    noncurrent_version_transition {
      days          = var.lifecycle_days.to_ia
      storage_class = "GLACIER"
    }
  }
}
