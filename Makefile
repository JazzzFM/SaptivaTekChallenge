build:
	docker build -t prompt-service .

run:
	docker run -p 8000:8000 -e VECTOR_BACKEND=faiss prompt-service

lint:
	ruff check .
	mypy . --python-version=3.11
