import os
import secrets
from datetime import datetime, timedelta

import jwt

from .schemas import UserInfo, User, UserInDB, UserLogin
from database import get_async_session

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from fastapi import Depends, APIRouter, HTTPException
from dotenv import load_dotenv
from passlib.context import CryptContext

from models.models import UserData
from .utils import verify_token, generate_token

load_dotenv()
register_router = APIRouter()

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


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


@register_router.get('/user-info', response_model=UserInfo)
async def user_info(token: dict = Depends(verify_token), session: AsyncSession = Depends(get_async_session)):
    if token is None:
        raise HTTPException(status_code=401, detail='Token not provided!')

    user_id = token.get('user_id')

    query = select(UserData).where(UserData.id == user_id)
    user = await session.execute(query)
    try:
        result = user.one()
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
