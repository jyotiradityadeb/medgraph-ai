up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

shell-backend:
	docker-compose exec backend bash

shell-frontend:
	docker-compose exec frontend sh

seed:
	docker-compose exec backend python scripts/seed_graph.py && docker-compose exec backend python scripts/seed_vectors.py

validate:
	docker-compose exec backend python scripts/validate_system.py

test:
	docker-compose exec backend pytest tests/ -v
