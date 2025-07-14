# ai-content-marketing-tool/models.py
from datetime import datetime
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Content(db.Model):
    __tablename__ = 'contents'

    # ----------------------------------------------------------------------
    # 기본 메타데이터 필드: 모든 콘텐츠 레코드에 공통으로 포함되는 필수 정보
    # ----------------------------------------------------------------------
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='contents', lazy=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # ----------------------------------------------------------------------
    # 공통 마케팅 콘텐츠 파라미터: 모든 콘텐츠 유형(블로그, 이메일, SNS)에 
    # 공통으로 적용될 수 있는 마케팅 관련 설정
    # ----------------------------------------------------------------------
    topic = db.Column(db.String(200), nullable=False) # 콘텐츠의 핵심 주제
    industry = db.Column(db.String(100), nullable=False) # 콘텐츠가 속한 업종
    content_type = db.Column(db.String(50), nullable=False) # 콘텐츠 종류: 'blog', 'email', 'sns'
    target_audience = db.Column(db.String(255), nullable=True) # 타겟 고객 (예: 20-30대 개발자)

    ad_purpose = db.Column(db.String(100), nullable=True) # 광고 목적 (제품 판매, 앱 설치, 브랜드 인지도 등)
    product_category = db.Column(db.String(100), nullable=True) # 제품 카테고리 (화장품, SaaS, 패션 등)
    brand_style_tone = db.Column(db.String(100), nullable=True) # 브랜드 스타일/톤 (고급, 감성, 트렌디, 미니멀 등)
    key_points = db.Column(db.Text, nullable=True) # 콘텐츠에 강조하고 싶은 핵심 내용/메시지 (범용적 사용)
    landing_page_url = db.Column(db.String(2048), nullable=True) # CTA(Call To Action)가 연결될 랜딩 페이지 URL

    # ----------------------------------------------------------------------
    # 텍스트 콘텐츠 전용 설정: 텍스트 기반 콘텐츠(블로그, 이메일)에 주로 적용되는 설정
    # (SNS 콘텐츠 생성 시에는 해당 필드가 사용되지 않을 수 있음)
    # ----------------------------------------------------------------------
    tone = db.Column(db.String(50), nullable=True) # 콘텐츠의 톤앤매너 (전문적, 친근함, 유머러스 등)
    length_option = db.Column(db.String(20), nullable=True) # 콘텐츠 분량 옵션 (짧게, 중간, 길게)
    seo_keywords = db.Column(db.Text, nullable=True) # SEO 키워드 (쉼표로 구분)
    generated_text = db.Column(db.Text, nullable=True) # AI가 생성한 텍스트 본문 (SNS 이미지의 경우 NULL 가능)

    # ----------------------------------------------------------------------
    # 블로그 전용 필드: 블로그 게시글 유형에만 해당하는 고유 설정
    # ----------------------------------------------------------------------
    blog_style = db.Column(db.String(50), nullable=True) # 블로그 스타일 (예: 추천 리스트 포스팅, 리뷰/후기 포스팅)

    # ----------------------------------------------------------------------
    # 이메일 전용 필드: 이메일 유형에만 해당하는 고유 설정
    # ----------------------------------------------------------------------
    email_subject = db.Column(db.String(255), nullable=True) # 이메일 제목
    email_type = db.Column(db.String(50), nullable=True) # 이메일 유형 (예: 뉴스레터, 프로모션)
    
    # ----------------------------------------------------------------------
    # SNS 이미지/비주얼 콘텐츠 전용 필드: SNS 게시물 중 이미지/비주얼 콘텐츠 생성에 필요한 설정
    # ----------------------------------------------------------------------
    cut_count = db.Column(db.Integer, nullable=True) # 생성할 이미지 컷 수 (예: 1컷, 3컷)
    aspect_ratio_sns = db.Column(db.String(20), nullable=True) # SNS 이미지 종횡비 (예: 1:1, 9:16)
    other_requirements = db.Column(db.Text, nullable=True) # 기타 이미지 생성 요구사항 (예: 인물 제외, 특정 색상, 텍스트 위치 등)
    generated_image_url = db.Column(db.String(2048), nullable=True) # AI가 생성한 이미지의 URL

    def __repr__(self):
        return f'<Content {self.topic}>'