from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.dependencies import require_password_changed
from app.routers import admin, attendance, attendance_reports, auth, dashboard, employees, leave, payroll, profiles

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Dayflow HRMS", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(employees.router)
app.include_router(profiles.router)
app.include_router(attendance.router)
app.include_router(attendance_reports.router)
app.include_router(leave.router)
app.include_router(payroll.router)
app.include_router(dashboard.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request, "about.html")


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse(request, "signup.html")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(request, "about.html")




@app.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request):
    return templates.TemplateResponse(request, "change_password.html")


@app.get("/employees", response_class=HTMLResponse)
def employees_page(request: Request):
    return templates.TemplateResponse(request, "employees.html")



@app.get("/profile/{user_id}", response_class=HTMLResponse)
def profile_page(request: Request, user_id: int):
    return templates.TemplateResponse(request, "profile.html", {"user_id": user_id})


@app.get("/attendance/view", response_class=HTMLResponse)
def attendance_page(request: Request):
    return templates.TemplateResponse(request, "attendance.html")


@app.get("/time-off", response_class=HTMLResponse)
def time_off_page(request: Request):
    return templates.TemplateResponse(request, "time_off.html")


@app.get("/payroll", response_class=HTMLResponse)
def payroll_page(request: Request):
    return templates.TemplateResponse(request, "payroll.html")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")