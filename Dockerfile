FROM python:3.10 AS builder

WORKDIR /app

COPY ./alembic.ini /app/alembic.ini
RUN ["pip3", "install", "--user", "poetry"]
COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock
RUN ["/root/.local/bin/poetry", "config", "virtualenvs.create", "false", "--local"]
RUN ["/root/.local/bin/poetry", "install"]

COPY ./alembic /app/alembic
COPY ./cli_registry /app/cli_registry

CMD ["/root/.local/bin/poetry", "run", "app"]
