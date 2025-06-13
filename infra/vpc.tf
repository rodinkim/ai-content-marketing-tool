# --- 1. VPC 리소스 생성 ---
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "ai-content-marketing-tool-vpc",
    Owner = "ohsung.kim@bespinglobal.com"
  }
}

# --- 2. 가용 영역(AZ) 정보 가져오기 ---
data "aws_availability_zones" "available" {
  state = "available"
}

# --- 3. Public Subnet 1개 생성 ---
resource "aws_subnet" "public" {
  # count 제거, 단일 리소스 생성
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  # 사용 가능한 AZ 중 첫 번째 AZ에 배치
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "ai-content-marketing-tool-public-subnet"
  }
}

# --- 4. Private Subnet 1개 생성 ---
resource "aws_subnet" "private" {
  # count 제거, 단일 리소스 생성
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.101.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "ai-content-marketing-tool-private-subnet"
  }
}

# --- 5. 인터넷 게이트웨이(IGW) 생성 및 VPC에 연결 ---
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "ai-content-marketing-tool-igw"
  }
}

# --- 6. Public 라우팅 테이블 생성 ---
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "ai-content-marketing-tool-public-rt"
  }
}

# Public Subnet을 Public 라우팅 테이블과 연결
resource "aws_route_table_association" "public_assoc" {
  # count 제거, 단일 리소스 연결
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}

# --- 7. NAT 게이트웨이를 위한 EIP(탄력적 IP) 생성 ---
resource "aws_eip" "nat" {
  domain = "vpc"
  
  tags = {
    Name = "ai-content-marketing-tool-nat-eip"
  }
}

# --- 8. NAT 게이트웨이 생성 (Public Subnet에 배치) ---
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id

  tags = {
    Name = "ai-content-marketing-tool-nat-gw"
  }

  depends_on = [aws_internet_gateway.igw]
}

# --- 9. Private 라우팅 테이블 생성 ---
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }

  tags = {
    Name = "ai-content-marketing-tool-private-rt"
  }
}

# Private Subnet을 Private 라우팅 테이블과 연결
resource "aws_route_table_association" "private_assoc" {
  # count 제거, 단일 리소스 연결
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private_rt.id
}