# Terraform 및 프로바이더 버전 설정
# 코드의 안정적인 실행을 위해 권장됩니다.
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0" # AWS 프로바이더 버전을 5.x대로 고정
    }
  }
}

# 사용할 AWS 프로바이더 및 리전 설정
# 여기에 명시된 리전에 모든 리소스가 생성됩니다.
provider "aws" {
  region = "ap-northeast-2" # 서울 리전
}