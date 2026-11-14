$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -q
Set-Location ..
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}
Set-Location backend
alembic upgrade head
python -m app.seed_roles
python -m app.seed_categories
python -m app.seed_service_categories
uvicorn app.main:app --host 127.0.0.1 --port 8742 --reload
