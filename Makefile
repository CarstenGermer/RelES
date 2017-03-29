help:
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

test: init_env requirements_dev ## Run unittests via py.test
	echo "*** Running tests..."
	py.test tests

test_debug: init_env requirements_dev ## Run unittests via py.test in debug/verbose mode
	echo "*** Running tests..."
	py.test tests --timeout=3 --timeout_method=thread -v

coverage: ## Measure code coverage
	py.test --cov=reles tests

lint: ## Check code for linting issues (configured via pylama.ini)
	pylama

sort_imports: ## Check and optimize our python import statements (configured via .editorconfig)
	isort

init_env: ## Init runtime environment (bring up containers, update .env file)
	echo "*** Setting up runtime environment..."
	echo "*** Make sure to run 'eval \$$(docker-machine env default)' first if needed ***"
	docker-compose up -d
	python bin/docker2dotenv.py

serve: init_env ## Launch (autoreloading) server instance
	echo "*** Running autoreloading gunicorn..."
	gunicorn --workers=1 --reload wsgi:application

pip_tools:
	pip install --upgrade pip pip-tools > /dev/null 2>&1

requirements: pip_tools ## Compile (resolve dependency tree) & sync (install) requirements
	echo "*** syncing venv to match requirements"
	pip-sync requirements.txt
	# pip-sync removed `pkg-resources-0.0.0`
	wget https://bootstrap.pypa.io/ez_setup.py -O - | python > /dev/null

requirements_dev: pip_tools ## Compile (resolve dependency tree) & sync (install) development requirements
	echo "*** syncing venv to match requirements_dev.txt"
	pip-sync requirements_dev.txt
	# pip-sync removed `pkg-resources-0.0.0`
	wget https://bootstrap.pypa.io/ez_setup.py -O - | python > /dev/null

requirements_upgrade: pip_tools ## Let pip-compile try to find upgrades to our dependencies
	pip-compile --upgrade requirements.in
	pip-compile --upgrade requirements_dev.in
	pip-sync requirements_dev.txt
	# pip-sync removed `pkg-resources-0.0.0`
	wget https://bootstrap.pypa.io/ez_setup.py -O - | python > /dev/null
	git diff requirements.txt requirements_dev.txt

clean: ## Clean various python runtime cruft
	find -type f -iname *.py[co] -delete
	find -type d -name __pycache__ | xargs rm -rf
	find -type d -name .cache | xargs rm -rf

runserver: init_env requirements_dev
	./manage.py runserver --debug

# MAKE FILE "SETTINGS"
.DEFAULT: help
.PHONY: help test coverage lint sort_imports init_env pip_tools serve requirements requirements_dev requirements_upgrade clean
.SILENT:
