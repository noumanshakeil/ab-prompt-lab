from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db import get_db
from backend.services import experiments as svc

class ExperimentIn(BaseModel):
    name: str = Field(min_length=2)
    prompt_a: str = Field(min_length=4)
    prompt_b: str = Field(min_length=4)
    traffic_a: int = Field(default=50, ge=0, le=100)

class RunIn(BaseModel):
    subject: str = Field(min_length=2)
    input: str = Field(min_length=1)

router = APIRouter()

@router.get("/experiments")
async def list_experiments(db: AsyncSession = Depends(get_db)):
    rows = await svc.list_experiments(db)
    return {"experiments": [{"id": e.id, "name": e.name, "status": e.status, "winner": e.winner} for e in rows]}

@router.post("/experiments")
async def create_experiment(payload: ExperimentIn, db: AsyncSession = Depends(get_db)):
    row = await svc.create_experiment(db, payload.name, payload.prompt_a, payload.prompt_b, payload.traffic_a)
    return {"id": row.id, "name": row.name}

@router.get("/experiments/{experiment_id}/metrics")
async def get_metrics(experiment_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.metrics(db, experiment_id)

@router.post("/experiments/{experiment_id}/run")
async def run_variant(experiment_id: str, payload: RunIn, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.route_and_run(db, experiment_id, payload.subject, payload.input)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.post("/experiments/{experiment_id}/winner")
async def winner(experiment_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.select_winner(db, experiment_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
