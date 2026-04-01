variable "project_name" { type = string }
variable "environment"  { type = string }
variable "common_tags"  { type = map(string) default = {} }
variable "s3_bucket_names" { type = map(string) }
variable "secrets_arns" { type = list(string) default = [] }

locals {
  role_name = "${var.project_name}-glue-role-${var.environment}"
  s3_bucket_arns  = [for b in values(var.s3_bucket_names) : "arn:aws:s3:::${b}"]
  s3_object_arns  = [for b in values(var.s3_bucket_names) : "arn:aws:s3:::${b}/*"]
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "glue_role" {
  name               = local.role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = var.common_tags
}

data "aws_iam_policy_document" "glue_inline" {
  statement {
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = local.s3_bucket_arns
  }
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject","s3:PutObject","s3:DeleteObject","s3:AbortMultipartUpload","s3:ListBucketMultipartUploads"
    ]
    resources = local.s3_object_arns
  }
  statement {
    effect = "Allow"
    actions = [
      "glue:GetDatabase","glue:GetDatabases","glue:CreateDatabase","glue:UpdateDatabase","glue:DeleteDatabase",
      "glue:GetTable","glue:GetTables","glue:CreateTable","glue:UpdateTable","glue:DeleteTable",
      "glue:BatchCreatePartition","glue:CreatePartition","glue:UpdatePartition","glue:DeletePartition",
      "glue:StartJobRun","glue:GetJobRun","glue:GetJobRuns","glue:GetJob","glue:BatchStopJobRun"
    ]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "lakeformation:GetDataAccess","lakeformation:GrantPermissions","lakeformation:RevokePermissions",
      "lakeformation:ListPermissions","lakeformation:ListResources","lakeformation:GetEffectivePermissionsForPath"
    ]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"
    ]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = length(var.secrets_arns) > 0 ? var.secrets_arns : ["*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "athena:StartQueryExecution","athena:GetQueryExecution","athena:GetQueryResults",
      "athena:ListQueryExecutions","athena:StopQueryExecution"
    ]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "redshift-data:ExecuteStatement","redshift-data:DescribeStatement","redshift-data:GetStatementResult"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "glue_policy" {
  name   = "${var.project_name}-glue-policy-${var.environment}"
  path   = "/"
  policy = data.aws_iam_policy_document.glue_inline.json
}

resource "aws_iam_role_policy_attachment" "attach_glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "attach_lf_admin" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSLakeFormationDataAdmin"
}

resource "aws_iam_role_policy_attachment" "attach_inline" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.glue_policy.arn
}
