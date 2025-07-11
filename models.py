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
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='contents', lazy=True)
    topic = db.Column(db.String(200), nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    blog_style = db.Column(db.String(50), nullable=True)
    tone = db.Column(db.String(50), nullable=False)
    length_option = db.Column(db.String(20), nullable=False)
    seo_keywords = db.Column(db.Text)
    target_audience = db.Column(db.String(255), nullable=True)  
    email_type = db.Column(db.String(50), nullable=True)       
    key_points = db.Column(db.Text, nullable=True)             
    landing_page_url = db.Column(db.String(2048), nullable=True) 
    email_subject = db.Column(db.String(255), nullable=True)  # 이메일 제목 필드 추가
    generated_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Content {self.topic}>'