# Makefile for softsync

.PHONY: create-venv check-venv install-dev test

create-venv:
	python3 -m venv .venv
	.venv/bin/pip3 install --upgrade pip==21.3.1
	.venv/bin/pip3 install -e '.[dev]'

check-venv:
ifndef VIRTUAL_ENV
	$(error VIRTUAL_ENV is undefined)
endif

install-dev: check-venv
	pip3 install -e '.[dev]'

test: check-venv
	pytest
