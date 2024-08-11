FROM docker

# poetry because we need it to run
# the others because we need them for psutil
RUN apk add poetry build-base linux-headers

ENV POETRY_VIRTUALENVS_PATH=/tmp/poetry/venv
ENV POETRY_CACHE_DIR=/tmp/poetry/cache
