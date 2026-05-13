from fastapi import Request, HTTPException, status, Depends
from app.utils.auth_utils import decode_access_token
from app.models import Patient, Doctor

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        scheme, _, param = token.partition(" ")
        payload = decode_access_token(param)
        if not payload:
            return None
            
        user_id = payload.get("id")
        role = payload.get("role")
        
        if role == "admin":
            # Admin is not in DB, return a mock user object
            class AdminUser:
                def __init__(self, email, role, id):
                    self.email = email
                    self.role = role
                    self.id = id
            return AdminUser(email=payload.get("sub"), role="admin", id=user_id)

        if role == "patient": 
            user = await Patient.get(user_id)
        elif role == "doctor":
            user = await Doctor.get(user_id)
        else:
            return None
            
        return user
    except Exception:
        return None

async def require_user(user = Depends(get_current_user)):
    if not user:
         raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail="Not authenticated",
            headers={"Location": "/auth/login"},
        )
    return user
