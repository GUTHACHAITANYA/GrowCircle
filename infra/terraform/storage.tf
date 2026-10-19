# S3 Bucket for Produce Listing Photos & Audio Notes
resource "aws_s3_bucket" "media_bucket" {
  bucket = "growcircle-${var.environment}-media-mumbai"

  tags = {
    Name = "growcircle-${var.environment}-media"
  }
}

# Block Public Access by default (all access via CloudFront or presigned URLs)
resource "aws_s3_bucket_public_access_block" "media_pab" {
  bucket = aws_s3_bucket.media_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-Side Encryption (KMS)
resource "aws_s3_bucket_server_side_encryption_configuration" "media_enc" {
  bucket = aws_s3_bucket.media_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle Rule: Archive transient voice notes and scratch audio after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "media_lifecycle" {
  bucket = aws_s3_bucket.media_bucket.id

  rule {
    id     = "transient-audio-cleanup"
    status = "Enabled"

    filter {
      prefix = "temp_audio/"
    }

    expiration {
      days = 30
    }
  }
}
