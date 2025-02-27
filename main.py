from fastapi import FastAPI, Request
from database import create_tables
import routes.books as book_routes
import routes.users as user_routes
import routes.transactions as transaction_routes
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup():
    await create_tables()  # Ensure database tables are created

# Include Routers
app.include_router(book_routes.router, prefix="/books", tags=["Books"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(transaction_routes.router, prefix="/transactions", tags=["Transactions"])


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
