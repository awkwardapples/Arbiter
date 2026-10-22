.PHONY: setup lint test verify verify-pass secret-scan hardcode-check

setup:
	python scripts/tasks.py setup

lint:
	python scripts/tasks.py lint

test:
	python scripts/tasks.py test

verify:
	python scripts/tasks.py verify

verify-pass:
	python scripts/tasks.py verify-pass --pass $(PASS)

secret-scan:
	python scripts/tasks.py secret-scan

hardcode-check:
	python scripts/tasks.py hardcode-check
