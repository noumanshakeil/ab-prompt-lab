from __future__ import annotations
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.llm import get_llm
from backend.models import Assignment, Experiment, Variant
from backend.utils.ids import short_id

def pick_variant(traffic_a: int, subject: str) -> str:
    bucket = int(hashlib.sha256(subject.encode()).hexdigest(), 16) % 100
    return "A" if bucket < max(0, min(traffic_a, 100)) else "B"

async def create_experiment(
    session: AsyncSession, name: str, prompt_a: str, prompt_b: str, traffic_a: int = 50
) -> Experiment:
    exp = Experiment(id=short_id(), name=name.strip()[:160], traffic_a=traffic_a)
    session.add(exp)
    await session.flush()
    session.add(Variant(id=short_id(), experiment_id=exp.id, label="A", prompt=prompt_a.strip()))
    session.add(Variant(id=short_id(), experiment_id=exp.id, label="B", prompt=prompt_b.strip()))
    await session.commit()
    await session.refresh(exp)
    return exp

async def list_experiments(session: AsyncSession) -> list[Experiment]:
    return list((await session.execute(select(Experiment).order_by(Experiment.created_at.desc()))).scalars())

async def get_variants(session: AsyncSession, experiment_id: str) -> list[Variant]:
    stmt = select(Variant).where(Variant.experiment_id == experiment_id)
    return list((await session.execute(stmt)).scalars())

async def route_and_run(session: AsyncSession, experiment_id: str, subject: str, user_input: str) -> dict:
    exp = await session.get(Experiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")
    label = pick_variant(exp.traffic_a, subject)
    variants = {v.label: v for v in await get_variants(session, experiment_id)}
    variant = variants.get(label)
    if not variant:
        raise ValueError("variant missing")
    llm = get_llm()
    output = await llm.complete(user_input, system=variant.prompt)
    score = min(1.0, len(output) / 120.0)
    variant.impressions += 1
    variant.total_score += score
    session.add(
        Assignment(
            experiment_id=experiment_id,
            subject=subject[:120],
            variant_label=label,
            score=score,
            output=output[:4000],
        )
    )
    await session.commit()
    return {"variant": label, "output": output, "score": score}

async def metrics(session: AsyncSession, experiment_id: str) -> dict:
    variants = await get_variants(session, experiment_id)
    rows = []
    best_label = None
    best_avg = -1.0
    for v in variants:
        avg = (v.total_score / v.impressions) if v.impressions else 0.0
        rows.append({"label": v.label, "impressions": v.impressions, "avg_score": round(avg, 3)})
        if v.impressions and avg > best_avg:
            best_avg = avg
            best_label = v.label
    return {"variants": rows, "leader": best_label}

async def select_winner(session: AsyncSession, experiment_id: str) -> dict:
    m = await metrics(session, experiment_id)
    exp = await session.get(Experiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")
    exp.winner = m.get("leader")
    exp.status = "completed"
    await session.commit()
    return {"winner": exp.winner, "metrics": m}
