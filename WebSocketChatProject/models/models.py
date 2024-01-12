from sqlalchemy import Column, Integer, ForeignKey, String, MetaData
from database import Base

metadata = MetaData()


class UserData(Base):
    __tablename__ = 'userdata'
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String)
    password = Column(String)


class Message(Base):
    __tablename__ = 'message'
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey("userdata.id"))
    receiver_id = Column(Integer, ForeignKey("userdata.id"))
    message = Column(String)


class Room(Base):
    __tablename__ = 'room'
    metadata = metadata
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String)
    sender_id = Column(ForeignKey('userdata.id'))
    receiver_id = Column(ForeignKey('userdata.id'))
