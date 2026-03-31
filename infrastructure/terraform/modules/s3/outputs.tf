output "bucket_names" {
  description = "Mapa de buckets por layer"
  value = { for k, v in aws_s3_bucket.layer : k => v.bucket }
}
