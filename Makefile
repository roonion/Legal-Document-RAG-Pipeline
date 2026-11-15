.PHONY: dev-up dev-down backend-test frontend-dev lint eval load-test install-backend install-frontend

dev-up:
	docker compose up -d

dev-down:
	docker compose down

install-backend:
	cd backend && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

backend-test:
	cd backend && pytest tests/unit tests/nodes -q --tb=short

frontend-dev:
	cd frontend && npm run dev

lint:
	cd backend && ruff check app tests && ruff format --check app tests
	cd frontend && npm run lint

eval:
	cd backend && pytest tests/evaluation -q --tb=short || true

load-test:
	cd backend && locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 60s || true
