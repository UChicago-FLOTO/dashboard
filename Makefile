# Set make variables from .env file
ifneq (,$(wildcard ./.env))
	include .env
	export
	ENV_FILE_PARAM = --env-file .env
endif

DOCKER_TAG ?= $(shell git rev-parse --short HEAD)
DOCKER_IMAGE ?= $(DOCKER_REGISTRY)/floto:$(DOCKER_TAG)
DOCKER_IMAGE_LATEST ?= $(DOCKER_REGISTRY)/floto:latest
DOCKER_DEV_IMAGE ?= floto-dev:$(DOCKER_TAG)
DOCKER_DEV_IMAGE_LATEST ?= floto-dev:latest
PY_IMG_TAG ?= 3.9.7

.env:
	cp .env.sample .env

.PHONY: build
build: .env
	docker build --build-arg PY_IMG_TAG=$(PY_IMG_TAG) \
				 -t $(DOCKER_IMAGE) -f Dockerfile --target release .
	docker tag $(DOCKER_IMAGE) $(DOCKER_IMAGE_LATEST)

build-dev: .env
	docker build --build-arg PY_IMG_TAG=$(PY_IMG_TAG) \
				 -t $(DOCKER_DEV_IMAGE) -f Dockerfile --target dev .
	docker tag $(DOCKER_DEV_IMAGE) $(DOCKER_DEV_IMAGE_LATEST)

.PHONY: publish
publish:
	docker push $(DOCKER_IMAGE)

.PHONY: publish-latest
publish-latest:
	docker push $(DOCKER_IMAGE_LATEST)

.PHONY: start
start: .env
	docker compose $(ENV_FILE_PARAM) up -d

.PHONY: clean
clean:
	docker compose $(ENV_FILE_PARAM) down

.PHONY: migrations
migrations: start
	docker compose exec floto python manage.py makemigrations --check

requirements-frozen.txt: build
	docker run --rm $(DOCKER_IMAGE) pip freeze > $@

.PHONY: tests
tests: .env
	docker-docker -f ./tests-compose.yml run manage.py test
