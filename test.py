import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from models import User, Book
from main import app

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """
    Creates a single AsyncMock session that will be used
    both by the tests and by the FastAPI routes.
    """
    mock_session = AsyncMock(spec=AsyncSession)

    async def mock_execute(*args, **kwargs):
        query = args[0]
        mock_result = AsyncMock()
        
        if "FROM users" in str(query):
            # Mock a user query
            mock_result.scalars.return_value.first.return_value = User(id=1, username="testuser")
        elif "FROM books" in str(query):
            # Mock a book query
            mock_result.scalars.return_value.first.return_value = Book(id=1, title="Test Book", author="Test Author")
        else:
            # Default to no result
            mock_result.scalars.return_value.first.return_value = None

        return mock_result

    # Attach the side_effect to execute
    mock_session.execute.side_effect = mock_execute
    mock_session.commit = AsyncMock()

    yield mock_session

@pytest.fixture(scope="function", autouse=True)
def override_get_db(test_db):
    """
    This fixture overrides the get_db dependency with the
    same mock_session from 'test_db'.
    By using 'autouse=True', we ensure it's applied to all tests.
    """
    async def _get_db_override():
        yield test_db

    app.dependency_overrides[get_db] = _get_db_override
    yield
    # Clear overrides to avoid side effects on other tests/modules
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def async_client():
    """
    Create an AsyncClient that uses ASGITransport to
    talk directly to the FastAPI app in memory.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_add_user(async_client, test_db):
    response = await async_client.post("/users/add", data={"username": "testuser"})
    # Check that the endpoint responded successfully.
    assert response.status_code in [200, 303]
    # Now check if our mock DB was called
    test_db.execute.assert_called()

@pytest.mark.asyncio
async def test_delete_user(async_client, test_db):
    response = await async_client.get("/users/delete/1")
    assert response.status_code in [200, 303]
    test_db.execute.assert_called()

@pytest.mark.asyncio
async def test_update_user(async_client, test_db):
    response = await async_client.post("/users/update/1", data={"username": "updatedname"})
    assert response.status_code in [200, 303]
    test_db.execute.assert_called()

@pytest.mark.asyncio
async def test_delete_book(async_client, test_db):
    response = await async_client.get("/books/delete/1")
    assert response.status_code in [200, 303]
    test_db.execute.assert_called()

@pytest.mark.asyncio
async def test_update_book(async_client, test_db):
    response = await async_client.post("/books/update/1", data={"title": "Updated Title", "author": "New Author"})
    assert response.status_code in [200, 303]
    test_db.execute.assert_called()

@pytest.mark.asyncio
async def test_duplicate_transaction(async_client, test_db):
    response = await async_client.post(
        "/transactions/add_transaction",
        data={"user_id": 1, "status": "checked_out", "book_id": 1}
    )
    assert response.status_code in [200, 303]
    test_db.execute.assert_called()
