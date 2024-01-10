from pydantic import BaseModel


class MessageScheme(BaseModel):
    message: str
    receiver: int
