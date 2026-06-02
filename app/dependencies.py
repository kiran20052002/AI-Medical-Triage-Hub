from fastapi import Request, HTTPException, status, Depends, Response
from fastapi.responses import RedirectResponse
from app.utils.auth_utils import decode_access_token, decode_token, create_access_token
from app.models import Patient, Doctor, RefreshToken
from datetime import datetime, timezone

async def get_current_user(request: Request, response: Response):
    token = request.cookies.get("access_token")
    user_payload = None
    
    if token:
        try:
            scheme, _, param = token.partition(" ")
            user_payload = decode_access_token(param)
        except Exception:
            user_payload = None

    if not user_payload:
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            db_token = await RefreshToken.find_one(RefreshToken.token == refresh_token)
            if db_token and db_token.expires_at > datetime.now(timezone.utc):
                user_payload = decode_token(refresh_token)
                if user_payload:
                    new_access_token = create_access_token(data=user_payload)
                    response.set_cookie(key="access_token", value=f"Bearer {new_access_token}", httponly=True)
            else:
                if db_token:
                    await db_token.delete()

    if not user_payload:
        return None
            
    user_id = user_payload.get("id")
    role = user_payload.get("role")
    
    if role == "admin":
        # Admin is not in DB, return a mock user object
        class AdminUser:
            def __init__(self, email, role, id):
                self.email = email
                self.role = role
                self.id = id
        return AdminUser(email=user_payload.get("sub"), role="admin", id=user_id)

    if role == "patient": 
        user = await Patient.get(user_id)
    elif role == "doctor":
        user = await Doctor.get(user_id)
    else:
        return None
        
    return user

async def require_user(user = Depends(get_current_user)):
    if not user:
        return RedirectResponse(
            url="/auth/login",
            status_code=303
        )
    return user
