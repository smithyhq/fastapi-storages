ARGS ?= $(filter-out $@,$(MAKECMDGOALS))

%:
	@:

PY_ARGS := $(or $(filter %.py,$(ARGS)),fastapi_storages)

setup:
	uv sync --all-groups

test:
	uv run coverage run -m pytest $(ARGS)

cov:
	uv run coverage report --show-missing --skip-covered --fail-under=99
	uv run coverage xml

lint:
	uv run ruff check $(PY_ARGS)
	uv run ruff format --check $(PY_ARGS)
	uv run mypy $(PY_ARGS)

format:
	uv run ruff format $(PY_ARGS)
	uv run ruff check --fix $(PY_ARGS)

docs-build:
	uv run mkdocs build

docs-serve:
	uv run mkdocs serve --dev-addr localhost:8080

docs-deploy:
	uv run mkdocs gh-deploy --force

build:
	uv build

publish:
	uv publish


.PHONY: setup test cov lint format docs-build docs-serve docs-deploy build publish
