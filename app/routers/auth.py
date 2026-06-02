from fastapi import APIRouter, HTTPException, status, Request, Response, Form
import os
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from app.utils.auth_utils import verify_password, create_access_token, get_password_hash, create_refresh_token, decode_token, REFRESH_TOKEN_EXPIRE_DAYS
from app.models import Patient, Doctor, RefreshToken
from beanie import PydanticObjectId
from datetime import timedelta, datetime



router = APIRouter(prefix="/auth", tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")

async def create_tokens_and_set_cookies(response: Response, user_id: str, email: str, role: str):
    access_token = create_access_token(data={"sub": email, "role": role, "id": user_id})
    refresh_token_str = create_refresh_token(data={"sub": email, "role": role, "id": user_id})
    
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    rf_doc = RefreshToken(
        token=refresh_token_str,
        user_id=PydanticObjectId(user_id),
        user_role=role,
        expires_at=expires_at
    )
    await rf_doc.insert()
    
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token_str, httponly=True, max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)
    return response


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):    
    user = await Patient.find_one(Patient.email == email)
    role = "patient"
    if not user:
        user = None
    
    print(f"Login attempt for {user.email}")

    if user: 
        print(f"User found. Role: {role}")
        is_valid = verify_password(password, user.password)
        print(f"Password valid? {is_valid}")
    else:
        print("User not found in DB")
    
    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": "Invalid credentials"})
    
    
    
    response = RedirectResponse(url="/tickets/", status_code=status.HTTP_303_SEE_OTHER)
    await create_tokens_and_set_cookies(response, str(user.id), user.email, role)
    return response

@router.get("/admin-login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("auth/admin_login.html", {"request": request})

@router.post("/admin-login")
async def login_admin(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    
    env_email = os.getenv("ADMIN_EMAIL")
    env_password = os.getenv("ADMIN_PASSWORD")
    
    auth_success = False
    
    if env_email and env_password and email == env_email and password == env_password:
        auth_success = True
    else:
        auth_success = False
    
    if not auth_success:
        return templates.TemplateResponse("auth/admin_login.html", {
            "request": request,
            "error": "Invalid admin credentials"
        })

    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    await create_tokens_and_set_cookies(response, "000000000000000000000000", env_email, "admin")
    return response



@router.get("/doctor-login", response_class = HTMLResponse)
async def doctor_login_page(request: Request):
    return templates.TemplateResponse("auth/doctor_login.html", {"request": request})

@router.post("/doctor-login")
async def login_doctor(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    user = await Doctor.find_one(Doctor.email == email)

    if not user or user.role!="doctor" or not verify_password(password, user.password):
        return templates.TemplateResponse("auth/doctor_login.html", {
            "request": request,
            "error": "Invalid doctor credentials"
        })
    
    response = RedirectResponse(url="/tickets/", status_code=status.HTTP_303_SEE_OTHER)
    await create_tokens_and_set_cookies(response, str(user.id), user.email, user.role)
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
async def logout(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await RefreshToken.find_one(RefreshToken.token == refresh_token).delete()
    
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

@router.post("/refresh")
async def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    

    db_token = await RefreshToken.find_one(RefreshToken.token == refresh_token)
    if not db_token or db_token.expires_at < datetime.utcnow():
        if db_token:
            await db_token.delete()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    

    payload = decode_token(refresh_token)
    if not payload:
        await db_token.delete()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    email = payload.get("sub")
    role = payload.get("role")
    user_id = payload.get("id")
    
    await db_token.delete()
    
    await create_tokens_and_set_cookies(response, user_id, email, role)
    return {"status": "success"}
