@echo off
echo Starting AuditMind AI...
start cmd /k "cd /d %~dp0backend && C:\Users\HP\anaconda3\python.exe -m uvicorn app.main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
start cmd /k "cd /d %~dp0frontend && npm run dev"
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
