import logging
from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Book
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI Router and Jinja2 Templates
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_books(request: Request, db: AsyncSession = Depends(get_db), page: int = 1, per_page: int = 5):
    """
    List all books with pagination.

    Args:
        request (Request): FastAPI request object.
        db (AsyncSession): Database session dependency.
        page (int, optional): Page number. Defaults to 1.
        per_page (int, optional): Books per page. Defaults to 5.

    Returns:
        TemplateResponse: Renders `books.html` with paginated book data.
    """
    try:
        # Calculate the offset based on page number
        offset = (page - 1) * per_page

        # Fetch total book count
        total_books_result = await db.execute(select(Book))
        total_books = len(total_books_result.scalars().all())

        # Fetch paginated books
        result = await db.execute(select(Book).offset(offset).limit(per_page))
        books = result.scalars().all()

        total_pages = (total_books // per_page) + (1 if total_books % per_page > 0 else 0)

        logger.info(f"Fetched {len(books)} books for page {page}")

        return templates.TemplateResponse("books.html", {
            "request": request,
            "books": books,
            "page": page,
            "total_pages": total_pages
        })

    except Exception as e:
        logger.error(f"Error fetching books: {e}")
        return {"error": str(e)}


@router.post("/add")
async def add_book(title: str = Form(...), author: str = Form(...), db: AsyncSession = Depends(get_db)):
    """
    Add a new book to the database.

    Args:
        title (str): The title of the book.
        author (str): The author of the book.
        db (AsyncSession): Database session dependency.

    Returns:
        RedirectResponse: Redirects to `/books` after adding the book.
    """
    try:
        new_book = Book(title=title, author=author)
        db.add(new_book)
        await db.commit()
        await db.refresh(new_book)

        logger.info(f"Added new book: '{title}' by {author}")

        return RedirectResponse(url="/books", status_code=303)

    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding book: {e}")
        return {"error": str(e)}


@router.get("/delete/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a book by its ID.

    Args:
        book_id (int): The ID of the book to be deleted.
        db (AsyncSession): Database session dependency.

    Returns:
        RedirectResponse | dict: Redirects to `/books` or returns an error message.
    """
    try:
        # Find the book by ID
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalars().first()

        if not book:
            logger.warning(f"Delete attempt for non-existent book ID: {book_id}")
            return {"error": "Book not found"}  # Return an error if book is not found

        await db.delete(book)
        await db.commit()
        
        logger.info(f"Deleted book: '{book.title}' (ID: {book_id})")

        return RedirectResponse(url="/books", status_code=303)

    except Exception as e:
        logger.error(f"Error deleting book {book_id}: {e}")
        return {"error": str(e)}


@router.get("/edit/{book_id}")
async def edit_book(book_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Fetch book details for editing.

    Args:
        book_id (int): The ID of the book to be edited.
        request (Request): FastAPI request object.
        db (AsyncSession): Database session dependency.

    Returns:
        TemplateResponse | dict: Renders `edit_book.html` or returns an error message.
    """
    try:
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalars().first()

        if not book:
            logger.warning(f"Edit attempt for non-existent book ID: {book_id}")
            return {"error": "Book not found"}  # Handle error if book does not exist

        return templates.TemplateResponse("edit_book.html", {"request": request, "book": book})

    except Exception as e:
        logger.error(f"Error fetching book for edit {book_id}: {e}")
        return {"error": str(e)}


@router.post("/update/{book_id}")
async def update_book(book_id: int, title: str = Form(...), author: str = Form(...), db: AsyncSession = Depends(get_db)):
    """
    Update book details.

    Args:
        book_id (int): The ID of the book to be updated.
        title (str): The new title of the book.
        author (str): The new author of the book.
        db (AsyncSession): Database session dependency.

    Returns:
        RedirectResponse | dict: Redirects to `/books` or returns an error message.
    """
    try:
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalars().first()

        if not book:
            logger.warning(f"Update attempt for non-existent book ID: {book_id}")
            return {"error": "Book not found"}  # Return an error if book is not found

        # Update the book details
        book.title = title
        book.author = author
        await db.commit()
        await db.refresh(book)

        logger.info(f"Updated book (ID: {book_id}) - New Title: '{title}', New Author: '{author}'")

        return RedirectResponse(url="/books", status_code=303)

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating book {book_id}: {e}")
        return {"error": str(e)}  
