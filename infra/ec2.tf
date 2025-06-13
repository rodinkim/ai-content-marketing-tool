# --- 10. EC2 인스턴스를 위한 보안 그룹(Security Group) 생성 ---
# 보안 그룹은 EC2 인스턴스의 가상 방화벽 역할을 합니다.
resource "aws_security_group" "web_sg" {
  name        = "ai-content-marketing-tool-web-sg"
  description = "Allow HTTP & SSH traffic"
  vpc_id      = aws_vpc.main.id

  # Ingress (인바운드) 규칙
  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # 경고: 실제 운영 환경에서는 내 IP 주소로 제한하는 것이 안전합니다.
  }

  ingress {
    description = "HTTP from anywhere for Flask app"
    from_port   = 5000 # Flask 기본 포트인 5000번을 허용
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress (아웃바운드) 규칙
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # 모든 프로토콜
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ai-content-marketing-tool-web-sg"
  }
}

# --- 11. EC2 인스턴스에 사용할 최신 Amazon Linux 2023 AMI 조회 ---
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

# --- 12. EC2 인스턴스 생성 ---
resource "aws_instance" "app_server" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  
  # 1단계에서 생성하거나 준비한 키 페어의 이름을 정확히 입력합니다.
  key_name      = var.ec2_key_name

  # Public Subnet에 인스턴스 생성
  subnet_id     = aws_subnet.public.id

  # 위에서 생성한 보안 그룹과 연결
  vpc_security_group_ids = [aws_security_group.web_sg.id]

  tags = {
    Name = "ai-content-marketing-tool-server"
  }
}

# --- 변수 선언 (키 페어 이름을 받기 위함) ---
variable "ec2_key_name" {
  description = "EC2 instance key pair name"
  type        = string
  # default 값을 설정하거나, apply 시 직접 입력할 수 있습니다.
  # 예: default = "my-key"
}

# --- 생성된 인스턴스의 Public IP 주소를 출력 ---
output "instance_public_ip" {
  description = "The public IP address of the EC2 instance"
  value       = aws_instance.app_server.public_ip
}