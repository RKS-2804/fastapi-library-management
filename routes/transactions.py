import logging
from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from datetime import datetime
from starlette.responses import RedirectResponse
from database import get_db
from models import BookTransaction, User, Book
from fastapi.templating import Jinja2Templates

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI Router and Jinja2 Templates
router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def get_all_users(db: AsyncSession):
    """
    Fetch all users from the database.

    Args:
        db (AsyncSession): Database session dependency.

    Returns:
        list: List of User objects.
    """
    result = await db.execute(select(User))
    return result.scalars().all()


async def get_all_books(db: AsyncSession):
    """
    Fetch all books from the database.

    Args:
        db (AsyncSession): Database session dependency.

    Returns:
        list: List of Book objects.
    """
    result = await db.execute(select(Book))
    return result.scalars().all()


@router.get("/")
async def list_transactions(
    request: Request, 
    db: AsyncSession = Depends(get_db), 
    page: int = 1, 
    per_page: int = 5
):
    """
    List all transactions with pagination.

    Args:
        request (Request): FastAPI request object.
        db (AsyncSession): Database session dependency.
        page (int, optional): Page number. Defaults to 1.
        per_page (int, optional): Transactions per page. Defaults to 5.

    Returns:
        TemplateResponse: Renders `transactions.html` with transaction data.
    """
    try:
        total_transactions = await db.execute(select(BookTransaction))
        total_transactions_count = len(total_transactions.scalars().all())

        result = await db.execute(
            select(BookTransaction)
            .options(selectinload(BookTransaction.book), selectinload(BookTransaction.user))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        transactions = result.scalars().all()

        transactions_list = [
            {
                "id": transaction.id,
                "book_title": transaction.book.title if transaction.book else "Unknown",
                "user_name": transaction.user.username if transaction.user else "Unknown",
                "checkout_date": transaction.checkout_date,
                "status": transaction.status,
            }
            for transaction in transactions
        ]

        users = await get_all_users(db)
        books = await get_all_books(db)

        logger.info(f"Fetched {len(transactions)} transactions for page {page}")

        return templates.TemplateResponse("transactions.html", {
            "request": request,
            "transactions": transactions_list,
            "users": users,
            "books": books,
            "page": page,
            "total_pages": (total_transactions_count // per_page) + (1 if total_transactions_count % per_page > 0 else 0)
        })

    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return {"error": str(e)}


@router.post("/add_transaction")
async def add_transaction(
    request: Request,
    user_id: int = Form(...),
    status: str = Form(...),
    book_id: int = Form(None),
    title: str = Form(None),
    author: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new book transaction (Check-out or Check-in).

    Args:
        request (Request): FastAPI request object.
        user_id (int): ID of the user performing the transaction.
        status (str): Status of the transaction (checked_out / checked_in).
        book_id (int, optional): ID of the book being checked out. Required for check-out.
        title (str, optional): Title of a new book for check-in.
        author (str, optional): Author of a new book for check-in.
        db (AsyncSession): Database session dependency.

    Returns:
        RedirectResponse | dict: Redirects to `/transactions` or returns an error message.
    """
    try:
        if status == "checked_out":
            # Prevent duplicate checkouts
            existing_transaction = await db.execute(
                select(BookTransaction).where(
                    BookTransaction.user_id == user_id,
                    BookTransaction.book_id == book_id,
                    BookTransaction.status == "checked_out"
                )
            )
            existing_transaction = existing_transaction.scalars().first()

            if existing_transaction:
                logger.warning(f"User {user_id} attempted to check out book {book_id} which is already checked out.")
                return {"detail": "Book is already checked out by this user!"}

            # Fetch user and book
            user = await db.execute(select(User).where(User.id == user_id))
            user = user.scalars().first()

            book = await db.execute(select(Book).where(Book.id == book_id))
            book = book.scalars().first()

            if not user or not book:
                logger.error(f"User ID {user_id} or Book ID {book_id} not found")
                return {"detail": "User or Book not found"}

            new_transaction = BookTransaction(
                user_id=user_id,
                book_id=book_id,
                status=status,
                checkout_date=datetime.utcnow()
            )
            db.add(new_transaction)
            await db.commit()
            await db.refresh(new_transaction)

            logger.info(f"User {user_id} checked out book {book_id}")

        elif status == "checked_in":
            # Create a new book entry if it doesn't exist
            new_book = Book(title=title, author=author)
            db.add(new_book)
            await db.commit()
            await db.refresh(new_book)

            new_transaction = BookTransaction(
                user_id=user_id,
                book_id=new_book.id,
                status=status,
                checkout_date=datetime.utcnow()
            )
            db.add(new_transaction)
            await db.commit()
            await db.refresh(new_transaction)

            logger.info(f"User {user_id} checked in new book '{title}' by {author}")

        return RedirectResponse(url="/transactions", status_code=303)

    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding transaction: {e}")
        return {"error": str(e)}
