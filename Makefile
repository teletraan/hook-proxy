REGISTRY ?= dcr.teletraan.io
IMAGE_NAME ?= library/hook-proxy
IMAGE_TAG ?= dev-latest

docker-build:
	docker build -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} .

docker-push: docker-build
	 docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

update:
	docker pull dcr.teletraan.io/library/hook-proxy:dev-latest
	docker-compose up -d