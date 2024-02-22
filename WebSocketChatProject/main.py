import base64
import hashlib
import json
from typing import List

from fastapi import FastAPI, WebSocket, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import NoResultFound
from starlette.websockets import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select

from auth.schemas import UserRead
from models.models import Message, UserData, Room
from schemes import MessageScheme, RoomScheme, ReceiverScheme, MessageShowScheme
from auth.utils import verify_token
from database import get_async_session
from auth.auth import register_router

app = FastAPI()
router = APIRouter()
app.mount("/static", StaticFiles(directory="Frontend/static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # can alter with time
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # self.encryption_key = Fernet(encryption_key.encode())

    async def connect(self, websocket: WebSocket, room: str):
        if len(self.active_connections) < 2:
            await websocket.accept()
            self.active_connections.append({"socket": websocket, "room": room})

    async def disconnect(self, websocket: WebSocket):
        for connection in self.active_connections:
            if connection['socket'] == websocket:
                self.active_connections.remove(connection)
                break

    async def broadcast(self, message:str, room: str):
        for connection in self.active_connections:
            if connection['room'] == room:
                await connection["socket"].send_text(message)

    async def send_to_all(self, data: str):
        for connection in self.active_connections:
            await connection['socket'].send_text(data)


manager = WebSocketManager()


@router.websocket('/ws/{room}')
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, room)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@router.post('/sendfile')
async def send_file(file_data: bytes, room: str):
    base64_data = base64.b64encode(file_data).decode('utf-8')
    await manager.broadcast(base64_data, room)
    return {'message': 'File sent'}


@router.post('/send-message')
async def send_message(
        message: MessageScheme,
        token: dict = Depends(verify_token),
        session: AsyncSession = Depends(get_async_session)
):
    if token is None:
        raise HTTPException(status_code=403, detail='Forbidden')

    try:
        sender_id = token.get('user_id')
        message_text = message.message
        receiver_id = message.receiver
        query = insert(Message).values(
            sender_id=sender_id,
            message=message_text,
            receiver_id=receiver_id
        )
        await session.execute(query)
        await session.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'{e}')
    return {'success': True}


@router.get('/users', response_model=List[UserRead])
async def user_list(
        token: dict = Depends(verify_token),
        session: AsyncSession = Depends(get_async_session)
):
    if token is None:
        raise HTTPException(status_code=403, detail='Forbidden')

    query = select(UserData).where(UserData.id != token.get('user_id'))
    user__data = await session.execute(query)
    user_data = user__data.scalars().all()
    return user_data


@router.post('/room', response_model=RoomScheme)
async def get_or_create_room(
        receiver: ReceiverScheme,
        token: dict = Depends(verify_token),
        session: AsyncSession = Depends(get_async_session)
):
    if token is None:
        raise HTTPException(status_code=403, detail='Forbidden')
    sender_id = token.get('user_id')
    room_data = {
        "sender_id": sender_id,
        "receiver_id": receiver.receiver_id
    }
    dump_data = json.dumps(room_data)
    hash_object = hashlib.sha256(dump_data.encode())
    unique_code = hash_object.hexdigest()
    query_get = select(Room).where(
        ((Room.sender_id == sender_id) & (Room.receiver_id == receiver.receiver_id)) |
        ((Room.sender_id == receiver.receiver_id) & (Room.receiver_id == sender_id))
    )
    room__data = await session.execute(query_get)
    try:
        result = room__data.scalars().one()
    except NoResultFound:
        query = insert(Room).values(
            key=unique_code,
            sender_id=sender_id,
            receiver_id=receiver.receiver_id
        )
        await session.execute(query)
        await session.commit()

        result_query = select(Room).where(Room.key==unique_code)
        result_data = await session.execute(result_query)
        result = result_data.scalars().one()
    print(result)
    return result


@router.get('/messages', response_model=List[MessageShowScheme])
async def get_chat_messages(
        receiver_id: int,
        token: dict = Depends(verify_token),
        session: AsyncSession = Depends(get_async_session)
):
    if token is None:
        raise HTTPException(status_code=403, detail='Forbidden')
    sender_id = token.get('user_id')
    query = select(Message).where(
        (Message.sender_id == sender_id) & (Message.receiver_id == receiver_id) |
        (Message.sender_id == receiver_id) & (Message.receiver_id == sender_id)
    )
    message_data = await session.execute(query)
    result = message_data.scalars().all()
    return result


@router.get('/rooms')
async def get_my_chats(
        token: dict = Depends(verify_token),
        session: AsyncSession = Depends(get_async_session)
):
    if token is None:
        raise HTTPException(status_code=403, detail='Forbidden')
    user_id = token.get('user_id')
    query = select(Room).where((Room.sender_id == user_id) | (Room.receiver_id == user_id))


app.include_router(register_router)
app.include_router(router)
