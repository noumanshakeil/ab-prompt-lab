from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db import get_db
from backend.services import experiments as svc

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, experiment_id: str | None = None, db: AsyncSession = Depends(get_db)):
    exps = await svc.list_experiments(db)
    metrics = await svc.metrics(db, experiment_id) if experiment_id else None
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "A/B Prompt Lab", "experiments": exps, "experiment_id": experiment_id, "metrics": metrics},
    )

@router.post("/ui/experiments")
async def ui_exp(
    name: str = Form(...),
    prompt_a: str = Form(...),
    prompt_b: str = Form(...),
    traffic_a: int = Form(50),
    db: AsyncSession = Depends(get_db),
):
    row = await svc.create_experiment(db, name, prompt_a, prompt_b, traffic_a)
    return RedirectResponse(f"/?experiment_id={row.id}", status_code=303)

@router.post("/ui/run")
async def ui_run(
    experiment_id: str = Form(...),
    subject: str = Form(...),
    user_input: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    await svc.route_and_run(db, experiment_id, subject, user_input)
    return RedirectResponse(f"/?experiment_id={experiment_id}", status_code=303)
