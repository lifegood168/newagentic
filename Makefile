.PHONY: dev test lint format typecheck init-db demo docker-up docker-down clean check-constraints

PY := python
APP := app.api.main:app

dev:
	uvicorn $(APP) --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=app --cov-report=term-missing

lint:
	ruff check . && ruff format --check .

format:
	ruff format .

typecheck:
	mypy app

init-db:
	$(PY) -m app.storage.init

demo:
	@echo "Health check:"
	@curl -sS http://localhost:8000/healthz | tee /dev/stderr; echo
	@echo "Templates:"
	@curl -sS http://localhost:8000/templates | tee /dev/stderr; echo

docker-up:
	docker compose -f deploy/docker-compose.yml up --build -d

docker-down:
	docker compose -f deploy/docker-compose.yml down

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete

# 强约束 CI 检查（见 ADR-0002）
check-constraints:
	@echo "约束 1：引擎层无业务残留"
	@! grep -rn "sales\|product\|client" app/runtime app/gateway app/storage app/factory 2>/dev/null || (echo "❌ 违反约束 1" && exit 1)
	@echo "约束 2：LLM 调用唯一入口"
	@! grep -rn "openai\.\|anthropic\.\|v1/chat" app/ --include="*.py" | grep -v "app/gateway/" || (echo "❌ 违反约束 2" && exit 1)
	@echo "约束 6：Phase 0/1 不存在 app/memory/"
	@! test -d app/memory || (echo "❌ 违反约束 6" && exit 1)
	@echo "✅ 所有约束通过"
