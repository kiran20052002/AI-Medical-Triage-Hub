from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from app.utils.auth_utils import get_password_hash
from app.models import Patient, Doctor
from beanie import PydanticObjectId


router = APIRouter(prefix="/auth", tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse("auth/signup.html", {"request": request})

@router.post("/signup")
async def signup(request: Request):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    role = form.get("role", "patient")
    specialist_str = form.get("specialist", "")

    # check if user exists in db
    if await Patient.find_one(Patient.email == email):
        return templates.TemplateResponse("auth/signup.html", {"request": request, "error": "Email already registered"})

    hashed_password = get_password_hash(password)

    if role == 'doctor':
        specs = [s.strip() for s in specialist_str.split(",") if s.strip()]
        user = Doctor(email=email, password=hashed_password, role="doctor", specialist=specs)
    else:
        user = Patient(email=email, password=hashed_password, role="patient") 

    await user.insert()

    return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

