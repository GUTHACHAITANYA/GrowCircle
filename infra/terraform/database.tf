# KMS Key for Database Encryption at Rest
resource "aws_kms_key" "db_kms" {
  description             = "KMS Key for GrowCircle RDS PostgreSQL encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "growcircle-${var.environment}-db-kms"
  }
}

# Database Security Group
resource "aws_security_group" "db_sg" {
  name        = "growcircle-${var.environment}-db-sg"
  description = "Allows inbound PostgreSQL traffic from private app subnets only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "PostgreSQL from Private Subnets"
    from_port   = 5432
    to_port     = 5432
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
    Name = "growcircle-${var.environment}-db-sg"
  }
}

# Random Master Password generated securely
resource "random_password" "db_password" {
  length  = 24
  special = false
}

# AWS Secrets Manager Secret for DB Credentials
resource "aws_secretsmanager_secret" "db_secret" {
  name                    = "growcircle/${var.environment}/database"
  kms_key_id              = aws_kms_key.db_kms.arn
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_secret_val" {
  secret_id = aws_secretsmanager_secret.db_secret.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    engine   = "postgres"
    port     = 5432
    dbname   = var.db_name
  })
}

# RDS PostgreSQL Instance with PostGIS support
resource "aws_db_instance" "postgres" {
  identifier     = "growcircle-${var.environment}-pg"
  engine         = "postgres"
  engine_version = "16.1"

  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.db_sg.id]

  # Multi-AZ for High Availability
  multi_az = var.environment == "prod" ? true : false

  # Storage Encryption with KMS
  storage_encrypted = true
  kms_key_id        = aws_kms_key.db_kms.arn

  # Automated Backups & Deletion Protection
  backup_retention_period   = 30
  backup_window             = "19:00-20:00" # 12:30 AM - 01:30 AM IST
  maintenance_window        = "sun:20:30-sun:21:30"
  copy_tags_to_snapshot     = true
  deletion_protection       = var.environment == "prod" ? true : false
  skip_final_snapshot       = var.environment == "prod" ? false : true
  final_snapshot_identifier = "growcircle-${var.environment}-pg-final-snapshot"

  auto_minor_version_upgrade = true

  tags = {
    Name = "growcircle-${var.environment}-postgres"
  }
}
