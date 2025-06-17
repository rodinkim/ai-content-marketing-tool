# --- EC2 인스턴스를 위한 보안 그룹(Security Group) ---
resource "aws_security_group" "web_sg" {
  name        = "ai-content-marketing-tool-web-sg"
  description = "Allow HTTP & SSH traffic"
  vpc_id      = aws_vpc.main.id

  # SSH 접속 허용 (운영 환경에서는 IP 제한 권장)
  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Flask 앱용 HTTP(5000) 포트 허용
  ingress {
    description = "HTTP for Flask app"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 모든 아웃바운드 트래픽 허용
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ai-content-marketing-tool-web-sg"
  }
}

# --- 최신 Amazon Linux 2023 AMI 조회 ---
data "aws_ami" "amazon_linux" {
  most_recent = true

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["amazon"]
}

# --- EC2 인스턴스 생성 ---
resource "aws_instance" "app_server" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  key_name               = var.ec2_key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web_sg.id]

  # S3 접근 권한을 위한 IAM 인스턴스 프로파일 연결
  iam_instance_profile   = aws_iam_instance_profile.ec2_s3_profile.name

  tags = {
    Name = "ai-content-marketing-tool-server"
  }
}

# --- 변수 선언 (키 페어 이름 입력용) ---
variable "ec2_key_name" {
  description = "EC2 instance key pair name"
  type        = string
  # 예: default = "my-key"
}

# --- EC2 인스턴스의 Public IP 출력 ---
output "instance_public_ip" {
  description = "The public IP address of the EC2 instance"
  value       = aws_instance.app_server.public_ip
}