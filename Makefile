.PHONY: data dev setup

# Generates the artifacts directly into the frontend's public folder
data:
	mkdir -p frontend/public/data
	uv run --directory backend python -m urbancanopy.cli --config backend/configs/multicity-demo.yml --output-dir ../frontend/public/data

# Installs frontend dependencies and starts the Next.js dev server
dev:
	cd frontend && npm install && npm run dev

# Full setup for a fresh clone
setup: data dev
