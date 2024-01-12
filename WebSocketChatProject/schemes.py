from pydantic import BaseModel


class MessageScheme(BaseModel):
    message: str
    receiver: int


class RoomScheme(BaseModel):
    id: int
    key: str
    sender_id: int
    receiver_id: int
