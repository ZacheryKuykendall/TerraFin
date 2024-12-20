PYTHON=python
PIP=pip
TEST_PATH=./tests

.PHONY: clean install test lint

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

install:
	$(PIP) install -r requirements.txt

test:
	$(PYTHON) -m pytest $(TEST_PATH) -v --cov=terrafin_calculator --cov-report=term

lint:
	$(PYTHON) -m flake8 terrafin_calculator tests
	$(PYTHON) -m black terrafin_calculator tests --check
	$(PYTHON) -m isort terrafin_calculator tests --check-only
