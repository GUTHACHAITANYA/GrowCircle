terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }

  backend "s3" {
    bucket         = "growcircle-terraform-state-mumbai"
    key            = "prod/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "growcircle-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "GrowCircle"
      Environment = var.environment
      Region      = "ap-south-1 (Mumbai)"
      Compliance  = "DPDP-Act-2023"
      ManagedBy   = "Terraform"
    }
  }
}
