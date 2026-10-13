"""A/B Prompt Lab — FastAPI backend + Jinja UI."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .llm import complete

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data" / "store.json"
FIELDS = ['name', 'variant_a', 'variant_b']

app = FastAPI(title="A/B Prompt Lab", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))


def load_store() -> dict:
    if not DATA.exists():
        DATA.parent.mkdir(parents=True, exist_ok=True)
        payload = {"experiments": [
  {
    "id": "ab1",
    "name": "tone",
    "variant_a": "formal",
    "variant_b": "casual"
  }
]}
        DATA.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return json.loads(DATA.read_text(encoding="utf-8"))


def save_store(store: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(store, indent=2), encoding="utf-8")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ab-prompt-lab", "llm_mode": settings.llm_mode}


@app.get("/api/experiments")
def list_items() -> dict:
    store = load_store()
    return {"experiments": store.get("experiments", [])}


@app.post("/api/experiments")
def create_item(payload: dict) -> dict:
    store = load_store()
    item = {"id": uuid.uuid4().hex[:8]}
    for key in FIELDS:
        item[key] = payload.get(key)
    store.setdefault("experiments", []).insert(0, item)
    save_store(store)
    return item


@app.post("/api/score_variants")
def run_action(payload: dict) -> dict:
    """Compare A/B prompt variants."""
    prompt = (
        "You are the AI engine for A/B Prompt Lab.\n"
        "Task: Compare A/B prompt variants.\n"
        f"Input JSON: {json.dumps(payload)[:4000]}"
    )
    text = complete(prompt)
    return {"ok": True, "action": "score_variants", "result": text, "mode": settings.llm_mode}


@app.get("/", response_class=HTMLResponse)
def home(request: Request, last_result: str | None = None) -> HTMLResponse:
    store = load_store()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "A/B Prompt Lab",
            "description": "A/B prompt testing lab with traffic splits, metrics, and winner selection UI.",
            "resource": "experiments",
            "action": "score_variants",
            "action_desc": "Compare A/B prompt variants",
            "items": store.get("experiments", []),
            "llm_mode": settings.llm_mode,
            "last_result": last_result,
        },
    )


@app.post("/ui/create", response_class=HTMLResponse)
async def ui_create(request: Request) -> HTMLResponse:
    form = await request.form()
    data = {k: form.get(k) for k in FIELDS}
    create_item(data)
    return home(request)


@app.post("/ui/action", response_class=HTMLResponse)
async def ui_action(request: Request, prompt: str = Form("demo")) -> HTMLResponse:
    result = run_action({"prompt": prompt})
    store = load_store()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "A/B Prompt Lab",
            "description": "A/B prompt testing lab with traffic splits, metrics, and winner selection UI.",
            "resource": "experiments",
            "action": "score_variants",
            "action_desc": "Compare A/B prompt variants",
            "items": store.get("experiments", []),
            "llm_mode": settings.llm_mode,
            "last_result": result.get("result"),
        },
    )
