from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.services.ranking_service import build_rankings
from app.services.openai_service import ai_summary_for_top5
from app.core.config import now_tw

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
def dashboard(request: Request):
    data = build_rankings()
    ai = ai_summary_for_top5(data["top5"])
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "now_tw": now_tw(),
        "top5": data["top5"],
        "treasure": data["treasure"],
        "ai": ai
    })
