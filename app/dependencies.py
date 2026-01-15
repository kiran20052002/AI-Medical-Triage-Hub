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

        if role == "patient" or role == "admin":
            user = await Patient.get(user_id)
        
        elif role == "doctor":
            user = await Doctor.get(user_id)
        
        else:
            return None
        
        return user
    except Exception:
        return None
