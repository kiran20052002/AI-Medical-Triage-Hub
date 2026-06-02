from fastapi import APIRouter, Depends, Request, Response
from app.dependencies import get_current_user
from app.models import Ticket, Patient, Doctor, Report

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
async def admin_dashboard(request: Request, current_user = Depends(get_current_user)):
    if not current_user or current_user.role != "admin":
        return Response(status_code=401)
    
    total_patients_count = await Patient.find().count()
    total_doctors_count = await Doctor.find().count()

    doctors = await Doctor.find().to_list()

    all_users = []
    for d in doctors:
        all_users.append({
            "email": d.email,
            "role": d.role,
            "id": str(d.id),
            "specialist": getattr(d, "specialist", [])
        })
    

    total_tickets = await Ticket.find().count()
    reports = await Report.find().sort("-created_at").to_list()

    return {
        "user": current_user,
        "total_patients": total_patients_count,
        "total_doctors": total_doctors_count,
        "total_tickets": total_tickets,
        "all_users": all_users, 
        "reports": reports
    }


