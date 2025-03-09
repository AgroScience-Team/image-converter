FROM python:3.10-slim

RUN pip install poetry

WORKDIR /image-converter

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

COPY ioc ./ioc
COPY src ./src

ENV PYTHONPATH "${PYTHONPATH}:/image-converter"

RUN poetry install --no-root
RUN apt update && apt install -y libexpat1

CMD ["poetry", "run", "python", "./src/main.py"]