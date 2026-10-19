# ElastiCache Redis Subnet Group
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "growcircle-${var.environment}-redis-subnets"
  subnet_ids = [aws_subnet.database_1.id, aws_subnet.database_2.id]
}

# Redis Security Group
resource "aws_security_group" "redis_sg" {
  name        = "growcircle-${var.environment}-redis-sg"
  description = "Allows Redis traffic from App subnets"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [
      aws_subnet.private_1.cidr_block,
      aws_subnet.private_2.cidr_block,
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "growcircle-${var.environment}-redis-sg"
  }
}

# ElastiCache Replication Group (Redis 7)
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "growcircle-${var.environment}-redis"
  description          = "Redis cluster for token-bucket rate limits, session cache and Celery"

  node_type            = var.redis_node_type
  port                 = 6379
  parameter_group_name = "default.redis7"

  subnet_group_name  = aws_elasticache_subnet_group.redis_subnet_group.name
  security_group_ids = [aws_security_group.redis_sg.id]

  automatic_failover_enabled = var.environment == "prod" ? true : false
  num_cache_clusters         = var.environment == "prod" ? 2 : 1

  at_rest_encryption_enabled = true
  transit_encryption_enabled = false

  tags = {
    Name = "growcircle-${var.environment}-redis"
  }
}
