# IAM Role for App Runner execution
resource "aws_iam_role" "apprunner_role" {
  name = "growcircle-${var.environment}-apprunner-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "build.apprunner.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr" {
  role       = aws_iam_role.apprunner_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# App Runner Auto Scaling Configuration
resource "aws_apprunner_auto_scaling_configuration_version" "scaling" {
  auto_scaling_configuration_name = "growcircle-${var.environment}-scaling"
  max_concurrency                 = 100
  max_size                        = 10
  min_size                        = 2

  tags = {
    Name = "growcircle-${var.environment}-scaling"
  }
}

# App Runner Service (Serverless Container in Mumbai)
resource "aws_apprunner_service" "backend" {
  service_name = "growcircle-${var.environment}-backend"

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.scaling.arn

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_role.arn
    }

    image_repository {
      image_identifier      = var.container_image
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"

        runtime_environment_variables = {
          ENVIRONMENT        = var.environment
          DATABASE_URL       = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
          DATABASE_SYNC_URL  = "postgresql://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
          REDIS_URL          = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
          CELERY_BROKER_URL  = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/1"
          PROMETHEUS_ENABLED = "true"
        }
      }
    }
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name = "growcircle-${var.environment}-api"
  }
}
