@echo off
setlocal

REM === Activa venv (ajusta si tu carpeta es distinta) ===
call .\.venv\Scripts\activate.bat

REM === Config: usa Postgres o comenta y usa SQLite ===
REM set CHOMBI_DB_URL=postgresql+psycopg://postgres:1234@localhost:5432/chombi
REM set CHOMBI_API_KEY=supersecreta

REM === Si quieres usar SQLite para pruebas ===
REM set CHOMBI_DB_URL=sqlite:///./chombi.db

python -m uvicorn app:app --reload --port 8000
endlocal
