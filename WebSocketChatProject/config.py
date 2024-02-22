import os
import secrets
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
SECRET = os.environ.get('SECRET')


class EnvObjectsForEmail:
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_FROM = os.getenv('MAIL_FROM')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_SERVER = os.getenv('MAIL_SERVER')


class Settings(BaseSettings):
    # BASEDIR = os.path.abspath(os.path.dirname(__file__))
    # LOG_PATH = os.path.join(BASEDIR, 'logs')
    # BACKEND_CORS_ORIGINS: List = ['*']

    # 默认管理员账号密码等信息
    # ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    # ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '123456')
    # ADMIN_NICKNAME = os.getenv('ADMIN_NICKNAME', 'admin')
    # ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '1104440778@qq.com')

    # 数据库账号密码
    DB_HOST: str = os.getenv('DB_HOST')
    DB_PORT: str = os.getenv('DB_PORT')
    DB_USER: str = os.getenv('DB_USER')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD')
    DB_NAME: str = os.getenv('DB_NAME')

    # DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}'
    # SQLALCHEMY_DATABASE_URI: str = f'mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

    # Elasticsearch
    # ELASTIC_HOST = os.getenv('ELASTIC_HOST', '127.0.0.1')
    # ELASTIC_PORT = os.getenv('ELASTIC_PORT', 9200)

    # 12 hours
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    FORGET_PASSWORD_LINK_EXPIRE_MINUTES: int = 10
    SECRET_KEY: str = os.getenv('SECRET')

    APP_HOST: str = 'http://localhost:8000'
    FORGET_PASSWORD_URL: str = 'reset-password'
