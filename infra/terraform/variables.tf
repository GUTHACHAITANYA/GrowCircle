variable "aws_region" {
  description = "AWS Mumbai region for local data residency under DPDP Act 2023"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment name (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "VPC Classless Inter-Domain Routing block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_instance_class" {
  description = "RDS PostgreSQL compute instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "db_allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 50
}

variable "db_max_allocated_storage" {
  description = "Maximum storage autoscaling ceiling in GB"
  type        = number
  default     = 200
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "growcircle_prod"
}

variable "db_username" {
  description = "Database master administrator username"
  type        = string
  default     = "growcircle_admin"
  sensitive   = true
}

variable "redis_node_type" {
  description = "AWS ElastiCache Redis node type"
  type        = string
  default     = "cache.t4g.medium"
}

variable "container_image" {
  description = "ECR Docker image URI for GrowCircle backend engine"
  type        = string
  default     = "public.ecr.aws/growcircle/backend:1.0.0"
}

variable "app_cpu" {
  description = "CPU units allocated for App Runner / Fargate container (1024 = 1 vCPU)"
  type        = string
  default     = "1024"
}

variable "app_memory" {
  description = "Memory allocated for App Runner / Fargate container in MB"
  type        = string
  default     = "2048"
}
