import os
import secrets
from datetime import datetime, timedelta

import jwt
import requests

from .schemas import UserInfo, User, UserInDB, UserLogin, UserRead, ForgetPasswordRequest
from database import get_async_session

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from fastapi import Depends, APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from passlib.context import CryptContext
from starlette.background import BackgroundTasks
from starlette.responses import JSONResponse
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig

from models.models import UserData
from .utils import verify_token, generate_token, create_reset_password_token
from config import EnvObjectsForEmail, Settings

load_dotenv()
register_router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_SECRET_KEY = os.getenv('GOOGLE_SECRET_KEY')
GOOGLE_REDIRECT_URL = os.getenv('GOOGLE_REDIRECT_URL')

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

obj = EnvObjectsForEmail

mail_config = ConnectionConfig(
    MAIL_USERNAME=obj.MAIL_USERNAME,
    MAIL_PASSWORD=obj.MAIL_PASSWORD,
    MAIL_FROM=obj.MAIL_FROM,
    MAIL_PORT=obj.MAIL_PORT,
    MAIL_SERVER=obj.MAIL_SERVER,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

settings_email = EnvObjectsForEmail()
settings = Settings()


@register_router.get("/login/google")
async def login_google():
    return {
        "url": f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URL}&scope=openid%20profile%20email&access_type=offline"
    }


@register_router.get("/auth/google")
async def auth_google(code: str, session: AsyncSession = Depends(get_async_session)):
    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_SECRET_KEY,
        "redirect_uri": GOOGLE_REDIRECT_URL,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)
    access_token = response.json().get("access_token")
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo",
                             headers={"Authorization": f"Bearer {access_token}"})
    user_info_data = user_info.json()
    user_data = {
        'first_name': user_info_data['given_name'],
        'last_name': user_info_data['family_name'],
        'username': user_info_data['email'],
        'password': pwd_context.hash(user_info_data['email'])
    }
    query_exist = select(UserData).where(UserData.username == user_info_data['email'])
    user_exist_data = await session.execute(query_exist)
    try:
        result = user_exist_data.scalars().one()
    except NoResultFound:
        query = insert(UserData).values(**user_data)
        await session.execute(query)
        await session.commit()
    query = select(UserData).where(UserData.username == user_data['username'])
    userdata = await session.execute(query)
    user_data = userdata.one()
    token = generate_token(user_data[0].id)
    return token


@register_router.get("/token")
async def get_token(token: str = Depends(oauth2_scheme)):
    return jwt.decode(token, GOOGLE_SECRET_KEY, algorithms=["HS256"])


@register_router.post('/register')
async def register(user: User, session: AsyncSession = Depends(get_async_session)):
    if user.password1 == user.password2:
        if not select(UserData).where(UserData.username == user.username).exists:
            return {'success': False, 'message': 'Username already exists!'}
        password = pwd_context.hash(user.password1)
        user_in_db = UserInDB(**dict(user), password=password, joined_at=datetime.utcnow())
        query = insert(UserData).values(**dict(user_in_db))
        await session.execute(query)
        await session.commit()
        user_info = UserInfo(**dict(user_in_db))
        return dict(user_info)


@register_router.post('/login')
async def login(user: UserLogin, session: AsyncSession = Depends(get_async_session)):
    query = select(UserData).where(UserData.username == user.username)
    userdata = await session.execute(query)
    user_data = userdata.one()
    print(user_data[0].id)
    if pwd_context.verify(user.password, user_data[0].password):
        token = generate_token(user_data[0].id)
        return token
    else:
        return {'success': False, 'message': 'Username or password is not correct!'}


@register_router.get('/user-info', response_model=UserRead)
async def user_info(token: dict = Depends(verify_token), session: AsyncSession = Depends(get_async_session)):
    if token is None:
        raise HTTPException(status_code=401, detail='Token not provided!')

    user_id = token.get('user_id')

    query = select(UserData).where(UserData.id == user_id)
    user = await session.execute(query)
    try:
        result = user.scalars().one()
        return result
    except NoResultFound:
        raise HTTPException(status_code=404, detail='User not found!')


@register_router.post('/refresh-token')
async def refresh_auth_token(
        refresh_token: str
):
    try:
        secret_key = os.environ.get('SECRET')
        payload = jwt.decode(refresh_token, secret_key, algorithms=['HS256'])
        jti_access = str(secrets.token_urlsafe(32))
        data_access_token = {
            'token_type': 'access',
            'exp': datetime.utcnow() + timedelta(minutes=30),
            'user_id': payload.get('user_id'),
            'jti': jti_access
        }
        access_token = jwt.encode(data_access_token, secret_key, 'HS256')
        return {
            'access_token': access_token
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@register_router.post("/forget-password")
async def forget_password(
        background_tasks: BackgroundTasks,
        fpr: ForgetPasswordRequest,
        session: AsyncSession = Depends(get_async_session)
):
    try:
        query = select(UserData).where(UserData.email == fpr.email)
        result = await session.execute(query)
        email_data = result.scalars().one()
        if email_data is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Invalid Email address")
        secret_token = create_reset_password_token(fpr.email)
        forget_url_link = f"{settings.APP_HOST}/{settings.FORGET_PASSWORD_URL}/{secret_token}"

        body = (f'Company: {settings_email.MAIL_FROM}\n\n'
                
                f'Link expiration minutes: {settings.FORGET_PASSWORD_LINK_EXPIRE_MINUTES}\n\n'
                
                f'link: {forget_url_link}\n\n')

        message = MessageSchema(
            subject="Password Reset Instructions",
            recipients=[fpr.email],
            body=body,
            subtype=MessageType.html
        )

        fm = FastMail(mail_config)
        background_tasks.add_task(fm.send_message, message)

        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"message": "Email has been sent", "success": True,
                                     "status_code": status.HTTP_200_OK})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Something Unexpected, Server Error")
