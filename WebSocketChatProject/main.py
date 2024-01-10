import base64
from typing import List

from fastapi import FastAPI, WebSocket, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select

from models.models import Message
from schemes import MessageScheme
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

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, sender: str, message:str, websocket: WebSocket):
        for connection in self.active_connections:
            if connection == websocket:
                continue
            await connection.send_text(message)

    async def send_to_all(self, data: str):
        for connection in self.active_connections:
            await connection.send_text(data)


manager = WebSocketManager()
connected_clients = {}


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_to_all(data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@router.post('/sendfile')
async def send_file(file_data: bytes):
    base64_data = base64.b64encode(file_data).decode('utf-8')
    await manager.broadcast(base64_data)
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


app.include_router(register_router)
app.include_router(router)
