from urllib.parse import unquote
from fastapi import APIRouter, Depends, Request, Response, UploadFile, File, HTTPException
from beanie.operators import In
from app.dependencies import get_current_user
from app.models import Ticket, Patient, Doctor, Report, MedicalDocumentParent, MedicalDocumentChunk
from app.utils.ai_utils import process_medical_pdf, pinecone_index

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user):
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _source_filename(parent: MedicalDocumentParent) -> str:
    if parent.source_filename:
        return parent.source_filename
    # Legacy documents predate the source_filename field; recover it from the title.
    return parent.title.rsplit(" - Part ", 1)[0] if " - Part " in parent.title else parent.title


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


@router.post("/upload-medical-pdf")
async def upload_medical_pdf(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    _require_admin(current_user)

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        file_bytes = await file.read()
        result = await process_medical_pdf(file_bytes, file.filename)
        return {"status": "success", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base")
async def list_knowledge_base(current_user = Depends(get_current_user)):
    _require_admin(current_user)

    parents = await MedicalDocumentParent.find().to_list()

    documents = {}
    for p in parents:
        name = _source_filename(p)
        entry = documents.setdefault(name, {
            "filename": name,
            "chunk_count": 0,
            "uploaded_at": p.created_at,
        })
        entry["chunk_count"] += 1
        if p.created_at < entry["uploaded_at"]:
            entry["uploaded_at"] = p.created_at

    return {"documents": sorted(documents.values(), key=lambda d: d["uploaded_at"], reverse=True)}


@router.get("/knowledge-base/{filename}")
async def get_knowledge_base_document(filename: str, current_user = Depends(get_current_user)):
    _require_admin(current_user)
    filename = unquote(filename)

    parents = await MedicalDocumentParent.find().to_list()
    matching = sorted(
        (p for p in parents if _source_filename(p) == filename),
        key=lambda p: p.created_at
    )
    if not matching:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "filename": filename,
        "chunks": [
            {"id": str(p.id), "title": p.title, "content": p.content, "created_at": p.created_at}
            for p in matching
        ]
    }


@router.delete("/knowledge-base/{filename}")
async def delete_knowledge_base_document(filename: str, current_user = Depends(get_current_user)):
    _require_admin(current_user)
    filename = unquote(filename)

    parents = await MedicalDocumentParent.find().to_list()
    matching = [p for p in parents if _source_filename(p) == filename]
    if not matching:
        raise HTTPException(status_code=404, detail="Document not found")

    parent_ids = [p.id for p in matching]
    children = await MedicalDocumentChunk.find(In(MedicalDocumentChunk.parent_id, parent_ids)).to_list()
    child_ids = [str(c.id) for c in children]

    if pinecone_index and child_ids:
        pinecone_index.delete(ids=child_ids)

    for c in children:
        await c.delete()
    for p in matching:
        await p.delete()

    return {
        "status": "success",
        "detail": f"Deleted {len(matching)} chunk(s) and {len(child_ids)} embedding(s) for '{filename}'."
    }
