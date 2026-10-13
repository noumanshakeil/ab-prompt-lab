# Dev server for ab-prompt-lab
$env:LLM_MODE = "mock"
uvicorn backend.main:app --reload --port 8000
