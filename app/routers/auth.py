from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.templating import Jinja2Templates
import os
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, HTMLResponse
from app.utils.auth_utils import verify_password, create_access_token, get_password_hash
from app.models import Patient, Doctor
from beanie import PydanticObjectId
from datetime import timedelta


router = APIRouter(prefix="/auth", tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = await Patient.find_one(Patient.email == form_data.username)
    role = "patient"
    if not user:
        user = None
    
    print(f"Login attempt for {user.email}")

    if user: 
        print(f"User found. Role: {role}")
        is_valid = verify_password(form_data.password, user.password)
        print(f"Password valid? {is_valid}")
    else:
        print("User not found in DB")
    
    if not user or not verify_password(form_data.password, user.password):
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": "Invalid credentials"})
    
    
    # Create token
    access_token = create_access_token(data={"sub": user.email, "role": role, "id": str(user.id)})

    response = RedirectResponse(url="/tickets/", status_code=status.HTTP_303_SEE_OTHER)

    # Set cookie
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return response

@router.get("/admin-login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("auth/admin_login.html", {"request": request})

@router.post("/admin-login")
async def login_admin(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    
    env_email = os.getenv("ADMIN_EMAIL")
    env_password = os.getenv("ADMIN_PASSWORD")
    
    auth_success = False
    
    if env_email and env_password and form_data.username == env_email and form_data.password == env_password:
        auth_success = True
    else:
        auth_success = False
    
    if not auth_success:
        return templates.TemplateResponse("auth/admin_login.html", {
            "request": request,
            "error": "Invalid admin credentials"
        })

    # Create access token
    access_token = create_access_token(
        data={"sub": env_email, "role": "admin", "id": "000000000000000000000000"},
        expires_delta=timedelta(minutes=30)
    )
    
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response



@router.get("/doctor-login", response_class = HTMLResponse)
async def doctor_login_page(request: Request):
    return templates.TemplateResponse("auth/doctor_login.html", {"request": request})

@router.post("/doctor-login")
async def login_doctor(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = await Doctor.find_one(Doctor.email == form_data.username)

    if not user or user.role!="doctor" or not verify_password(form_data.password, user.password):
        return templates.TemplateResponse("auth/doctor_login.html", {
            "request": request,
            "error": "Invalid doctor credentials"
        })
    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "id": str(user.id)},
        expires_delta=timedelta(minutes=30)
    )

    response = RedirectResponse(url="/tickets/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response


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

    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response
