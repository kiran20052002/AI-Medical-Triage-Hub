from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.dependencies import get_current_user
from app.models import Ticket, Patient, Doctor, Report

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user = Depends(get_current_user)):
    if not current_user or current_user.role != "admin":
        return RedirectResponse("/auth/login")
    
    total_patients_count = await Patient.find().count()
    total_doctors_count = await Doctor.find().count()

    # Fetch only doctors for the list
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

    return templates.TemplateResponse("dashboard_admin.html", {
        "request": request,
        "user": current_user,
        "total_patients": total_patients_count,
        "total_doctors": total_doctors_count,
        "total_tickets": total_tickets,
        "all_users": all_users, # This now contains only doctors
        "reports": reports
    })


