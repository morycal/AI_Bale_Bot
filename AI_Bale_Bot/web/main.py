from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from core.database import get_users

app = FastAPI()
templates = Jinja2Templates(directory="web/templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/users")
def users(request: Request):
    data = get_users()
    return templates.TemplateResponse("users.html", {"request": request, "users": data})

@app.get("/stats")
def stats(request: Request):
    data = get_users()
    return templates.TemplateResponse("stats.html", {"request": request, "count": len(data)})