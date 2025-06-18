# RDS용 DB Subnet Group (퍼블릭 또는 프라이빗 서브넷 ID 사용)
resource "aws_db_subnet_group" "default" {
  name       = "main"
  subnet_ids = [
  aws_subnet.public.id, # ap-northeast-2a
  aws_subnet.public_c.id  # ap-northeast-2c
  ]

  tags = {
    Name = "Main DB subnet group"
  }
}

# PostgreSQL RDS 인스턴스 (프리티어)
resource "aws_db_instance" "postgres" {
  identifier              = "ai-content-marketing-tool-db"
  engine                  = "postgres"
  engine_version          = "15.10" # AWS 콘솔에서 지원하는 버전 문자열 사용
  instance_class          = "db.t3.micro" # 프리티어: db.t3.micro 또는 db.t2.micro
  allocated_storage       = 20            # 프리티어 최대 20GB
  db_name                 = "vectordb"
  username                = "postgres"
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.default.name
  vpc_security_group_ids  = [aws_security_group.db_sg.id]
  skip_final_snapshot     = true
  publicly_accessible     = true # 운영 환경에서는 false 권장

  tags = {
    Name = "ai-content-marketing-tool-db"
  }
}

# MySQL RDS 인스턴스 (프리티어)
resource "aws_db_instance" "mysql" {
  identifier              = "ai-content-marketing-tool-mysql"
  engine                  = "mysql"
  engine_version          = "8.0.41" # AWS 콘솔에서 지원하는 버전 문자열 사용
  instance_class          = "db.t3.micro" # 프리티어 지원
  allocated_storage       = 20
  db_name                 = "aicontentdb"
  username                = "admin"
  password                = var.mysql_password
  db_subnet_group_name    = aws_db_subnet_group.default.name
  vpc_security_group_ids  = [aws_security_group.db_sg.id]
  skip_final_snapshot     = true
  publicly_accessible     = true

  tags = {
    Name = "ai-content-marketing-tool-mysql"
  }
}

# DB용 보안 그룹 (운영 환경에서는 인바운드 제한 권장)
resource "aws_security_group" "db_sg" {
  name        = "ai-content-marketing-tool-db-sg"
  description = "Allow PostgreSQL/MySQL access"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # 운영 환경에서는 제한 권장
  }

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # 운영 환경에서는 제한 권장
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ai-content-marketing-tool-db-sg"
  }
}

# PostgreSQL 비밀번호 변수
variable "db_password" {
  description = "The password for the RDS PostgreSQL master user"
  type        = string
  sensitive   = true
}

# MySQL 비밀번호 변수
variable "mysql_password" {
  description = "The password for the RDS MySQL master user"
  type        = string
  sensitive   = true
}