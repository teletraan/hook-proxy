build:
	docker build -t dcr.teletraan.io/library/hook-proxy:latest .

push: build
	 docker push dcr.teletraan.io/library/hook-proxy:latest

update:
	docker pull dcr.teletraan.io/library/hook-proxy:latest
	docker-compose up -d