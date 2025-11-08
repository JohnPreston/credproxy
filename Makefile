.PHONY: clean clean-test clean-pyc clean-build docs help conform release-test release codebuild coverage docker-build security-scan sbom
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, sys, subprocess
from pathlib import Path

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

file_path = Path(sys.argv[1]).resolve()
file_url = "file://" + pathname2url(str(file_path))

# Try different methods to open browser
if os.environ.get('DISPLAY'):
	try:
		import webbrowser
		webbrowser.open(file_url)
		print(f"Opened browser: {file_url}")
	except Exception as e:
		print(f"Browser open failed: {e}")
		try:
			subprocess.run(['xdg-open', str(file_path)], check=False)
		except:
			pass
else:
	print(f"Documentation available at: {file_url}")
	print(f"File path: {file_path}")
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"
AWS := aws

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test clean-c9 ## remove all build, test, coverage and Python artifacts

clean-c9:
	find . -type f -name ".~c9*.py" -print -delete

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -type d -name '*.egg-info' -exec rm -fr {} +
	find . -type d -name '*.egg' -exec rm -rf {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

test: ## run tests quickly with the default Python
	poetry run pytest tests -vv -s -x

format: ## format code using ruff and isort
	poetry run ruff format credproxy tests

lint: ## lint code using ruff
	poetry run ruff check credproxy tests

test-all: ## run tests on every Python version with tox
	tox --skip-missing-interpreters

test-cov: ## run tests with coverage report
	poetry run pytest tests --cov=credproxy --cov-report=term-missing --cov-report=html --cov-report=xml -vv

test-cov-view: test-cov ## run tests with coverage and open HTML report
	$(BROWSER) htmlcov/index.html

test-cov-summary: ## run tests and show coverage summary only
	poetry run pytest tests --cov=credproxy --cov-report=term -vv

coverage: ## check code coverage quickly with the default Python
	poetry run coverage run --source credproxy -a -m pytest tests -vv -x
	poetry run coverage report -m
	poetry run coverage xml -o coverage/coverage.xml
	poetry run coverage html
	$(BROWSER) htmlcov/index.html

.ONESHELL:

codebuild: ## check code coverage quickly with the default Python
	coverage run --source credproxy -m behave tests/features --junit;\
	BEHAVE=$$? ;\
	coverage run --source credproxy -a -m pytest tests -vv -x ;\
	PYTEST=$$? ;\
	echo $$BEHAVE
	echo $$PYTEST
	coverage report -m
	coverage xml -o coverage/coverage.xml
	if [ $$BEHAVE -eq 0 ] && [ $$PYTEST -eq 0 ]; then exit 0; else exit 1; fi

docs: clean-c9 ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/build/html/index.html

nightly-docs: docs
	echo Uploading to s3://${NIGHTLY_DOCS_BUCKET} && \
	cd docs/_build/html && \
	$(AWS) s3 sync . s3://${NIGHTLY_DOCS_BUCKET}/ \
	--storage-class ONEZONE_IA

publish-docs: docs
	cd docs/build/html && \
	$(AWS) s3 sync . s3://${DOCS_BUCKET}/ \
	--storage-class ONEZONE_IA

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	twine check dist/*
	poetry publish --build

release-test: dist ## package and upload a release
	twine check dist/* || echo Failed to validate release
	poetry config repositories.pypitest https://test.pypi.org/legacy/
	poetry publish -r pypitest --build

dist: clean ## builds source and wheel package
	poetry build
	ls -l dist

install: conform ## install the package to the active Python's site-packages
	pip install . --use-pep517 #--use-feature=in-tree-build

conform	: ## Conform to a standard of coding syntax
	poetry run ruff check --fix credproxy tests
	poetry run ruff format credproxy tests
	find credproxy -name "*.json" -type f  -exec sed -i '1s/^\xEF\xBB\xBF//' {} +
	deno fmt **/*.md || echo "deno not installed"
	deno fmt **/*.yaml || echo "deno not installed"

docker-build: sbom ## Build Docker image using docker compose build
	docker compose build \
		--build-arg GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
		--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ")

security-scan: ## Run security vulnerability scan using Grype
	grype dir:.
	$(MAKE) docker-build
	grype public.ecr.aws/compose-x/aws/credproxy:latest

sbom: ## Generate Software Bill of Materials (SBOM)
	poetry run cyclonedx-py poetry --only main -o sbom.json
