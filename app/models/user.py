from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    public_key_y = Column(Text, nullable=False)
    salt = Column(String(255), nullable=False)
    
    def __repr__(self):
        return f"<User(username={self.username})>"
