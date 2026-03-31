#!/bin/bash
set -e
ENVIRONMENT=${1:-dev}
ACTION=${2:-plan}
cd infrastructure/terraform
terraform init
terraform workspace select $ENVIRONMENT || terraform workspace new $ENVIRONMENT
case $ACTION in
  "plan")
    terraform plan -var-file="../environments/${ENVIRONMENT}.tfvars" -out="${ENVIRONMENT}.tfplan"
    ;;
  "apply")
    terraform apply -var-file="../environments/${ENVIRONMENT}.tfvars" -auto-approve
    ;;
  "destroy")
    terraform destroy -var-file="../environments/${ENVIRONMENT}.tfvars" -auto-approve
    ;;
  *)
    echo "Invalid action"
    exit 1
    ;;
esac
echo "Done."
