FROM python:3.10-alpine
RUN pip3 install poetry
WORKDIR bot/
COPY pyproject.toml ./
COPY poetry.lock ./
RUN poetry install --no-root
COPY . ./
CMD ["poetry", "run", "python3", "-m", "nextbox"]
