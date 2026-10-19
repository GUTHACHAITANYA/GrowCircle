output "api_service_url" {
  description = "Public URL of the GrowCircle App Runner backend service"
  value       = "https://${aws_apprunner_service.backend.service_url}"
}

output "database_endpoint" {
  description = "Endpoint address of the RDS PostgreSQL cluster"
  value       = aws_db_instance.postgres.endpoint
}

output "redis_primary_endpoint" {
  description = "Primary endpoint address of the ElastiCache Redis replication group"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "media_s3_bucket" {
  description = "S3 bucket for produce media and audio notes"
  value       = aws_s3_bucket.media_bucket.bucket
}

output "vpc_id" {
  description = "ID of the GrowCircle VPC in Mumbai"
  value       = aws_vpc.main.id
}
