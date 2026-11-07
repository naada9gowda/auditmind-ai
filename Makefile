.PHONY: setup seed-clean seed-demo dev test

setup:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

seed-clean:
	cd backend && C:\Users\HP\anaconda3\python.exe -m app.seed --clean

seed-demo:
	cd backend && C:\Users\HP\anaconda3\python.exe -m app.seed --demo

dev:
	start cmd /k "cd backend && C:\Users\HP\anaconda3\python.exe -m uvicorn app.main:app --reload --port 8000"
	start cmd /k "cd frontend && npm run dev"

test:
	cd backend && C:\Users\HP\anaconda3\python.exe -m pytest tests/ -v
