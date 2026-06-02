from fastapi import Request, HTTPException, status, Depends, Response
from app.utils.auth_utils import decode_access_token, decode_token, create_access_token
from app.models import Patient, Doctor, RefreshToken
from datetime import datetime

async def get_current_user(request: Request, response: Response):
    cookies = request.cookies
    token = cookies.get("access_token")
    user_payload = None
    
    if token:
        try:
            user_payload = decode_access_token(token)
        except Exception as e:
            user_payload = None

    if not user_payload:
        refresh_token = cookies.get("refresh_token")
        if refresh_token:
            db_token = await RefreshToken.find_one(RefreshToken.token == refresh_token)
            if db_token and db_token.expires_at > datetime.utcnow():
                user_payload = decode_token(refresh_token)
                if user_payload:
                    new_access_token = create_access_token(data=user_payload)
                    response.set_cookie(
                        key="access_token", 
                        value=new_access_token, 
                        httponly=True, 
                        path="/",
                        samesite="lax",
                        secure=False
                    )
            else:
                if db_token:
                    await db_token.delete()

    if not user_payload:
        return None
            
    user_id = user_payload.get("id")
    role = user_payload.get("role")
    
    if role == "admin":
        class AdminUser:
            def __init__(self, email, role, id):
                self.email = email
                self.role = role
                self.id = id
        return AdminUser(email=user_payload.get("sub"), role="admin", id=user_id)

    from beanie import PydanticObjectId
    try:
        obj_id = PydanticObjectId(user_id)
        if role == "patient": 
            user = await Patient.get(obj_id)
        elif role == "doctor":
            user = await Doctor.get(obj_id)
        else:
            user = None

    except Exception as e:
        user = None
        
    return user

async def require_user(user = Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
