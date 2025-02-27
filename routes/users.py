import logging
from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import get_db
from models import User
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from sqlalchemy.sql import and_

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI Router
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_users(request: Request, db: AsyncSession = Depends(get_db), page: int = 1, per_page: int = 5):
    """
    List users with pagination.
    
    Args:
        request (Request): FastAPI request object.
        db (AsyncSession): Database session dependency.
        page (int, optional): Current page number. Defaults to 1.
        per_page (int, optional): Users per page. Defaults to 5.

    Returns:
        TemplateResponse: Renders `users.html` with paginated user data.
    """
    try:
        offset = (page - 1) * per_page

        # Fetch total user count
        result = await db.execute(select(User))
        total_users = len(result.scalars().all())

        # Fetch paginated users sorted by ID
        result = await db.execute(select(User).order_by(User.id).offset(offset).limit(per_page))
        users = result.scalars().all()

        total_pages = (total_users // per_page) + (1 if total_users % per_page > 0 else 0)

        logger.info(f"Fetched {len(users)} users for page {page}")

        return templates.TemplateResponse("users.html", {
            "request": request,
            "users": users,
            "page": page,
            "total_pages": total_pages
        })
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return {"error": str(e)}


@router.post("/add")
async def add_user(username: str = Form(...), db: AsyncSession = Depends(get_db)):
    """
    Add a new user while preventing duplicate usernames.

    Args:
        username (str): The username for the new user.
        db (AsyncSession): Database session dependency.

    Returns:
        RedirectResponse | dict: Redirects to `/users` or returns an error message.
    """
    try:
        # Check if the username already exists
        existing_user = await db.execute(select(User).where(User.username == username))
        if existing_user.scalars().first():
            logger.warning(f"Attempted to add duplicate username: {username}")
            return {"error": f"Username '{username}' already exists!"}

        # Add new user
        new_user = User(username=username)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"User '{username}' added successfully")
        return RedirectResponse(url="/users", status_code=303)

    except IntegrityError:
        await db.rollback()
        logger.error(f"IntegrityError: Username '{username}' is already taken.")
        return {"error": f"Username '{username}' is already taken. Choose a different one."}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding user: {e}")
        return {"error": str(e)}


@router.get("/delete/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a user by their ID.

    Args:
        user_id (int): The ID of the user to be deleted.
        db (AsyncSession): Database session dependency.

    Returns:
        RedirectResponse | dict: Redirects to `/users` or returns an error message.
    """
    try:
        # Find the user by ID
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.warning(f"Delete attempt for non-existent user ID: {user_id}")
            return {"error": "User not found"}

        await db.delete(user)
        await db.commit()
        logger.info(f"Deleted user ID: {user_id}")

        return RedirectResponse(url="/users", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return {"error": str(e)}


@router.get("/edit/{user_id}")
async def edit_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Fetch user details for editing.

    Args:
        user_id (int): The ID of the user to be edited.
        request (Request): FastAPI request object.
        db (AsyncSession): Database session dependency.

    Returns:
        TemplateResponse | dict: Renders `edit_user.html` or returns an error message.
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.warning(f"Edit attempt for non-existent user ID: {user_id}")
            return {"error": "User not found"}

        return templates.TemplateResponse("edit_user.html", {"request": request, "user": user})
    except Exception as e:
        logger.error(f"Error fetching user for edit {user_id}: {e}")
        return {"error": str(e)}


@router.post("/update/{user_id}")
async def update_user(
    user_id: int, 
    username: str = Form(...), 
    db: AsyncSession = Depends(get_db)
):
    """
    Update user details.

    Args:
        user_id (int): The ID of the user to be updated.
        username (str): The new username.
        db (AsyncSession): Database session dependency.

    Returns:
        RedirectResponse | dict: Redirects to `/users` or returns an error message.
    """
    try:
        logger.info(f"Received update request for user {user_id} with new username: {username}")

        # Check if username is already taken
        result = await db.execute(select(User).where(and_(User.username == username, User.id != user_id)))
        existing_user = result.scalars().first()

        if existing_user:
            logger.warning(f"Username '{username}' is already in use. Update rejected.")
            return {"error": f"Username '{username}' is already in use."}

        # Fetch the user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.warning(f"Update attempt for non-existent user ID: {user_id}")
            return {"error": "User not found"}

        # Update user details
        user.username = username
        await db.commit()
        await db.refresh(user)

        logger.info(f"User {user_id} updated successfully")
        return RedirectResponse(url="/users", status_code=303)

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user {user_id}: {e}")
        return {"error": str(e)}
