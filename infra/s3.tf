resource "aws_s3_bucket" "knowledge_base_bucket" {
  bucket = "ai-content-marketing-tool-knowledge-base"
  force_destroy = true

  tags = {
    Name        = "ai-content-marketing-tool-knowledge-base"
    Environment = "development"
    Project     = "ai-content-marketing-tool"
  }
}

output "knowledge_base_bucket_name" {
  description = "The name of the S3 bucket for knowledge_base"
  value       = aws_s3_bucket.knowledge_base_bucket.bucket
}