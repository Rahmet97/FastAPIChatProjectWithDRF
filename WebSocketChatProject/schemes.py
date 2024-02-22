from pydantic import BaseModel


class MessageScheme(BaseModel):
    message: str
    receiver: int


class RoomScheme(BaseModel):
    id: int
    key: str
    sender_id: int
    receiver_id: int


class ReceiverScheme(BaseModel):
    receiver_id: int


class MessageShowScheme(BaseModel):
    id: int
    message: str
    sender_id: int
    receiver_id: int
