FROM python:3.12-slim AS poetry
LABEL authors="Roman Poltorabatko"
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Add MongoDB tools using the specified .deb file
RUN apt-get update && apt-get install -y wget && \
    wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-100.9.4.deb && \
    apt-get install -y ./mongodb-database-tools-debian12-x86_64-100.9.4.deb && \
    rm mongodb-database-tools-debian12-x86_64-100.9.4.deb


RUN pip install poetry

FROM poetry AS environment
WORKDIR /usr/src/app
COPY ./poetry.lock ./pyproject.toml /usr/src/app/

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

FROM environment AS code
WORKDIR /usr/src/app
COPY . /usr/src/app

RUN mkdir /usr/src/app/logs || true
RUN poetry install

ENTRYPOINT ["poetry", "run", "app"]