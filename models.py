from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    author = Column(String(255), nullable=False)
    transactions = relationship("BookTransaction", back_populates="book")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    transactions = relationship("BookTransaction", back_populates="user")

class BookTransaction(Base):
    __tablename__ = "book_transactions"
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    checkout_date = Column(DateTime, default=func.now())  
    status = Column(String(20), nullable=False) 

    user = relationship("User", back_populates="transactions")
    book = relationship("Book", back_populates="transactions")
