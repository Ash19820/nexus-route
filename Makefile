.PHONY: build run stop

IMAGE_NAME = nexus-route:latest
CONTAINER_NAME = nexus-gateway

build:
	podman build -t $(IMAGE_NAME) .

run:
	podman run --rm -it \
		--name $(CONTAINER_NAME) \
		-p 127.0.0.1:8000:8000 \
		--env-file .env \
		$(IMAGE_NAME)

stop:
	podman stop $(CONTAINER_NAME)
