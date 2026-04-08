run-backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

install-backend:
	cd backend && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

setup:
	cp backend/.env.example backend/.env
	make install-backend
	make install-frontend

test-backend:
	cd backend && pytest tests/ -v
