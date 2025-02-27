from pydantic import BaseModel
from datetime import datetime

class BookBase(BaseModel):
    title: str
    author: str

class BookCreate(BookBase):
    pass

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    pass

class CheckoutBase(BaseModel):
    user_id: int
    book_id: int
    checkout_date: datetime = datetime.now()
