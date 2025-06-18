# AWS ECR(Elastic Container Registry) 리포지토리 생성
# 이 코드는 ai-content-marketing-tool 프로젝트를 위한 ECR 리포지토리를 생성합니다.

resource "aws_ecr_repository" "ai_content_marketing_tool_repo" {
  name                 = "ai-content-marketing-tool-repo" # 생성할 ECR 리포지토리 이름
  image_tag_mutability = "MUTABLE"                  # 이미지 태그 변경 가능 여부 (MUTABLE 또는 IMMUTABLE)

  # 이미지 스캔 설정 (푸시 시 이미지 취약점 스캔 활성화)
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "ai-content-marketing-tool-repo"
    Environment = "development" # 또는 development, staging 등 환경에 맞게
    Project     = "ai-content-marketing-tool"
  }
}

# ECR 리포지토리 URL을 출력합니다.
# 이 URL은 Docker 이미지를 푸시하거나 EC2에서 이미지를 가져올 때 사용됩니다.
output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.ai_content_marketing_tool_repo.repository_url
}
